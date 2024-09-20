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
import shutil
import argparse
import asyncio
import gevent
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
# from volttron.platform.web import Response
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
from rdflib.compare import to_isomorphic, graph_diff
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
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
        gevent.sleep(.1)
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
            gevent.sleep(.1)
            _log.debug(f"Currently Processing at {track_lower}")
            track_upper = track_lower + self.batch_broadcast_size
            if track_upper > self.high_limit:
                track_upper = self.high_limit
            i_ams = await app.who_is(track_lower, track_upper)
            for i_am in i_ams:
                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
                device_graph = bacnet_graph.create_device(device_address, device_identifier)
                bacnet_graph.graph.add((device_graph.device_iri, BACnetNS["device-on-network"], BACnetURI["//network/"+str(device_address.addrNet)]))
                bacnet_graph.graph.add((device_graph.device_iri, BACnetNS["vendor_id"], BACnetURI["//vendor/"+str(i_am.vendorID)]))
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

        nx_graph = rdflib_to_networkx_digraph(
            g, 
            edge_attrs=custom_edge_attrs,
            transform_s=custom_transform_node_str,
            transform_o=custom_transform_node_str,
        )

        is_directed = nx_graph.is_directed()
        print(f"Is the graph directed? {is_directed}")

        remove_nodes = []
        rdf_edges = {}
        device_address_edges = []
        data = {}
        for u, v, attr in nx_graph.edges(data=True):
            label = attr.get("label", "")
            if RDFS._NS in label:
                print("rdfs: ", u, v)
                rdf_edges[u] = v
                remove_nodes.append(u)
                remove_nodes.append(v)
            elif 'device-address' in label:
                device_address_edges.append((u, v))
            elif 'device-instance' in label:
                if u in data:
                    data[u]['device instance'] = str(v)
                else:
                    data[u] = {'device instance': str(v)}
                remove_nodes.append(v)
            elif str(label) == 'a':
                if u in data:
                    data[u]['bacnet type'] = str(v)
                else:
                    data[u] = {'bacnet type': str(v)}
                remove_nodes.append(v)
            elif label not in ['device-on-network', 'router-to-network']:
                remove_nodes.append(v)
            elif label == 'device-on-network' and 'network/None' in v:
                remove_nodes.append(v)
                remove_nodes.append(u)

        for u, v in device_address_edges:
            if u in data:
                data[u]['device address'] = str(rdf_edges[v])
            else:
                data[u] = {'device address': str(rdf_edges[v])}

        nx_graph.remove_nodes_from(remove_nodes)
        
        return nx_graph, data
    
    def pass_networkx_to_pyvis(self, nx_graph, net:Network, data):
        for node in nx_graph.nodes:
            if "router/" in node:
                color = "cyan"
                size = 30
                title = "Router Node"
            elif "network/" in node:
                color = "green"
                size = 20
                title = "Network Node"
            else:
                color = "red"
                size = 10
                title = str(data.get(node, {}))

            net.add_node(node, size=size, title=title, data=data.get(node, {}), color=color)

        print("edges: ", len(nx_graph.edges))
        for edge in nx_graph.edges(data=True):
            label = edge[2].get("label", "")
            net.add_edge(edge[0], edge[1], label=label)

    async def get_device_and_router(self, g, bacnet_graph):
        _log.debug("Running Async for Who Is and Router to network")
        app = await self.set_application(self.bacpypes_settings)
        await self.get_router_networks(app, g)
        await self.get_device_objects(app, bacnet_graph)

    def start_get_device_and_router(self, g, bacnet_graph):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.get_device_and_router(g, bacnet_graph))
        finally:
            loop.close()

    def who_is_broadcast(self):
        """
        Broadcasts a Who-Is message to the BACnet network
        """
        _log.debug("who_is_broadcast")
        g = Graph()
        now = datetime.now()
        # Create ttl graph
        bacnet_graph = BACnetGraph(g)
        gevent.spawn(self.start_get_device_and_router(g, bacnet_graph))
        
        rdf_path = f"grasshopper/webroot/grasshopper/graphs/ttl/bacnet_graph_{now}.ttl"
        os.makedirs(os.path.dirname(rdf_path), exist_ok=True)
        g.serialize(destination=rdf_path, format="turtle")

        nx_graph, node_data = self.build_networkx_graph(g)

        net = Network(notebook=True, bgcolor="#222222", font_color="white", filter_menu=True)
        self.pass_networkx_to_pyvis(nx_graph, net, node_data)
        net.show_buttons(filter_=['physics'])
        net_path = f"grasshopper/webroot/grasshopper/graphs/html/bacnet_graph_{now}.html"
        os.makedirs(os.path.dirname(net_path), exist_ok=True)
        net.write_html(net_path)

        html_lib_route = "grasshopper/webroot/grasshopper/graphs/html/lib"
        if not os.path.exists(html_lib_route):
            if os.path.exists("lib"):
                shutil.move("lib", html_lib_route)

    def jsonrpc(self, env, data):
        """
        Returns camera information for web interface
        """
        _log.debug("JSONRPC running to fetch data")
        data = []
        graph_ttl_roots = os.path.abspath(os.path.join(os.path.dirname(__file__), 'webroot/grasshopper/graphs/ttl/'))
        if os.path.exists(graph_ttl_roots):
            for filename in os.listdir(graph_ttl_roots):
                if filename.endswith('.ttl'):
                    data.append(filename)
        return {'data' : data}

    def compare_rdf_graphs(self, env, data):
        """
        Takes requested rdf graphs to compare and returns resulting pyvis display
        """
        _log.debug("Started RDF Graph Comparison")
        def pass_networkx_to_pyvis(nx_graph, net:Network, data, color, image=None):
            shape = "image" if image else "dot"
            for node in nx_graph.nodes:
                if "router/" in node:
                    size = 30
                    title = "Router Node"
                elif "network/" in node:
                    size = 20
                    title = "Network Node"
                else:
                    size = 10
                    title = str(data.get(node, {}))
                if image:
                    net.add_node(node, size=size, title=title, shape=shape, image=image, data=data.get(node, {}), color=color)
                else:
                    net.add_node(node, size=size, title=title, data=data.get(node, {}), color=color)
            print("edges: ", len(nx_graph.edges))
            for edge in nx_graph.edges(data=True):
                label = edge[2].get("label", "")
                net.add_edge(edge[0], edge[1], label=label)
        
        if env['REQUEST_METHOD'].upper() != 'POST':
            return {"status": False}
        print(data)
        ttl_graph1 = data.get("graph1", None)
        ttl_graph2 = data.get("graph2", None)
        if not ttl_graph1 or not ttl_graph2:
            return {"status": False}
        ttl_graph1_path = f"grasshopper/webroot/grasshopper/graphs/ttl/{ttl_graph1}"
        ttl_graph2_path = f"grasshopper/webroot/grasshopper/graphs/ttl/{ttl_graph2}"
        g1 = Graph()
        g2 = Graph()
        g1.parse(ttl_graph1_path, format="ttl")
        g2.parse(ttl_graph2_path, format="ttl")

        iso_g1 = to_isomorphic(g1)
        iso_g2 = to_isomorphic(g2)

        in_both, in_first, in_second = graph_diff(iso_g1, iso_g2)

        nx_graph_in_both, node_data_in_both = self.build_networkx_graph(in_both)
        nx_graph_in_first, node_data_in_first = self.build_networkx_graph(in_first)
        nx_graph_in_second, node_data_in_second = self.build_networkx_graph(in_second)

        net = Network(notebook=True, bgcolor="#222222", font_color="white", filter_menu=False)
        pass_networkx_to_pyvis(nx_graph_in_both, net, node_data_in_both, "grey")
        pass_networkx_to_pyvis(nx_graph_in_first, net, node_data_in_first, "red", "../../imgs/minus.png")
        pass_networkx_to_pyvis(nx_graph_in_second, net, node_data_in_second, "green", "../../imgs/plus.png")
        net.show_buttons(filter_=['physics'])
        net.write_html(f"grasshopper/webroot/grasshopper/graphs/html/compare.html")
        _log.debug("RDF Graph Compared Completed")
        return {"status": True}

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
        self.vip.web.register_endpoint(r'/grasshopper_rpc/compare_rdf_graphs', self.compare_rdf_graphs)

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
