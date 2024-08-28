"""
Copyright 2023 ACE IoT Solutions
Licensed under the MIT License (MIT)
Created by Justice Lee

This agent is used to analyze images from a camera using YOLOv8, and publish the results to the VOLTTRON message bus.
The agent is configured using the config file, and the camera information is stored in the config file.
The agent will periodically scan the cameras and publish the results to the message bus.
The agent also provides a web interface to view the camera images and the pre filtered results of the analysis.


"""

__docformat__ = 'reStructuredText'

import logging
import sys
import os
import argparse
import asyncio
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
import grequests
from requests.auth import HTTPDigestAuth, HTTPBasicAuth
from io import BytesIO
from datetime import datetime
from volttron.platform.messaging import headers as header_mod
from volttron.platform.agent import utils


from bacpypes3.debugging import bacpypes_debugging, ModuleLogger

from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.basetypes import PropertyIdentifier
from bacpypes3.apdu import AbortReason, AbortPDU, ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.vendor import get_vendor_info

from rdflib import Graph, Namespace  # type: ignore
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI

from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
import networkx as nx
from pyvis.network import Network
from bacpypes3.rdf.core import BACnetNS
from rdflib.namespace import RDFS

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"

seconds_in_day = 86400


def grasshopper(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Yolo
    :rtype: Yolo
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    scan_interval_secs = config.get('scan_interval_secs', seconds_in_day)
    low_limit = config.get('low_limit', 0)
    high_limit = config.get('high_limit', 4194303)
    batch_broadcast_size = config.get('batch_broadcast_size', 10000)
    bacpypes_settings = config.get('bacpypes_settings', {
        "name": "Excelsior",
        "instance": 999,
        "network": 0,
        "address": "192.168.1.12/24:47808",
        "vendoridentifier": 999,
        "foreign": None,
        "ttl": 30,
        "bbmd": None
    })
    graph_store_limit = config.get('graph_store_limit', 30)
    return Grasshopper(scan_interval_secs, low_limit, high_limit, batch_broadcast_size, bacpypes_settings, graph_store_limit, **kwargs)


class Grasshopper(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, scan_interval_secs=seconds_in_day, low_limit=0, high_limit = 4194303, batch_broadcast_size = 10000, bacpypes_settings = None, 
        graph_store_limit=30, **kwargs):
        super(Grasshopper, self).__init__(enable_web=True, **kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.bacnet_analysis = None
        self.scan_interval_secs = scan_interval_secs
        self.low_limit = low_limit
        self.high_limit = high_limit
        self.batch_broadcast_size = batch_broadcast_size
        if bacpypes_settings is None:
            bacpypes_settings = {
                "name": "Excelsior",
                "instance": 999,
                "network": 0,
                "address": "192.168.1.12/24:47808",
                "vendoridentifier": 999,
                "foreign": None,
                "ttl": 30,
                "bbmd": None
            }
        self.bacpypes_settings = bacpypes_settings
        self.graph_store_limit = graph_store_limit
        # asyncio.run(self.set_application(self.bacpypes_settings))
        self.default_config = {
            "scan_interval_secs": scan_interval_secs,
            "low_limit": low_limit,
            "high_limit": high_limit,
            "batch_broadcast_size": batch_broadcast_size,
            "graph_store_limit": graph_store_limit,
            "bacpypes_settings": bacpypes_settings
        }
        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.vip.config.set_default("config", self.default_config)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        _log.debug("Init completed")

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus. If a configuration exists at startup
        this will be called before onstart.

        Is called every time the configuration in the store changes.
        """
        config = self.default_config.copy()
        config.update(contents)


        # _log.debug("Configuring Agent")
        # _log.debug(contents)
        try:
            # if config_name == "config":
            #     for entry in contents:
            #         _log.debug(f"setting {entry}")
            self.scan_interval_secs = contents.get("scan_interval_secs", 86400)
            self.low_limit = contents.get("low_limit", 0)
            self.high_limit = contents.get("high_limit", 4194303)
            self.batch_broadcast_size = contents.get("batch_broadcast_size", 10000)
            self.bacpypes_settings = contents.get("bacpypes_settings", {
                "name": "Excelsior",
                "instance": 999,
                "network": 0,
                "address": "192.168.1.12/24:47808",
                "vendoridentifier": 999,
                "foreign": None,
                "ttl": 30,
                "bbmd": None
            })
            self.graph_store_limit = contents.get("graph_store_limit", 30)
            # asyncio.run(self.set_application(self.bacpypes_settings))
            if self.bacnet_analysis is not None:
                self.bacnet_analysis.kill()
            self.bacnet_analysis = self.core.periodic(self.scan_interval_secs, self.who_is_broadcast)
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return

        _log.debug("Config completed")

    def _grequests_exception_handler(self, request, exception):
        """
        Log exceptions from grequests
        """
        _log.error(f"grequests error: {exception} with {request}")

    async def set_application(self, bacpypes_settings):
        """
        Set the application address for the BACnet analysis
        """
        app_settings = argparse.Namespace(**bacpypes_settings)
        # self.app = Application.from_args(app_settings)
        return Application.from_args(app_settings)
        # _log.debug("set_application completed")

    async def get_router_networks(self, app, g):
        """
        Get the router to network information from the graph
        """
        _log.debug("get_router_networks")
        routers = await app.nse.who_is_router_to_network()
        for adapter, i_am_router_to_network in routers:
            _log.debug(f"adapter: {adapter} i_am_router_to_network: {i_am_router_to_network}")
            for net in i_am_router_to_network.iartnNetworkList:
                g.add((BACnetURI["//router/"+str(i_am_router_to_network.pduSource)], BACnetNS["router-to-network"],
                    BACnetURI["//network/"+str(net)]))
        _log.debug("get_router_networks Completed")
                
    async def get_device_objects(self, app, bacnet_graph):
        """
        Get the device objects from the graph
        """
        _log.debug("get_device_objects")
        track_lower = self.low_limit
        while track_lower <= self.high_limit:
            track_upper = track_lower + self.batch_broadcast_size
            if track_upper > self.high_limit:
                track_upper = self.high_limit
            i_ams = await app.who_is(track_lower, track_upper)
            for i_am in i_ams:
                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
                device_graph = bacnet_graph.create_device(device_address, device_identifier)
                bacnet_graph.graph.add((device_graph.device_iri, BACnetNS["i-am"], BACnetURI["//network/"+str(device_address.addrNet)]))
            track_lower += self.batch_broadcast_size
        _log.debug("get_device_objects Completed")

    def build_networkx_graph(self, g):
        """
        Build a networkx graph from the BACnet graph
        """
        def custom_edge_attrs(s, p, o):
            if RDFS._NS in p:
                label = p
            else:
                label = f"{str(p).split('#')[-1]}"
            return {
                "label": label,
                "color": "red",
            }

        def custom_transform_node_str(s):
            if RDFS._NS in s:
                return s
            elif BACnetNS in s:
                return f"{str(s).split('#')[-1]}"
            else:
                return s
    
        nx_graph = rdflib_to_networkx_graph(
            g, 
            edge_attrs=custom_edge_attrs,
            transform_s=custom_transform_node_str,
            transform_o=custom_transform_node_str,
        )

        rdf_edges = [(u, v) for u, v, attr in nx_graph.edges(data=True) if RDFS._NS in attr.get('label', '')]
        for u, v in rdf_edges:
            v_copy = str(v)
            nx_graph.remove_node(v)
            nx.relabel_nodes(nx_graph, {u: v_copy}, copy=False) 
        return nx_graph
    
    def pass_networkx_to_pyvis(self, nx_graph, net:Network):
        for node in nx_graph.nodes:
            color = "blue" if "router/" in node else "red"
            size = 20 if "router/" in node else 10
            net.add_node(node, size=size, color=color)

        for edge in nx_graph.edges(data=True):
            label = edge[2].get("label", "")
            net.add_edge(edge[0], edge[1], label=label)

    async def get_device_and_router(self, g, bacnet_graph):
        _log.debug("Running Async for Who Is and Router to network")
        app = await self.set_application(self.bacpypes_settings)
        await self.get_router_networks(app, g)
        await self.get_device_objects(app, bacnet_graph)

    def who_is_broadcast(self):
        """
        Broadcasts a Who-Is message to the BACnet network
        """
        _log.debug("who_is_broadcast")
        g = Graph()
        now = datetime.now()
        # Create ttl graph
        bacnet_graph = BACnetGraph(g)
        asyncio.run(self.get_device_and_router(g, bacnet_graph))
        
        rdf_path = f"grasshopper/webroot/grasshopper/graphs/ttl/bacnet_graph_{now}.ttl"
        os.makedirs(os.path.dirname(rdf_path), exist_ok=True)
        g.serialize(destination=rdf_path, format="turtle")

        nx_graph = self.build_networkx_graph(g)

        net = Network(notebook=True, bgcolor="#222222", font_color="white", filter_menu=True)
        self.pass_networkx_to_pyvis(nx_graph, net)
        net.show_buttons(filter_=['physics'])
        net_path = f"grasshopper/webroot/grasshopper/graphs/html/bacnet_graph_{now}.html"
        os.makedirs(os.path.dirname(net_path), exist_ok=True)
        net.write_html(net_path)

    def jsonrpc(self, env, data):
        """
        Returns camera information for web interface
        """
        _log.debug("////////////////JSONRPC")
        data = []
        graph_html_roots = os.path.abspath(os.path.join(os.path.dirname(__file__), 'webroot/grasshopper/graphs/html/'))
        _log.debug("GRAPH URL: ", graph_html_roots)
        if os.path.exists(graph_html_roots):
            for filename in os.listdir(graph_html_roots):
                data.append(filename)
        _log.debug(data)
        return {'data' : data}

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        # Example publish to pubsub
        # self.vip.pubsub.publish('pubsub', "devices/camera/topic", message="HI!")
        _log.debug("in onstart")

        # Sets WEB_ROOT to be the path to the webroot directory
        # in the agent-data directory of the installed agent..
        WEB_ROOT = os.path.abspath(os.path.abspath(os.path.join(os.path.dirname(__file__), 'webroot/')))
        # Serves the static content from 'webroot' directory

        self.vip.web.register_path(r'^/grasshopper/.*', WEB_ROOT)
        self.vip.web.register_endpoint(r'/grasshopper_rpc/jsonrpc', self.jsonrpc)

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        pass

    @RPC.export
    def rpc_method(self, arg1, arg2, kwarg1=None, kwarg2=None):
        """
        RPC method

        May be called from another agent via self.core.rpc.call
        """
        pass
        # return self.setting1 + arg1 - arg2


def main():
    """Main method called to start the agent."""
    utils.vip_main(grasshopper, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
