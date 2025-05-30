"""
File contains the bacpypes3_scanner class which is used to scan the network for devices and routers.
"""

import argparse
import asyncio
import ipaddress
import logging
from typing import Any, List, Set, Union

import gevent
import rdflib
from bacpypes3.app import Application
from bacpypes3.comm import ApplicationServiceElement, bind
from bacpypes3.ipv4.bvll import (
    LPDU,
    ReadBroadcastDistributionTable,
    ReadBroadcastDistributionTableAck,
    ReadForeignDeviceTable,
    ReadForeignDeviceTableAck,
)
from bacpypes3.ipv4.service import BVLLServiceAccessPoint
from bacpypes3.pdu import Address, IPv4Address, IPv6Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI
from rdflib import RDF, Graph, Literal, Namespace  # type: ignore
from rdflib.compare import graph_diff, to_isomorphic
from rdflib.extras.external_graph_libs import (
    rdflib_to_networkx_digraph,
    rdflib_to_networkx_graph,
)
from rdflib.namespace import RDFS
from volttron.platform.agent import utils

from .rdf_components import (
    AttachDeviceComponent,
    BACnetNode,
    BBMDNode,
    BBMDTypeHandler,
    DeviceNode,
    DeviceTypeHandler,
    NetworkComponent,
    NetworkNode,
    NetworkTypeHandler,
    RouterNode,
    RouterTypeHandler,
    SubnetComponent,
    SubnetNode,
    SubnetTypeHandler,
)

_log = logging.getLogger(__name__)
utils.setup_logging()


class BVLLServiceElement(ApplicationServiceElement):
    """
    A service element for handling BACnet Virtual Link Layer (BVLL) messages.

    This class extends ApplicationServiceElement to process BVLL messages like
    read broadcast distribution table (BDT) and foreign device table (FDT) requests.
    It provides asynchronous interfaces for these operations.
    """

    def __init__(self):
        """
        Initialize the BVLLServiceElement with empty future dictionaries.

        The dictionaries track pending requests for BDT and FDT operations.
        """
        self.read_bdt_future = {}  # Maps addresses to futures for BDT responses
        self.read_fdt_future = {}  # Maps addresses to futures for FDT responses

    async def confirmation(self, pdu: LPDU):
        """
        Process incoming BVLL confirmations.

        This method handles responses to BDT and FDT read requests by resolving
        the appropriate future with the received data.

        Args:
            pdu (LPDU): The received protocol data unit
        """
        if isinstance(pdu, ReadBroadcastDistributionTableAck):
            if self.read_bdt_future.get(pdu.pduSource):
                self.read_bdt_future[pdu.pduSource].set_result(pdu.bvlciBDT)
                del self.read_bdt_future[pdu.pduSource]

        elif isinstance(pdu, ReadForeignDeviceTableAck):
            if self.read_fdt_future.get(pdu.pduSource):
                self.read_fdt_future[pdu.pduSource].set_result(pdu.bvlciFDT)
                del self.read_fdt_future[pdu.pduSource]

    def create_future_request(
        self, destination: Address, request_class
    ) -> asyncio.Future:
        """
        Create a future for a BVLL request.

        This method creates and schedules an asynchronous request to a BACnet device.

        Args:
            destination (Address): The address of the target device
            request_class: The class of the request to create (e.g., ReadBroadcastDistributionTable)

        Returns:
            asyncio.Future: A future representing the pending request
        """
        task: asyncio.Future = asyncio.ensure_future(
            self.request(request_class(destination=destination))
        )
        return task

    async def create_and_await_request(
        self, destination: Address, request_class, request_registry: dict, timeout=5
    ):
        """
        Create a BVLL request and await its completion.

        This method creates a request, registers a future for its response, sends the request,
        and waits for the response with a timeout. It also includes error handling and cleanup.

        Args:
            destination (Address): The address of the target device
            request_class: The class of the request to create
            request_registry (dict): Dictionary mapping addresses to response futures
            timeout (int, optional): Timeout in seconds. Defaults to 5.

        Returns:
            Any: The response data if successful, None if timeout or error
        """
        result_future: asyncio.Future = asyncio.Future()
        request_registry[destination] = result_future
        task = self.create_future_request(destination, request_class)
        try:
            await asyncio.wait_for(task, timeout)
            result = await asyncio.wait_for(result_future, timeout)
            return result
        except asyncio.TimeoutError:
            _log.error(
                f"Timeout while waiting for {request_class.__name__} response from {destination}"
            )
            return None
        except Exception as e:
            _log.error(f"Error in {request_class.__name__} request: {e}")
            return None
        finally:
            if not task.done():
                task.cancel()
            else:
                try:
                    task.exception()
                except (asyncio.CancelledError, asyncio.InvalidStateError) as e:
                    _log.error(f"Task was cancelled or invalid state: {task}: {e}")

            if destination in request_registry:
                del request_registry[destination]

    async def read_broadcast_distribution_table(self, address: IPv4Address, timeout=5):
        """
        Read the Broadcast Distribution Table (BDT) from a BBMD device.

        This method sends a ReadBroadcastDistributionTable request to a device
        and waits for the response containing the BDT entries.

        Args:
            address (IPv4Address): The address of the BBMD device
            timeout (int, optional): Timeout in seconds. Defaults to 5.

        Returns:
            list: The Broadcast Distribution Table entries if successful, None otherwise
        """
        return await self.create_and_await_request(
            address, ReadBroadcastDistributionTable, self.read_bdt_future, timeout
        )

    async def read_foreign_device_table(self, address: IPv4Address, timeout=5):
        """
        Read the Foreign Device Table (FDT) from a BBMD device.

        This method sends a ReadForeignDeviceTable request to a device
        and waits for the response containing the FDT entries.

        Args:
            address (IPv4Address): The address of the BBMD device
            timeout (int, optional): Timeout in seconds. Defaults to 5.

        Returns:
            list: The Foreign Device Table entries if successful, None otherwise
        """
        return await self.create_and_await_request(
            address, ReadForeignDeviceTable, self.read_fdt_future, timeout
        )


class bacpypes3_scanner:
    """
    Scanner for discovering and mapping BACnet networks and devices.

    This class provides functionality to scan BACnet networks, discover devices and routers,
    and build an RDF graph representation of the network topology. It uses the BACpypes3
    library for BACnet communication.
    """

    def __init__(
        self,
        bacpypes_settings: dict,
        prev_graph: Graph,
        bbmds: List[str],
        subnets: List[str],
        device_broadcast_empty_step_size: int = 1000,
        device_broadcast_full_step_size: int = 100,
        scan_low_limit: int = 0,
        scan_high_limit: int = 4194303,
    ) -> None:
        """
        Initialize the BACpypes3 scanner with the given settings.

        Args:
            bacpypes_settings (dict): BACpypes application configuration settings
            prev_graph (Graph): Previous RDF graph of the network (for incremental scanning)
            bbmds (List[str]): List of BBMD IP addresses to scan
            subnets (List[str]): List of subnet CIDR notations to scan
            device_broadcast_empty_step_size (int, optional): Step size for scanning when few devices
                are expected. Defaults to 1000.
            device_broadcast_full_step_size (int, optional): Step size for scanning when many devices
                are expected. Defaults to 100.
            scan_low_limit (int, optional): Lower limit of device instance numbers to scan.
                Defaults to 0.
            scan_high_limit (int, optional): Upper limit of device instance numbers to scan.
                Defaults to 4194303.
        """
        _log.debug("bacpypes3_scanner: init")
        self.bacpypes_settings = bacpypes_settings
        self.prev_graph = prev_graph
        self.app_settings = bacpypes_settings
        self.bbmds = [ipaddress.ip_address(bbmd) for bbmd in bbmds]
        self.subnets = [
            ipaddress.ip_network(subnet, strict=False) for subnet in subnets
        ]
        self.device_broadcast_empty_step_size = device_broadcast_empty_step_size
        self.device_broadcast_full_step_size = device_broadcast_full_step_size
        self.scanner_node: DeviceNode
        self.low_limit = scan_low_limit
        self.high_limit = scan_high_limit
        self.bbmd_in_subnet: dict[
            Union[ipaddress.IPv4Network, ipaddress.IPv6Network], str
        ] = {}
        self.scanned_networks: set[int] = set()
        self.scanned_bbmds: list[BBMDNode] = []
        self.scanned_ipaddress_bbmd: dict[ipaddress.IPv4Address, BBMDNode] = {}
        self.scanned_bbmds_bdt: dict[
            ipaddress.IPv4Address, list[ipaddress.IPv4Address]
        ] = {}
        self.scanned_bbmds_fdt: dict[Address, Any] = {}

    async def set_application(self, graph: Graph) -> Application:
        """
        Set the application address for the BACnet analysis
        """
        _log.debug("bacpypes3_scanner: set_application")
        settings = self.bacpypes_settings.copy()
        bbmd_ips = self.get_bbmd_ips(graph)
        settings["bbmd"] = self.bacpypes_settings.get("bbmd", None)
        app_settings = argparse.Namespace(**self.bacpypes_settings)
        _log.debug(f"Application config: {app_settings}")
        return Application.from_args(app_settings)

    def get_networks_from_graph(self, g: rdflib.Graph) -> Set[int]:
        """Return a set of network numbers from the graph"""
        _log.debug("bacpypes3_scanner: get_networks_from_graph")
        networks = set()
        for t in g.triples((None, RDF.type, BACnetNS["Network"])):
            networks.add(int(t[0].split("/")[-1]))
        return networks

    def get_bbmd_ips(
        self, g: rdflib.Graph
    ) -> Set[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
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

    def get_device_ips(
        self, g: rdflib.Graph
    ) -> Set[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
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

    async def set_scanner_node(self, graph: Graph):
        """
        Set the scanner node in the graph
        """
        _log.debug("bacpypes3_scanner: set_scanner_node")
        scanner_node = DeviceNode(graph, BACnetURI["//Grasshopper"])
        scanner_node.add_properties(
            label=BACnetURI[self.bacpypes_settings["name"]],
            device_identifier=BACnetURI[self.bacpypes_settings["instance"]],
            device_address=BACnetURI[self.bacpypes_settings["address"]],
            vendor_id=BACnetURI[self.bacpypes_settings["vendoridentifier"]],
        )
        scanner_ip = ipaddress.ip_address(
            self.bacpypes_settings["address"].split(":")[0].split("/")[0]
        )
        await self.add_subnet_to_device(scanner_node, scanner_ip)
        self.scanner_node = scanner_node

    async def get_device_and_router(self, graph: Graph) -> None:
        """
        Main scanning method that discovers devices and routers on the BACnet network.

        This method performs the complete scanning process:
        1. Sets up the BACnet application
        2. Creates the scanner node in the graph
        3. Discovers devices on the network
        4. Discovers routers and their networks
        5. Reads BBMD tables
        6. Updates the graph with subnet and network information

        Args:
            graph (Graph): The RDF graph to populate with discovered devices and topology

        Returns:
            None
        """
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

    async def get_router_networks(self, app: Application, graph: Graph) -> None:
        """
        Discover routers and their connected networks on the BACnet internetwork.

        This method sends Who-Is-Router-To-Network requests for each network ID that
        has been discovered during device scanning. It creates Router nodes in the graph
        for each discovered router and associates them with their networks.

        Who-is-router-to-network is called for individual networks found existing in
        the graph from device broadcasts to prevent overloading the network.
        Valid network ranges go from 1 to 65,534.

        Args:
            app (Application): The BACnet application object
            graph (Graph): The RDF graph to populate with router information

        Returns:
            None
        """
        _log.debug("bacpypes3_scanner: get_router_networks")
        for network_id in self.scanned_networks:
            _log.debug(f"Currently Processing network {network_id}")
            routers = await app.nse.who_is_router_to_network(network=network_id)
            for adapter, i_am_router_to_network in routers:
                _log.debug(
                    f"adapter: {adapter} i_am_router_to_network: {i_am_router_to_network}"
                )
                router_pdu_source = i_am_router_to_network.pduSource
                router_iri = BACnetURI["//router/" + str(router_pdu_source)]
                router_node = RouterNode(graph, router_iri)
                for net in i_am_router_to_network.iartnNetworkList:
                    router_node.add_properties(network_id=net)

                ip = ipaddress.ip_address(router_pdu_source)
                not_in_network = True
                for subnet in self.subnets:
                    if ip in subnet:
                        not_in_network = False
                        router_node.add_properties(subnet=subnet)
                if not_in_network:
                    self.scanner_node.add_properties(device_iri=router_iri)

        _log.debug("get_router_networks Completed")

    async def check_if_device_is_bbmd(
        self, ase: BVLLServiceElement, device_address: Address
    ) -> bool:
        """
        Check if a device is a BBMD by attempting to read its Broadcast Distribution Table.

        This method tries to read the BDT from the device. If successful, it stores the BDT
        entries and identifies the device as a BBMD.

        Args:
            ase (BVLLServiceElement): The BVLL service element for sending the request
            device_address (Address): The address of the device to check

        Returns:
            bool: True if the device is a BBMD, False otherwise
        """
        _log.debug("bacpypes3_scanner: check_if_device_is_bbmd")
        try:
            bdt = await ase.read_broadcast_distribution_table(device_address)
            ip = ipaddress.ip_address(device_address)
            if bdt is not None and isinstance(ip, ipaddress.IPv4Address):
                self.scanned_bbmds_bdt[ip] = [
                    ipaddr
                    for bdt_entry in bdt
                    for ipaddr in [ipaddress.ip_address(bdt_entry)]
                    if isinstance(ipaddr, ipaddress.IPv4Address)
                ]
                return True
        except Exception as e:
            pass
        _log.debug("check_if_device_is_bbmd Completed")
        return False

    async def read_bbmd_fdt(
        self, ase: BVLLServiceElement, device_address: Address
    ) -> None:
        """
        Read the Foreign Device Table from a BBMD device.

        This method attempts to read the FDT from a device and stores it
        if successful. The FDT contains information about foreign devices
        registered with this BBMD.

        Args:
            ase (BVLLServiceElement): The BVLL service element for sending the request
            device_address (Address): The address of the BBMD device

        Returns:
            None
        """
        _log.debug("bacpypes3_scanner: read_bbmd_fdt")
        try:
            fdt = await ase.read_broadcast_distribution_table(device_address)
            if fdt is not None:
                self.scanned_bbmds_fdt[device_address] = fdt
        except Exception as e:
            pass

    async def add_subnet_to_device(
        self, device: BACnetNode, ip: Address
    ) -> Union[ipaddress.IPv4Network, ipaddress.IPv6Network]:
        """
        Associate a device with its subnet based on its IP address.

        This method finds which subnet the device belongs to based on its IP address.
        If the device doesn't match any known subnet, a new /24 subnet is created
        and added to the list of known subnets.

        Args:
            device (BACnetNode): The device node to associate with a subnet
            ip (Address): The IP address of the device

        Returns:
            Union[ipaddress.IPv4Network, ipaddress.IPv6Network]: The subnet the device belongs to
        """
        # Handles subnet information
        device_subnet = None
        for subnet in self.subnets:
            if ip in subnet:
                device_subnet = subnet
                device.add_properties(subnet=subnet)
                break

        if not device_subnet:
            device_subnet = ipaddress.ip_network(f"{ip}/24", strict=False)
            device.add_properties(subnet=device_subnet)
            self.subnets.append(device_subnet)

        return device_subnet

    async def get_device_objects(
        self, app: Application, ase: BVLLServiceElement, graph: Graph
    ) -> None:
        """
        Discover BACnet devices on the network and add them to the graph.

        This method sends Who-Is broadcasts to discover devices within the configured
        instance ID range. For each discovered device, it:
        1. Creates a Device or BBMD node in the graph
        2. Adds device properties (ID, address, vendor ID)
        3. Associates the device with its subnet
        4. Checks if the device is a BBMD by attempting to read its BDT

        The method uses an adaptive scanning approach, adjusting the scan range based on
        the density of devices in previous scans to optimize network traffic.

        Args:
            app (Application): The BACnet application object
            ase (BVLLServiceElement): The BVLL service element for BBMD operations
            graph (Graph): The RDF graph to populate with device information

        Returns:
            None
        """
        _log.debug("bacpypes3_scanner: get_device_objects")

        def get_known_device_end_range(graph: Graph, start_pos: int) -> int:
            """
            Determine the optimal upper bound for the next Who-Is request.

            This helper function analyzes the existing graph to find an appropriate
            upper bound for the next device scan range. It helps optimize scanning
            by using smaller steps in device-dense areas and larger steps in sparse areas.

            Args:
                graph (Graph): The RDF graph containing previously discovered devices
                start_pos (int): The starting device instance ID for this range

            Returns:
                int: The ending device instance ID for this range
            """
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
                    ip: Union[IPv4Address, IPv6Address] = ipaddress.ip_address(
                        device_address
                    )
                    device: Union[BBMDNode, DeviceNode]
                    if (
                        await self.check_if_device_is_bbmd(ase, device_address)
                        or ip in self.bbmds
                    ):
                        device = BBMDNode(graph, device_iri)
                    else:
                        device = DeviceNode(graph, device_iri)

                    device.add_properties(
                        label=device_iri,
                        device_identifier=device_identifier[1],
                        device_address=device_address,
                        vendor_id=i_am.vendorID,
                    )

                    device_subnet = await self.add_subnet_to_device(
                        device, device_address
                    )

                    if isinstance(device, BBMDNode):
                        self.bbmd_in_subnet[device_subnet] = device_iri
                        self.scanned_bbmds.append(device)
                        self.scanned_ipaddress_bbmd[ip] = device
                except ValueError:
                    device = DeviceNode(graph, device_iri)
                    device.add_properties(
                        label=device_iri,
                        device_identifier=device_identifier[1],
                        device_address=device_address,
                        vendor_id=i_am.vendorID,
                        network_id=device_address.addrNet,
                    )
                    self.scanned_networks.add(device_address.addrNet)

            track_lower = track_upper + 1
        _log.debug("get_device_objects Completed")

    async def set_subnet_network(self, graph: Graph) -> None:
        """
        Create subnet and network nodes in the graph and establish relationships.

        This method creates nodes for all discovered subnets and networks in the graph.
        It also establishes relationships between BBMD devices based on their BDT entries.

        Args:
            graph (Graph): The RDF graph to update with subnet and network information

        Returns:
            None
        """
        _log.debug("bacpypes3_scanner: set_subnet_network")
        for subnet in self.subnets:
            SubnetNode(graph, BACnetURI["//subnet/" + str(subnet)])

        for net in self.scanned_networks:
            NetworkNode(graph, BACnetURI["//network/" + str(net)])

        try:
            for bbmd_ipaddress, bdt in self.scanned_bbmds_bdt.items():
                bbmd: BBMDNode = self.scanned_ipaddress_bbmd[bbmd_ipaddress]
                for bdt_entry in bdt:
                    if bdt_entry in self.scanned_ipaddress_bbmd:
                        bdt_entry_bbmd: BBMDNode = self.scanned_ipaddress_bbmd[
                            bdt_entry
                        ]
                        bbmd.add_properties(device_iri=bdt_entry_bbmd.node_iri)
        except Exception as e:
            _log.debug(f"scanned_bbmds_fdt: {self.scanned_bbmds_fdt}")
            _log.error(f"Error in setting BDT: {e}")

        _log.debug(f"scanned_bbmds_bdt: {self.scanned_bbmds_bdt}")
        _log.debug(f"scanned_bbmds_fdt: {self.scanned_bbmds_fdt}")
        _log.debug("set_subnet_network Completed")
