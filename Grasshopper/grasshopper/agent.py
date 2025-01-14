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

from rdflib import Graph, Namespace, RDF, Literal  # type: ignore
from rdflib.compare import to_isomorphic, graph_diff
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph, rdflib_to_networkx_graph
from rdflib.namespace import RDFS
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI

import networkx as nx
from pyvis.network import Network

from gevent.pywsgi import WSGIServer
from gevent.ssl import SSLContext, PROTOCOL_TLS_SERVER
from flask import request
from flask_restx import Namespace, Resource, fields
from grasshopper.app import create_app
from grasshopper.api import executor
from grasshopper.serializers import ip_address, ip_address_list


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

        self.configure_server_setup()
        if self.bacnet_analysis is not None:
            self.bacnet_analysis.kill()
        self.bacnet_analysis = self.core.periodic(self.scan_interval_secs, self.who_is_broadcast)

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


        _log.debug("Configuring Agent")
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
            self.graph_store_limit = contents.get("graph_store_limit", None)
            
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return
        
        self.configure_server_setup()

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
            except KeyError:
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
            except KeyError:
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
            _log.debug(f"Currently Processing at {track_lower}")
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


    def setup_routes(self, app):
        current_instance = self

        class SubnetConfig(Resource):
            @app.api.marshal_with(ip_address_list)
            def get(self):
                """Gets the list of Subnets CIDR Addresses stored in the config"""
                list_of_subnets_ips = current_instance.config_retrieve_subnets()
                return {"ip_address_list": list_of_subnets_ips}

            @app.api.expect(ip_address)
            def post(self):
                """Adds ip address to the list of Subnets CIDR Addresses stored in the config"""
                list_of_subnets_ips = current_instance.config_retrieve_subnets()
                ip = request.json.get("ip_address")
                if ip and ip not in list_of_subnets_ips:
                    list_of_subnets_ips.append(ip)
                current_instance.config_store_subnets(list_of_subnets_ips)
                return {"list_of_subnets_ips": list_of_subnets_ips}

            @app.api.expect(ip_address)
            def delete(self):
                """Removes ip address from the list of subnets IP Addresses stored in the config"""
                list_of_subnets_ips = current_instance.config_retrieve_subnets()
                ip = request.json.get("ip_address")
                if ip and ip in list_of_subnets_ips:
                    list_of_subnets_ips.remove(ip)
                current_instance.config_store_subnets(list_of_subnets_ips)
                return {"list_of_subnets_ips": list_of_subnets_ips}

        class BBMDConfig(Resource):
            @app.api.marshal_with(ip_address_list)
            def get(self):
                """Gets the list of BBMD IP Addresses stored in the config"""
                list_of_bbmd_ips = current_instance.config_retrieve_bbmd_devices()
                return {"ip_address_list": list_of_bbmd_ips}

            @app.api.expect(ip_address)
            def post(self):
                """Adds ip address to the list of BBMD IP Addresses stored in the config"""
                list_of_bbmd_ips = current_instance.config_retrieve_bbmd_devices()
                ip = request.json.get("ip_address")
                if ip and ip not in list_of_bbmd_ips:
                    list_of_bbmd_ips.append(ip)
                current_instance.config_store_bbmd_devices(list_of_bbmd_ips)
                return {"list_of_bbmd_ips": list_of_bbmd_ips}

            @app.api.expect(ip_address)
            def delete(self):
                """Removes ip address from the list of BBMD IP Addresses stored in the config"""
                list_of_bbmd_ips = current_instance.config_retrieve_bbmd_devices()
                ip = request.json.get("ip_address")
                if ip and ip in list_of_bbmd_ips:
                    list_of_bbmd_ips.remove(ip)
                current_instance.config_store_bbmd_devices(list_of_bbmd_ips)
                return {"list_of_bbmd_ips": list_of_bbmd_ips}

        app.api.add_resource(BBMDConfig, '/bbmds')
        app.api.add_resource(SubnetConfig, '/subnets')

    def configure_server_setup(self):
        """
        Runs to setup web server and processes when configuration changes
        """
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
        app = create_app()
        app.config['agent_data_path'] = agent_data_path
        self.setup_routes(app)
        certfile = self.webapp_settings.get('certfile')
        keyfile = self.webapp_settings.get('keyfile')
        if certfile and keyfile:
            ssl_context = SSLContext(PROTOCOL_TLS_SERVER)
            try:
                ssl_context.load_cert_chain(certfile=certfile, keyfile=keyfile)
                self.http_server = WSGIServer((self.webapp_settings.get('host'), self.webapp_settings.get('port')), app, log=_log, ssl_context=ssl_context)
            except Exception as e:
                print(f"Failed to setup ssl_context: {e}")
                raise
        else:
            self.http_server = WSGIServer((self.webapp_settings.get('host'), self.webapp_settings.get('port')), app, log=_log)

        if self.http_server is None:
            _log.error("error: server not started successfully")
            self.vip.health.set_status(STATUS_BAD)
            return -1
        else:
            self.http_server.start()
        _log.info("SERVER STARTED")
        address, port = self.http_server.address
        _log.info(f"Starting server on {address}:{port}")
        

        folders = ["ttl", "compare"]
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

        

        # Sets WEB_ROOT to be the path to the webroot directory
        # in the agent-data directory of the installed agent..
        # WEB_ROOT = os.path.abspath(os.path.abspath(os.path.join(os.path.dirname(__file__), 'webroot/')))
        

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        self.http_server.stop()

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
