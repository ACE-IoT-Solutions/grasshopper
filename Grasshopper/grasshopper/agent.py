"""
Copyright 2023 ACE IoT Solutions
Licensed under the MIT License (MIT)
Created by Justice Lee

This agent is used to analyze the BacNet Network using bacpypes3 and return an overall view of the network.
The agent is configured using the config file, with the bacnet settings stored in the config file.
The agent will periodically scan the network and publish the responsive devices detected in a graphical view.
The agent also provides a web interface to view each scan of the network as found.
"""

__docformat__ = 'reStructuredText'

import logging
import os
import sys
import shutil
import argparse
import asyncio
import gevent
import json
import ipaddress
import signal
import re
import traceback
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
from bacpypes3.vendor import get_vendor_info, VendorInfo
from bacpypes3.local.networkport import NetworkPortObject

from rdflib import Graph, Namespace, RDF, Literal  # type: ignore
from rdflib.compare import to_isomorphic, graph_diff
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph, rdflib_to_networkx_graph
from rdflib.namespace import RDFS
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI

import networkx as nx
from pyvis.network import Network

import uvicorn
from fastapi import FastAPI, Request
from grasshopper.app import create_app
from grasshopper.api import executor, setup_bbmd_routes
from grasshopper.serializers import IPAddress, IPAddressList


_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"

seconds_in_day = 86400
DEVICE_STATE_CONFIG = "device_config"


def grasshopper(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Grasshopper
    :rtype: Grasshopper
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
    device_broadcast_full_step_size = config.get('device_broadcast_full_step_size', 100)
    device_broadcast_empty_step_size = config.get('device_broadcast_empty_step_size', 1000)
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
    webapp_settings = config.get('webapp_settings', {
        "host": "0.0.0.0",
        "port": 5000,
        "certfile": None,
        "keyfile": None
    })
    graph_store_limit = config.get('graph_store_limit', None)
    return Grasshopper(scan_interval_secs, low_limit, high_limit, device_broadcast_full_step_size,
        device_broadcast_empty_step_size, bacpypes_settings, graph_store_limit, webapp_settings, **kwargs)


class Grasshopper(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, scan_interval_secs=seconds_in_day, low_limit=0, high_limit = 4194303, device_broadcast_full_step_size= 100,
        device_broadcast_empty_step_size = 1000, bacpypes_settings = None, graph_store_limit=None, webapp_settings=None, **kwargs):
        super(Grasshopper, self).__init__(enable_web=True, **kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.bacnet_analysis = None
        self.scan_interval_secs = scan_interval_secs
        self.low_limit = low_limit
        self.high_limit = high_limit
        self.device_broadcast_full_step_size = device_broadcast_full_step_size
        self.device_broadcast_empty_step_size = device_broadcast_empty_step_size
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
        if webapp_settings is None:
            webapp_settings = {
                "host": "0.0.0.0",
                "port": 5000,
                "certfile": None,
                "keyfile": None
            }
        self.webapp_settings = webapp_settings
        self.graph_store_limit = graph_store_limit
        self.default_config = {
            "scan_interval_secs": scan_interval_secs,
            "low_limit": low_limit,
            "high_limit": high_limit,
            "device_broadcast_full_step_size": device_broadcast_full_step_size,
            "device_broadcast_empty_step_size": device_broadcast_empty_step_size,
            "graph_store_limit": graph_store_limit,
            "bacpypes_settings": bacpypes_settings,
            "webapp_settings": webapp_settings
        }
        self.config_store_lock = gevent.lock.BoundedSemaphore()
        self.http_server = None
        self.agent_data_path = None

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
        _log.debug("Configuring Agent")
        config = self.default_config.copy()
        config.update(contents)

        try:
            self.scan_interval_secs = contents.get("scan_interval_secs", 86400)
            self.low_limit = contents.get("low_limit", 0)
            self.high_limit = contents.get("high_limit", 4194303)
            self.device_broadcast_full_step_size = contents.get("device_broadcast_full_step_size", 100)
            self.device_broadcast_empty_step_size = contents.get("device_broadcast_empty_step_size", 1000)
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
            self.webapp_settings = contents.get("webapp_settings",{
                "host": "0.0.0.0",
                "port": 5000,
                "certfile": None,
                "keyfile": None
            })
            vendorid = self.bacpypes_settings.get("vendoridentifier", 999)
            if vendorid != 999:
                self.vendor_info = VendorInfo(vendorid)
                self.vendor_info.register_object_class(56, NetworkPortObject)
            
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return
        
        self.configure_server_setup()

        if self.bacnet_analysis is not None:
            self.bacnet_analysis.kill()
        self.bacnet_analysis = self.core.periodic(self.scan_interval_secs, self.who_is_broadcast)

        _log.debug("Config completed")

    def _grequests_exception_handler(self, request, exception):
        """
        Log exceptions from grequests
        """
        _log.error(f"grequests error: {exception} with {request}")

    def overwrite_triple(self, graph, subject, predicate, new_object):
        """
        Overwrite existing triples if triple is not one of reserved
        """
        if 'device-on-network' not in predicate and 'router-to-network' not in predicate:
            for triple in graph.triples((subject, predicate, None)):
                graph.remove(triple)

        graph.add((subject, predicate, new_object))

    def config_store_bbmd_devices(self, bbmd_devices: list):
        """
        Updates config list of foreign devices
        """
        _log.debug("config_store_bbmd_devices")
        with self.config_store_lock:
            try:
                config = self.vip.config.get(DEVICE_STATE_CONFIG)
            except KeyError:
                config = {}
            config["bbmd_devices"] = bbmd_devices
            self.vip.config.set(DEVICE_STATE_CONFIG, config)

    def config_retrieve_bbmd_devices(self):
        """
        Retrieve config foreign devices
        """
        _log.debug("config_retrieve_bbmd_devices")
        with self.config_store_lock:
            try:
                config = self.vip.config.get(DEVICE_STATE_CONFIG)
                _log.debug(f"config_retrieve_bbmd_devices config: {config}")
            except KeyError as ke:
                _log.error(f"Error config_retrieve_subnets: {ke}")
                return []
        return config.get("bbmd_devices", [])

    def config_store_subnets(self, subnets: list):
        """
        Updates config list of foreign devices
        """
        _log.debug("config_store_subnets")
        with self.config_store_lock:
            try:
                config = self.vip.config.get(DEVICE_STATE_CONFIG)
            except KeyError:
                config = {}
            config["subnets"] = subnets
            self.vip.config.set(DEVICE_STATE_CONFIG, config)

    def config_retrieve_subnets(self):
        """
        Retrieve config subnets
        """
        _log.debug("config_retrieve_subnets")
        with self.config_store_lock:
            try:
                config = self.vip.config.get(DEVICE_STATE_CONFIG)
                _log.debug(f"config_retrieve_subnets config: {config}")
            except KeyError as ke:
                _log.error(f"Error config_retrieve_subnets: {ke}")
                return []
        return config.get("subnets", [])

    async def set_application(self, bacpypes_settings):
        """
        Set the application address for the BACnet analysis
        """
        app_settings = argparse.Namespace(**bacpypes_settings)
        _log.debug(f"Application config: {app_settings}")
        return Application.from_args(app_settings)

    async def get_router_networks(self, app, graph, interfaces):
        """
        Get the router to network information from the network for the graph.
        Who_is_router_to_network is called based on individual networks found existing in the graph from device broadcast to prevent overloading the system.
        Valid network ranges go from 1 to 65,534
        """
        _log.debug("get_router_networks")
        for i in range(0, 65535):
            gevent.sleep(0)
            _log.debug(f"Currently Processing network {i}")
            if any(graph.triples((None, BACnetNS["router-to-network"], BACnetURI["//network/"+str(i)]))):
                routers = await app.nse.who_is_router_to_network(network=i)
                for adapter, i_am_router_to_network in routers:
                    _log.debug(f"adapter: {adapter} i_am_router_to_network: {i_am_router_to_network}")
                    self.overwrite_triple(graph, BACnetURI["//router/"+str(i_am_router_to_network.pduSource)], RDF.type, BACnetNS.Router)
                    for net in i_am_router_to_network.iartnNetworkList:
                        self.overwrite_triple(graph, BACnetURI["//router/"+str(i_am_router_to_network.pduSource)], BACnetNS["router-to-network"],
                            BACnetURI["//network/"+str(net)])

                    ip = ipaddress.ip_address(i_am_router_to_network.pduSource)
                    not_in_network = True
                    for interface in interfaces:
                        if ip in interface.network:
                            not_in_network = False
                            self.overwrite_triple(graph, BACnetURI["//router/"+str(i_am_router_to_network.pduSource)], 
                                BACnetNS["device-on-network"], BACnetURI["//subnet/"+str(interface.network)])
                    if not_in_network:
                        self.overwrite_triple(graph, BACnetURI["//Grasshopper"], BACnetNS["router-to-network"], 
                            BACnetURI["//router/"+str(i_am_router_to_network.pduSource)])
                
        _log.debug("get_router_networks Completed")
                
    async def get_device_objects(self, app, graph, interfaces):
        """
        Get the device objects from the network for the graph
        """
        _log.debug("get_device_objects")

        def get_known_device_end_range(graph, start_pos):
            """Checks number of existing networks and send who_is to potential devices in the network limited by stepsize"""
            current_pos = start_pos
            end_pos = current_pos + self.device_broadcast_empty_step_size
            track_routers = 0
            while current_pos < end_pos:
                if any(graph.triples((BACnetURI["//" + str(current_pos)], None, None))):
                    track_routers += 1
                if track_routers >= self.device_broadcast_full_step_size:
                    return current_pos
                current_pos += 1
            return end_pos

        bbmd_device_id_of_networks = {}
        devices_in_network = {}
        bbmd_ips = []
        bbmds = self.config_retrieve_bbmd_devices()

        for bbmd in bbmds:
            try:
                bbmd_ips.append(ipaddress.ip_address(bbmd))
            except ValueError as ve:
                _log.error(f"Invalid bbmd ip: {ve}")

        for interface in interfaces:
            bbmd_device_id_of_networks[interface.ip] = None
            devices_in_network[interface.ip] = []

        track_lower = self.low_limit
        while track_lower <= self.high_limit:
            gevent.sleep(0.1)
            _log.debug(f"Currently Processing devices at {track_lower}")
            track_upper = get_known_device_end_range(graph, track_lower)
            if track_upper > self.high_limit:
                track_upper = self.high_limit
            i_ams = await app.who_is(track_lower, track_upper)
            for i_am in i_ams:
                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
                device_iri = BACnetURI["//" + str(device_identifier[1])]
                try:
                    ip = ipaddress.ip_address(device_address)
                    not_in_network = True
                    for interface in interfaces:
                        if ip in interface.network:
                            not_in_network = False
                            if ip in bbmd_ips:
                                bbmd_device_id_of_networks[interface.ip] = device_iri
                            else:
                                self.overwrite_triple(graph, device_iri, RDF.type, BACnetNS.Device)
                            self.overwrite_triple(graph, device_iri, BACnetNS["device-on-network"], BACnetURI["//subnet/"+str(interface.network)])
                            self.overwrite_triple(graph, device_iri, BACnetNS["device-instance"], Literal(device_identifier[1]))
                            self.overwrite_triple(graph, device_iri, BACnetNS["device-address"], Literal(str(device_address)))
                            self.overwrite_triple(graph, device_iri, BACnetNS["vendor-id"], BACnetURI["//vendor/"+str(i_am.vendorID)])

                    if not_in_network:
                        raise ValueError("Device not in network")

                except ValueError:
                    self.overwrite_triple(graph, device_iri, RDF.type, BACnetNS.Device)
                    self.overwrite_triple(graph, device_iri, BACnetNS["device-on-network"], BACnetURI["//network/"+str(device_address.addrNet)])
                    self.overwrite_triple(graph, device_iri, BACnetNS["device-instance"], Literal(device_identifier[1]))
                    self.overwrite_triple(graph, device_iri, BACnetNS["device-address"], Literal(str(device_address)))
                    self.overwrite_triple(graph, device_iri, BACnetNS["vendor-id"], BACnetURI["//vendor/"+str(i_am.vendorID)])
                
            track_lower = track_upper + 1
        _log.debug(f"size of devices_in_network: {len(devices_in_network)} vs network {len(interfaces)}")
        for interface in interfaces:
            if bbmd_device_id_of_networks[interface.ip]:
                self.overwrite_triple(graph, bbmd_device_id_of_networks[interface.ip], RDF.type, BACnetNS.BBMD)
                self.overwrite_triple(graph, bbmd_device_id_of_networks[interface.ip], BACnetNS["device-on-network"], BACnetURI["//subnet/"+str(interface.network)])
                self.overwrite_triple(graph, BACnetURI['//Grasshopper'], BACnetNS["device-on-network"], bbmd_device_id_of_networks[interface.ip])
            else:
                self.overwrite_triple(graph, BACnetURI['//Grasshopper'], BACnetNS["device-on-network"], BACnetURI["//subnet/"+str(interface.network)])
            self.overwrite_triple(graph, BACnetURI["//subnet/"+str(interface.network)], RDF.type, BACnetNS.Subnet)

        _log.debug("get_device_objects Completed")

    async def get_device_and_router(self, graph):
        _log.debug("Running Async for Who Is and Router to network")
        settings = self.bacpypes_settings.copy()
        cidrs = self.config_retrieve_subnets()
        interfaces = []
        for cidr in cidrs:
            interfaces.append(ipaddress.ip_interface(cidr))
        settings['bbmd'] = cidrs
        app = await self.set_application(settings)
        self.overwrite_triple(graph, BACnetURI["//Grasshopper"], BACnetNS["address"], BACnetURI[self.bacpypes_settings['address']])
        self.overwrite_triple(graph, BACnetURI["//Grasshopper"], BACnetNS["vendoridentifier"], BACnetURI[self.bacpypes_settings['vendoridentifier']])
        self.overwrite_triple(graph, BACnetURI["//Grasshopper"], BACnetNS["name"], BACnetURI[self.bacpypes_settings['name']])
        await self.get_device_objects(app, graph, interfaces)
        await self.get_router_networks(app, graph, interfaces)
        app.close()

    def start_get_device_and_router(self, graph):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.get_device_and_router(graph))
        finally:
            loop.close()

    def who_is_broadcast(self):
        """
        Broadcasts a Who-Is message to the BACnet network
        """
        _log.debug("who_is_broadcast")

        def extract_datetime(filename):
            datetime_str = filename.split("_")[-1].replace(".ttl", "")
            return datetime.fromisoformat(datetime_str)
        
        def is_valid_filename(filename):
            pattern = r"^bacnet_graph_\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}\.ttl$"
            return re.match(pattern, filename)
        
        def find_latest_file(directory):
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            valid_files = [f for f in files if is_valid_filename(f)]

            if not valid_files:
                return None
            
            latest_file = max(valid_files, key=extract_datetime)
            return latest_file
        
        try:
            base_rdf_path = os.path.join(self.agent_data_path, "ttl/base.ttl")
            recent_ttl_file = find_latest_file(os.path.join(self.agent_data_path, "ttl"))

            graph = Graph()

            if os.path.exists(base_rdf_path):
                graph.parse(base_rdf_path, format='ttl')
            
            if recent_ttl_file:
                graph.parse(os.path.join(self.agent_data_path, f"ttl/{recent_ttl_file}"), format='ttl')

            now = datetime.now()

            gevent.spawn(self.start_get_device_and_router(graph))
            
            rdf_path = os.path.join(self.agent_data_path, f"ttl/bacnet_graph_{now}.ttl")
            os.makedirs(os.path.dirname(rdf_path), exist_ok=True)
            graph.serialize(destination=rdf_path, format="turtle")
        except Exception as e:
            _log.error(f"Error in who_is_broadcast: {e}")
            _log.error(traceback.format_exc())


    # setup_routes is not needed anymore as we use the setup_bbmd_routes function from api.py instead

    def configure_server_setup(self):
        """
        Runs to setup web server and processes when configuration changes
        """
        _log.debug('configure_server_setup')
        def ensure_folders_exist(agent_data_path, folder_names):
            for folder in folder_names:
                folder_path = os.path.join(agent_data_path, folder)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"Folder '{folder}' created.")
                else:
                    print(f"Folder '{folder}' already exists.")

        def get_agent_data_path(original_path):
            agent_name = os.path.basename(original_path)
            agent_data = f"{agent_name}.agent-data"
            modified_path = os.path.join(original_path, agent_data)
            return modified_path

        current_dir = os.getcwd()
        agent_data_path = get_agent_data_path(current_dir)
        self.agent_data_path = agent_data_path
        
        # Create FastAPI application
        app = create_app()
        app.state.agent_data_path = agent_data_path
        
        # Setup agent-specific routes
        setup_bbmd_routes(app)
        
        # Configure Uvicorn server
        host = self.webapp_settings.get('host', '0.0.0.0')
        port = int(self.webapp_settings.get('port', 5000))
        certfile = self.webapp_settings.get('certfile')
        keyfile = self.webapp_settings.get('keyfile')
        
        # Store app instance for later shutdown
        self.app = app
        
        # Configure server with or without SSL
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            ssl_certfile=certfile,
            ssl_keyfile=keyfile if certfile else None
        )
        
        # Create and start server
        self.http_server = uvicorn.Server(config)
        
        # Start in a new thread to not block
        import threading
        self.server_thread = threading.Thread(target=self.http_server.run)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        _log.info(f"FastAPI server started on {host}:{port}")

        # Create necessary folders
        folders = ["ttl", "compare", "network_config"]
        ensure_folders_exist(agent_data_path, folders)


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
        
        # Set up device config
        _log.info(f"Setting up Device Config")
        config_list = self.vip.config.list()
        if DEVICE_STATE_CONFIG not in config_list:
            _log.info(f"config: {DEVICE_STATE_CONFIG} not found")
            self.vip.config.set(
                config_name = DEVICE_STATE_CONFIG,
                contents={"bbmd_devices": [], "subnets": []}
            )
        else:
            _log.info(f"config: {DEVICE_STATE_CONFIG} found")

        # Sets WEB_ROOT to be the path to the webroot directory
        # in the agent-data directory of the installed agent..
        # WEB_ROOT = os.path.abspath(os.path.abspath(os.path.join(os.path.dirname(__file__), 'webroot/')))
        

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        _log.debug("in onstop")
        
        # Stop the Uvicorn server
        if hasattr(self, 'http_server') and self.http_server:
            self.http_server.should_exit = True
        
        #Kill executor and currently running tasks
        for pid in executor._processes.values():
            os.kill(pid.pid, signal.SIGKILL)
        executor.shutdown(wait=False)

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
