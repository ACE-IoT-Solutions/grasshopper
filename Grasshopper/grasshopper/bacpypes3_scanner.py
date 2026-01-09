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
    DeviceRouterNode,
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
        scavenge_enabled: bool = True,
        scavenge_margin: int = 10,
        scavenge_max_range: int = 25,
        scavenge_gap_threshold: int = 5,
        scavenge_gap_max_range: int = None,
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
            scavenge_enabled (bool, optional): Enable scavenge scanning for optimization.
                Defaults to True.
            scavenge_margin (int, optional): Device IDs before/after each block to scan.
                Defaults to 10.
            scavenge_max_range (int, optional): Max device IDs per WhoIs for margin scans.
                Defaults to 25.
            scavenge_gap_threshold (int, optional): Gap size to merge contiguous blocks.
                Defaults to 5.
            scavenge_gap_max_range (int, optional): Max range for gap scans (None = entire gap).
                Defaults to None.
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
        self.scanned_device_ips: dict[
            Union[ipaddress.IPv4Address, ipaddress.IPv6Address], BACnetNode
        ] = {}
        
        # Scavenge scan configuration
        self.scavenge_enabled = scavenge_enabled
        self.scavenge_margin = scavenge_margin
        self.scavenge_max_range = scavenge_max_range
        self.scavenge_gap_threshold = scavenge_gap_threshold
        self.scavenge_gap_max_range = scavenge_gap_max_range

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

    def _find_contiguous_blocks(self, device_ids: List[int]) -> List[tuple[int, int]]:
        """
        Find contiguous blocks of device IDs, merging small gaps.

        Args:
            device_ids: List of device IDs to analyze

        Returns:
            List of (start, end) tuples representing contiguous blocks
        """
        if not device_ids:
            return []

        # Sort device IDs
        sorted_ids = sorted(device_ids)
        blocks = []
        block_start = sorted_ids[0]
        block_end = sorted_ids[0]

        for device_id in sorted_ids[1:]:
            # Check if this ID extends the current block or starts a new one
            gap = device_id - block_end

            if gap <= self.scavenge_gap_threshold:
                # Small gap or continuous - extend current block
                block_end = device_id
            else:
                # Large gap - save current block and start new one
                blocks.append((block_start, block_end))
                block_start = device_id
                block_end = device_id

        # Add final block
        blocks.append((block_start, block_end))

        return blocks

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
                ip = ipaddress.ip_address(router_pdu_source)
                
                # Check if we already have a device at this IP address
                existing_device = self.scanned_device_ips.get(ip)
                
                if existing_device and isinstance(existing_device, DeviceNode):
                    # Convert existing device to a device+router by creating a new DeviceRouterNode
                    _log.debug(f"Merging device at {ip} into router")
                    
                    # Use the existing device's IRI (which is based on device instance, not IP)
                    device_iri = existing_device.node_iri
                    
                    # Extract device instance before removing triples from graph
                    device_instance = graph.value(subject=device_iri, predicate=BACnetNS["device-instance"])
                    
                    # Store all existing properties from the old device node
                    stored_properties = []
                    for predicate, obj in graph.predicate_objects(device_iri):
                        # Skip the type predicates since the new node will set the correct types
                        if predicate != RDF.type:
                            stored_properties.append((predicate, obj))
                    
                    # Remove the old device triples from the graph
                    graph.remove((device_iri, None, None))
                    
                    # Create a DeviceRouterNode to replace the DeviceNode
                    router_device_iri = BACnetURI["//router/" + str(device_instance)]
                    router_node = DeviceRouterNode(graph, router_device_iri)
                    
                    # Restore all the stored properties to the new node
                    for predicate, obj in stored_properties:
                        router_node.device.add_connection(predicate, obj)
                    
                    # Update our tracking
                    self.scanned_device_ips[ip] = router_node
                
                elif existing_device and isinstance(existing_device, (RouterNode, DeviceRouterNode)):
                    # Already a router or device+router, just use it
                    router_node = existing_device
                else:
                    # Create a standalone router node
                    router_iri = BACnetURI["//router/" + str(router_pdu_source)]
                    router_node = RouterNode(graph, router_iri)
                    self.scanned_device_ips[ip] = router_node
                
                for net in i_am_router_to_network.iartnNetworkList:
                    router_node.add_properties(network_id=net)

                not_in_network = True
                for subnet in self.subnets:
                    if ip in subnet:
                        not_in_network = False
                        router_node.add_properties(subnet=subnet)
                if not_in_network:
                    self.scanner_node.add_properties(device_iri=router_node.node_iri)
                
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
                    
                    # Track device by IP address for router merging
                    self.scanned_device_ips[ip] = device

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

    async def scavenge_scan(self, graph: Graph) -> None:
        """
        Perform scavenge scan around previously discovered devices from prev_graph.

        This method uses the previous day's graph to identify device blocks and performs
        targeted scans around those blocks instead of scanning the entire device ID range.

        Args:
            graph (Graph): The current RDF graph to populate with discovered devices

        Returns:
            None
        """
        if not self.scavenge_enabled:
            _log.info("Scavenge scan disabled, skipping")
            return

        _log.info("Starting scavenge scan using previous graph data")
        
        # Extract known device IDs from previous graph
        prev_device_ids = []
        for triple in self.prev_graph.triples((None, BACnetNS["device-instance"], None)):
            try:
                device_id = int(triple[2])
                prev_device_ids.append(device_id)
            except (ValueError, TypeError):
                continue

        if not prev_device_ids:
            _log.warning("No previous devices found in graph, falling back to full scan")
            await self.get_device_and_router(graph)
            return

        _log.info(f"Found {len(prev_device_ids)} devices in previous graph")

        # Find contiguous blocks of devices
        blocks = self._find_contiguous_blocks(prev_device_ids)
        _log.info(f"Identified {len(blocks)} device blocks from previous scan")

        # Set up the application for scanning
        app = await self.set_application(graph)
        local_adapter = app.nsap.local_adapter
        sap = local_adapter.clientPeer
        assert isinstance(sap, BVLLServiceAccessPoint)
        ase = BVLLServiceElement()
        bind(ase, sap)
        await self.set_scanner_node(graph)

        try:
            # Generate scavenge ranges
            scavenge_ranges = []

            # Determine scan boundaries
            absolute_low = self.low_limit
            absolute_high = self.high_limit

            # Check for gap BEFORE first block
            if blocks:
                first_block_start = blocks[0][0]
                pre_gap_end = first_block_start - self.scavenge_margin - 1
                pre_gap_size = pre_gap_end - absolute_low + 1

                if pre_gap_size > self.scavenge_gap_threshold:
                    _log.debug(f"Adding pre-scan gap: device IDs {absolute_low}-{pre_gap_end} ({pre_gap_size} IDs)")

                    # Use gap-specific max range
                    if self.scavenge_gap_max_range is None:
                        scavenge_ranges.append((absolute_low, pre_gap_end))
                    else:
                        current = absolute_low
                        while current <= pre_gap_end:
                            chunk_end = min(current + self.scavenge_gap_max_range - 1, pre_gap_end)
                            scavenge_ranges.append((current, chunk_end))
                            current = chunk_end + 1

                # Scan around each discovered block (±margin) and fill large gaps
                for i, (block_start, block_end) in enumerate(blocks):
                    # Add margin scan around this block
                    range_start = max(absolute_low, block_start - self.scavenge_margin)
                    range_end = min(absolute_high, block_end + self.scavenge_margin)

                    # Split into chunks if range is too large
                    current = range_start
                    while current <= range_end:
                        chunk_end = min(current + self.scavenge_max_range - 1, range_end)
                        scavenge_ranges.append((current, chunk_end))
                        current = chunk_end + 1

                    # Check for large gap to next block
                    if i < len(blocks) - 1:
                        gap_start = block_end + self.scavenge_margin + 1
                        gap_end = blocks[i + 1][0] - self.scavenge_margin - 1
                        gap_size = gap_end - gap_start + 1

                        # Only scan gaps larger than threshold
                        if gap_size > self.scavenge_gap_threshold:
                            _log.debug(f"Adding gap scan: device IDs {gap_start}-{gap_end} ({gap_size} IDs)")

                            # Use gap-specific max range
                            if self.scavenge_gap_max_range is None:
                                scavenge_ranges.append((gap_start, gap_end))
                            else:
                                current = gap_start
                                while current <= gap_end:
                                    chunk_end = min(current + self.scavenge_gap_max_range - 1, gap_end)
                                    scavenge_ranges.append((current, chunk_end))
                                    current = chunk_end + 1

                # Check for gap AFTER last block
                last_block_end = blocks[-1][1]
                post_gap_start = last_block_end + self.scavenge_margin + 1
                post_gap_size = absolute_high - post_gap_start + 1

                if post_gap_size > self.scavenge_gap_threshold:
                    _log.debug(f"Adding post-scan gap: device IDs {post_gap_start}-{absolute_high} ({post_gap_size} IDs)")

                    # Use gap-specific max range
                    if self.scavenge_gap_max_range is None:
                        scavenge_ranges.append((post_gap_start, absolute_high))
                    else:
                        current = post_gap_start
                        while current <= absolute_high:
                            chunk_end = min(current + self.scavenge_gap_max_range - 1, absolute_high)
                            scavenge_ranges.append((current, chunk_end))
                            current = chunk_end + 1

            _log.info(f"Performing {len(scavenge_ranges)} targeted scavenge scan(s)...")

            # Perform scavenge scans using existing device scanning logic
            for i, (low, high) in enumerate(scavenge_ranges, 1):
                _log.debug(f"Scavenge scan {i}/{len(scavenge_ranges)}: scanning device IDs {low}-{high}")
                
                try:
                    i_ams = await app.who_is(low, high)
                    
                    for i_am in i_ams:
                        device_address: Address = i_am.pduSource
                        device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
                        device_iri = BACnetURI["//" + str(device_identifier[1])]
                        
                        try:
                            ip: Union[IPv4Address, IPv6Address] = ipaddress.ip_address(device_address)
                            
                            # Skip if device already processed
                            if ip in self.scanned_device_ips:
                                continue
                            
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

                            device_subnet = await self.add_subnet_to_device(device, device_address)
                            
                            # Track device by IP address for router merging
                            self.scanned_device_ips[ip] = device

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

                except Exception as e:
                    _log.error(f"Error during scavenge scan {i}: {e}")

            # Discover routers and complete the scan
            await self.get_router_networks(app, graph)
            for bbmd in self.bbmds:
                await self.read_bbmd_fdt(ase, bbmd)
            await self.set_subnet_network(graph)

            _log.info("Scavenge scan completed successfully")

        finally:
            app.close()

    async def get_device_and_router_with_scavenge(self, graph: Graph) -> None:
        """
        Main scanning method that optionally uses scavenge scan for optimization.

        This method chooses between full scanning and scavenge scanning based on
        configuration and availability of previous graph data.

        Args:
            graph (Graph): The RDF graph to populate with discovered devices and topology

        Returns:
            None
        """
        if self.scavenge_enabled and self.prev_graph and len(self.prev_graph) > 0:
            _log.info("Using scavenge scan mode for optimized scanning")
            await self.scavenge_scan(graph)
        else:
            _log.info("Using full scan mode")
            await self.get_device_and_router(graph)
