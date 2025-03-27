"""
File contains the bacpypes3_scanner class which is used to scan the network for devices and routers.
"""
import argparse
import rdflib
import ipaddress
import gevent
import logging
import asyncio

from typing import Set, List, Union
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
from bacpypes3.ipv4.service import BVLLServiceAccessPoint
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
        task = asyncio.ensure_future(
            self.request(ReadBroadcastDistributionTable(destination=address))
        )
        try:
            result = asyncio.wait_for(self.read_bdt_future, timeout=5)
            return result
        except Exception as e:
            _log.error(f"Error in reading BDT: {e}")
            task.cancel()
            self.read_bdt_future.cancel()
            return None

    def read_foreign_device_table(self, address: IPv4Address) -> asyncio.Future:
        self.read_fdt_future = asyncio.Future()
        task = asyncio.ensure_future(self.request(ReadForeignDeviceTable(destination=address)))
        try:
            result = asyncio.wait_for(self.read_fdt_future, timeout=5)
            return result
        except Exception as e:
            _log.error(f"Error in reading FDT: {e}")
            task.cancel()
            self.read_fdt_future.cancel()
            return None

class bacpypes3_scanner:
    def __init__(self, bacpypes_settings: dict, prev_graph: Graph, bbmds: List[str], subnets: List[str], 
            device_broadcast_empty_step_size: int = 1000, device_broadcast_full_step_size: int = 100,
            scan_low_limit: int = 0, scan_high_limit:int = 4194303) -> None:
        """
        Initialize the BACpypes3 scanner with the settings
        """
        _log.debug("bacpypes3_scanner: init")
        self.bacpypes_settings = bacpypes_settings
        self.prev_graph = prev_graph
        self.app_settings = bacpypes_settings
        self.bbmds = [ipaddress.ip_address(bbmd) for bbmd in bbmds]
        self.subnets = [ipaddress.ip_network(subnet, strict = False) for subnet in subnets]
        self.device_broadcast_empty_step_size = device_broadcast_empty_step_size
        self.device_broadcast_full_step_size = device_broadcast_full_step_size
        self.scanner_node = None
        self.low_limit = scan_low_limit
        self.high_limit = scan_high_limit
        self.bbmd_in_subnet = {}
        self.scanned_networks = set()
        self.scanned_bbmds = []
        self.scanned_ipaddress_bbmd = {}
        self.scanned_bbmds_bdt = {}
        self.scanned_bbmds_fdt = {}

    async def set_application(self, graph: Graph)->Application:
        """
        Set the application address for the BACnet analysis
        """
        _log.debug("bacpypes3_scanner: set_application")
        settings = self.bacpypes_settings.copy()
        bbmd_ips = self.get_bbmd_ips(graph)
        settings['bbmd'] = self.bacpypes_settings.get('bbmd', None)
        app_settings = argparse.Namespace(**self.bacpypes_settings)
        _log.debug(f"Application config: {app_settings}")
        return Application.from_args(app_settings)

    def get_networks_from_graph(self, g: rdflib.Graph) -> Set[int]:
        """Return a set of network numbers from the graph"""
        _log.debug("bacpypes3_scanner: get_networks_from_graph")
        networks = set()
        for t in g.triples((None, RDF.type, BACnetNS["Network"])):
            networks.add(int(t[0].split('/')[-1]))
        return networks
    
    def get_bbmd_ips(self, g: rdflib.Graph) -> Set[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """Return a set of BBMD IPs from the graph"""
        _log.debug("bacpypes3_scanner: get_bbmd_ips")
        bbmd_ips = set()
        for t in g.triples((None, RDF.type, BACnetNS["BBMD"])):
            for t2 in g.triples((t[0], BACnetNS["device-address"], None)):
                try:
                    ip = ipaddress.ip_address(t2[2].value)
                    bbmd_ips.add(ip)
                except:
                    pass
        return bbmd_ips

    def get_device_ips(self, g: rdflib.Graph) -> Set[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """Return a set of device IPs from the graph"""
        _log.debug("bacpypes3_scanner: get_device_ips")
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
        _log.debug("bacpypes3_scanner: set_scanner_node")
        scanner_node = BACnetNode(graph, BACnetURI["//Grasshopper"], DeviceTypeHandler(), [AttachDeviceComponent(), SubnetComponent()])
        scanner_node.add_common_properties(
            label=BACnetURI[self.bacpypes_settings['name']],
            device_identifier=BACnetURI[self.bacpypes_settings['instance']],
            device_address=BACnetURI[self.bacpypes_settings['address']],
            vendor_id=BACnetURI[self.bacpypes_settings['vendoridentifier']]
        )
        scanner_ip = ipaddress.ip_address(self.bacpypes_settings['address'].split(':')[0].split('/')[0])
        await self.add_subnet_to_device(scanner_node, scanner_ip)
        self.scanner_node = scanner_node
    
    async def get_device_and_router(self, graph: Graph) -> None:
        _log.debug("Running Async for Who Is and Router to network")
        app = await self.set_application(graph)
        local_adapter = app.nsap.local_adapter
        sap = local_adapter.clientPeer
        assert isinstance(sap, BVLLServiceAccessPoint)
        ase = BVLLServiceElement()
        bind(ase, sap)
        await self.set_scanner_node(graph)
        await self.get_device_objects(app, ase, graph)
        await self.get_router_networks(app, graph)
        for bbmd in self.bbmds:
            await self.read_bbmd_fdt(ase, bbmd)
        await self.set_subnet_network(graph)
        app.close()
    
    async def get_router_networks(self, app: Application, graph:Graph) -> None:
        """
        Get the router to network information from the network for the graph.
        Who_is_router_to_network is called based on individual networks found existing in the graph from device broadcast to prevent overloading the system.
        Valid network ranges go from 1 to 65,534
        """
        _log.debug("bacpypes3_scanner: get_router_networks")
        for network_id in self.scanned_networks:
            gevent.sleep(0)
            _log.debug(f"Currently Processing network {network_id}")
            routers = await app.nse.who_is_router_to_network(network=network_id)
            for adapter, i_am_router_to_network in routers:
                _log.debug(f"adapter: {adapter} i_am_router_to_network: {i_am_router_to_network}")
                router_pdu_source = i_am_router_to_network.pduSource
                router_iri = BACnetURI["//router/"+str(router_pdu_source)]
                router_node = BACnetNode(graph, router_iri, RouterTypeHandler(), [SubnetComponent(), NetworkComponent()])
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

    async def check_if_device_is_bbmd(self, ase:BVLLServiceElement, device_address: Address) -> bool:
        """
        Check if the device is a BBMD
        """
        _log.debug("bacpypes3_scanner: check_if_device_is_bbmd")
        gevent.sleep(0)
        try:
            bdt = await ase.read_broadcast_distribution_table(device_address)
            if bdt is not None:
                self.scanned_bbmds_bdt[ipaddress.ip_address(device_address)] = [ipaddress.ip_address(bdt_entry) for bdt_entry in bdt]
                return True
        except Exception as e:
            pass
        _log.debug("check_if_device_is_bbmd Completed")
        return False
    
    async def read_bbmd_fdt(self, ase:BVLLServiceElement, device_address: Address) -> None:
        """
        Check if the device is a BBMD
        """
        _log.debug("bacpypes3_scanner: read_bbmd_fdt")
        gevent.sleep(0)
        try:
            fdt = await ase.read_broadcast_distribution_table(device_address)
            if fdt is not None:
                self.scanned_bbmds_fdt[device_address] = fdt
        except Exception as e:
            pass

    async def add_subnet_to_device(self, device: BACnetNode, ip: Address) -> ipaddress.IPv4Network:
        # Handles subnet information
        device_subnet = None
        for subnet in self.subnets:
            if ip in subnet:
                device_subnet = subnet
                device.add_component_properties(subnet=subnet)
                break
        
        if not device_subnet:
            device_subnet = ipaddress.ip_network(f"{ip}/24", strict=False)
            device.add_component_properties(subnet=device_subnet)
            self.subnets.append(device_subnet)

        return device_subnet
    
    async def get_device_objects(self, app: Application, ase:BVLLServiceElement, graph: Graph) -> None:
        """
        Get the device objects from the network for the graph
        """
        _log.debug("bacpypes3_scanner: get_device_objects")

        def get_known_device_end_range(graph: Graph, start_pos: int) -> int:
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
            track_upper = get_known_device_end_range(self.prev_graph, track_lower)
            if track_upper > self.high_limit:
                track_upper = self.high_limit
            
            try:
                i_ams = await app.who_is(track_lower, track_upper)
            except Exception as e:
                _log.error(f"Error in Who Is: {e}")
                track_lower = track_upper + 1
                continue

            _log.debug(f"Finished Scanning for devices at {track_lower}")

            for i_am in i_ams:
                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
                device_iri = BACnetURI["//" + str(device_identifier[1])]
                try:
                    ip = ipaddress.ip_address(device_address)
                    
                    # Check if device is a BBMD
                    if await self.check_if_device_is_bbmd(ase, device_address) or ip in self.bbmds:
                        device = BACnetNode(graph, device_iri, BBMDTypeHandler(), [SubnetComponent(), AttachDeviceComponent()])
                    else:
                        device = BACnetNode(graph, device_iri, DeviceTypeHandler(), [SubnetComponent()])
                    
                    device.add_common_properties(
                        label=device_iri,
                        device_identifier=device_identifier[1],
                        device_address=device_address,
                        vendor_id=i_am.vendorID
                    )

                    device_subnet = await self.add_subnet_to_device(device, device_address)

                    if isinstance(device.device.type_handler, BBMDTypeHandler):
                        self.bbmd_in_subnet[device_subnet] = device_iri
                        self.scanned_bbmds.append(device)
                        self.scanned_ipaddress_bbmd[ip] = device

                except ValueError:
                    device = BACnetNode(graph, device_iri, DeviceTypeHandler(), [NetworkComponent()])
                    device.add_common_properties(
                        label=device_iri,
                        device_identifier=device_identifier[1],
                        device_address=device_address,
                        vendor_id=i_am.vendorID
                    )
                    device.add_component_properties(network_id = device_address.addrNet)
                    self.scanned_networks.add(device_address.addrNet)

                
            track_lower = track_upper + 1
        _log.debug("get_device_objects Completed")

    async def set_subnet_network(self, graph: Graph) -> None:
        """
        Set the subnet and network information in the graph
        """
        _log.debug("bacpypes3_scanner: set_subnet_network")
        for subnet in self.subnets:
            BACnetNode(graph, BACnetURI["//subnet/"+str(subnet)], SubnetTypeHandler(), [AttachDeviceComponent()])

        for net in self.scanned_networks:
            BACnetNode(graph, BACnetURI["//network/"+str(net)], NetworkTypeHandler(), [AttachDeviceComponent()])

        try:
            for bbmd_ipaddress, bdt in self.scanned_bbmds_bdt.items():
                bbmd:BACnetNode = self.scanned_ipaddress_bbmd[bbmd_ipaddress]
                for bdt_entry in bdt:
                    if bdt_entry in self.scanned_ipaddress_bbmd:
                        bdt_entry_bbmd:BACnetNode = self.scanned_ipaddress_bbmd[bdt_entry]
                        bbmd.add_component_properties(device_iri = bdt_entry_bbmd.node_iri)
        except Exception as e:
            _log.error(f"Error in setting BDT: {e}")

        _log.debug(f"scanned_bbmds_bdt: {self.scanned_bbmds_bdt}")
        _log.debug(f"scanned_bbmds_fdt: {self.scanned_bbmds_fdt}")
        _log.debug("set_subnet_network Completed")

        

    