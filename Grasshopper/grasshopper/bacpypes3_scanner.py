"""
File contains the bacpypes3_scanner class which is used to scan the network for devices and routers.
"""
import argparse
import rdflib
import ipaddress
import gevent
import logging
import asyncio

from typing import Set, List
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.basetypes import PropertyIdentifier
from bacpypes3.apdu import AbortReason, AbortPDU, ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.vendor import get_vendor_info, VendorInfo
from bacpypes3.local.networkport import NetworkPortObject
from bacpypes3.comm import bind, ApplicationServiceElement
from bacpypes3.pdu import IPv4Address
from bacpypes3.ipv4.bvll import (
    LPDU,
    ReadBroadcastDistributionTable,
    ReadBroadcastDistributionTableAck,
    ReadForeignDeviceTable,
    ReadForeignDeviceTableAck,
)
from rdflib import Graph, Namespace, RDF, Literal  # type: ignore
from rdflib.compare import to_isomorphic, graph_diff
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph, rdflib_to_networkx_graph
from rdflib.namespace import RDFS
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI
from .rdf_components import (
    DeviceTypeHandler,
    BBMDTypeHandler,
    RouterTypeHandler,
    SubnetTypeHandler,
    NetworkTypeHandler,
    SubnetComponent,
    NetworkComponent,
    BACnetNode,
    AttachDeviceComponent,
)

from volttron.platform.agent import utils
_log = logging.getLogger(__name__)
utils.setup_logging()

class BVLLServiceElement(ApplicationServiceElement):

    def __init__(self):
        self.read_bdt_future = None
        self.read_fdt_future = None

    async def confirmation(self, pdu: LPDU):
        if isinstance(pdu, ReadBroadcastDistributionTableAck):
            self.read_bdt_future.set_result(pdu.bvlciBDT)
            self.read_bdt_future = None

        elif isinstance(pdu, ReadForeignDeviceTableAck):
            self.read_fdt_future.set_result(pdu.bvlciFDT)
            self.read_fdt_future = None

    def read_broadcast_distribution_table(self, address: IPv4Address) -> asyncio.Future:
        self.read_bdt_future = asyncio.Future()
        asyncio.ensure_future(
            self.request(ReadBroadcastDistributionTable(destination=address))
        )
        try:
            return asyncio.wait_for(self.read_bdt_future, timeout=3)
        except asyncio.TimeoutError:
            self.read_bdt_future.cancel()
            return None

    def read_foreign_device_table(self, address: IPv4Address) -> asyncio.Future:
        self.read_fdt_future = asyncio.Future()
        asyncio.ensure_future(self.request(ReadForeignDeviceTable(destination=address)))
        try:
            return asyncio.wait_for(self.read_fdt_future, timeout=3)
        except asyncio.TimeoutError:
            self.read_fdt_future.cancel()
            return None

class bacpypes3_scanner:
    def __init__(self, bacpypes_settings: dict, bbmds: List[str], subnets: List[str], 
            device_broadcast_empty_step_size: int = 1000, device_broadcast_full_step_size: int = 100,
            scan_low_limit: int = 0, scan_high_limit:int = 4194303) -> None:
        """
        Initialize the BACpypes3 scanner with the settings
        """
        self.bacpypes_settings = bacpypes_settings
        self.app_settings = bacpypes_settings
        self.bbmds = [ipaddress.ip_address(bbmd) for bbmd in bbmds]
        self.subnets = [ipaddress.ip_network(subnet) for subnet in subnets]
        self.device_broadcast_empty_step_size = device_broadcast_empty_step_size
        self.device_broadcast_full_step_size = device_broadcast_full_step_size
        self.scanner_node = None
        self.low_limit = scan_low_limit
        self.high_limit = scan_high_limit
        self.bbmd_in_subnet = {}

    async def set_application(self, graph: Graph)->Application:
        """
        Set the application address for the BACnet analysis
        """
        settings = self.bacpypes_settings.copy()
        bbmd_ips = self.get_bbmd_ips(graph)
        settings['bbmd'] = self.bacpypes_settings['bbmd'] + bbmd_ips + self.bbmds
        app_settings = argparse.Namespace(**self.bacpypes_settings)
        _log.debug(f"Application config: {app_settings}")
        return Application.from_args(app_settings)

    def get_networks_from_graph(self, g: rdflib.Graph) -> Set[int]:
        """Return a set of network numbers from the graph"""
        networks = set()
        for t in g.triples((None, RDF.type, BACnetNS["Network"])):
            networks.add(int(t[0].split('/')[-1]))
        return networks
    
    def get_bbmd_ips(self, g: rdflib.Graph) -> Set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """Return a set of BBMD IPs from the graph"""
        bbmd_ips = set()
        for t in g.triples((None, RDF.type, BACnetNS["BBMD"])):
            for t2 in g.triples((t[0], BACnetNS["device-address"], None)):
                try:
                    ip = ipaddress.ip_address(t2[2].value)
                    bbmd_ips.add(ip)
                except:
                    pass
        return bbmd_ips

    def get_device_ips(self, g: rdflib.Graph) -> Set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """Return a set of device IPs from the graph"""
        device_ips = set()
        for t in g.triples((None, RDF.type, BACnetNS["Device"])):
            for t2 in g.triples((t[0], BACnetNS["device-address"], None)):
                try:
                    ip = ipaddress.ip_address(t2[2].value)
                    device_ips.add(ip)
                except:
                    pass
        return device_ips
    
    async def set_scanner_node(self, graph:Graph)->BACnetNode:
        """
        Set the scanner node in the graph
        """
        scanner_node = BACnetNode(graph, BACnetURI["//Grasshopper"], DeviceTypeHandler, [AttachDeviceComponent])
        scanner_node.add_common_properties(
            label=BACnetURI[self.bacpypes_settings['name']],
            device_identifier=BACnetURI[self.bacpypes_settings['instance']],
            device_address=BACnetURI[self.bacpypes_settings['address']],
            vendor_id=BACnetURI[self.bacpypes_settings['vendoridentifier']]
        )
        self.scanner_node = scanner_node
    
    async def get_device_and_router(self, graph: Graph) -> None:
        _log.debug("Running Async for Who Is and Router to network")
        app = await self.set_application()
        await self.set_scanner_node(graph)
        await self.get_device_objects(app, graph)
        await self.get_router_networks(app, graph)
        await self.set_subnet_network(graph)
        app.close()
    
    async def get_router_networks(self, app: Application, graph:Graph) -> None:
        """
        Get the router to network information from the network for the graph.
        Who_is_router_to_network is called based on individual networks found existing in the graph from device broadcast to prevent overloading the system.
        Valid network ranges go from 1 to 65,534
        """
        _log.debug("get_router_networks")
        network_ids = self.get_networks_from_graph(graph)
        for network_id in network_ids:
            gevent.sleep(0)
            _log.debug(f"Currently Processing network {network_id}")
            routers = await app.nse.who_is_router_to_network(network=network_id)
            for adapter, i_am_router_to_network in routers:
                _log.debug(f"adapter: {adapter} i_am_router_to_network: {i_am_router_to_network}")
                router_pdu_source = i_am_router_to_network.pduSource
                router_iri = BACnetURI["//router/"+str(router_pdu_source)]
                router_node = BACnetNode(graph, router_iri, RouterTypeHandler, [SubnetComponent, NetworkComponent])
                for net in i_am_router_to_network.iartnNetworkList:
                    router_node.add_component_properties(network_id=net)

                ip = ipaddress.ip_address(router_pdu_source)
                not_in_network = True
                for subnet in self.subnets:
                    if ip in subnet:
                        not_in_network = False
                        router_node.add_component_properties(subnet=subnet)
                if not_in_network:
                    self.scanner_node.add_component_properties(device_iri = router_iri)
                
        _log.debug("get_router_networks Completed")

    async def check_if_device_is_bbmd(self, app: Application, device_address: Address) -> bool:
        """
        Check if the device is a BBMD
        """
        _log.debug("check_if_device_is_bbmd")
        is_bbmd = False
        try:
            bdt = await app.ase.read_broadcast_distribution_table(device_address)
            for bdte in bdt:
                is_bbmd = True
                break
        except (ErrorRejectAbortNack, AbortPDU) as e:
            _log.error(f"Error while checking if device is BBMD: {e}")
        _log.debug("check_if_device_is_bbmd Completed")
        return is_bbmd
    
    async def get_device_objects(self, app: Application, graph: Graph) -> None:
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

        track_lower = self.low_limit
        while track_lower <= self.high_limit:
            gevent.sleep(0)
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
                    not_in_subnet_list = True
                    
                    # Check if device is a BBMD
                    device_type_func = DeviceTypeHandler
                    if ip in self.bbmds or await self.check_if_device_is_bbmd(app, device_address):
                        device_type_func = BBMDTypeHandler
                    
                    device = BACnetNode(graph, device_iri, device_type_func, [SubnetComponent])
                    device.add_common_properties(
                        label=device_iri,
                        device_identifier=device_identifier[1],
                        device_address=device_address,
                        vendor_id=i_am.vendorID
                    )

                    for subnet in self.subnets:
                        if ip in subnet:
                            not_in_subnet_list = False
                            self.bbmd_in_subnet[subnet] = device_iri
                            device.add_component_properties(subnet=subnet)
                            break
                    
                    if not_in_subnet_list:
                        device_subnet = ipaddress.ip_network(f"{ip}/24", strict=False)
                        device.add_component_properties(subnet=device_subnet)

                except ValueError:
                    device = BACnetNode(graph, device_iri, DeviceTypeHandler, [NetworkComponent])
                    device.add_common_properties(
                        label=device_iri,
                        device_identifier=device_identifier[1],
                        device_address=device_address,
                        vendor_id=i_am.vendorID
                    )
                    device.add_component_properties(network_id = device_address.addrNet)

                
            track_lower = track_upper + 1
        _log.debug("get_device_objects Completed")

    def set_subnet_network(self, graph: Graph) -> None:
        """
        Set the subnet and network information in the graph
        """
        _log.debug("set_subnet_network")
        for subnet in self.subnets:
            if subnet in self.bbmd_in_subnet:
                self.scanner_node.add_component_properties(device_iri = self.bbmd_in_subnet[subnet])
            else:
                self.scanner_node.add_component_properties(subnet=subnet)
            BACnetNode(graph, BACnetURI["//subnet/"+str(subnet)], SubnetTypeHandler, [AttachDeviceComponent])

        for net in self.get_networks_from_graph(graph):
            BACnetNode(graph, BACnetURI["//network/"+str(net)], NetworkTypeHandler, [AttachDeviceComponent])

        _log.debug("set_subnet_network Completed")

        

    