"""
File contains the bacpypes3_scanner class which is used to scan the network for devices and routers.
"""

import asyncio
import ipaddress
import logging
from typing import Any, Dict, List, Optional, Set, Union

import netifaces

import gevent
import rdflib
from bacpypes3.app import Application
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.comm import ApplicationServiceElement, bind
from bacpypes3.local.device import DeviceObject
from bacpypes3.primitivedata import ObjectType
from bacpypes3.vendor import VendorInfo
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
        # Detect local subnet from system interfaces (or fall back to address config)
        self.local_subnet = self._parse_local_subnet_from_address(
            bacpypes_settings.get("address", "")
        )
        # If we detected a local subnet, ensure it's properly in our subnets list
        if self.local_subnet:
            # Remove any conflicting subnets (same network address but different prefix)
            # This handles cases where /24 was configured but actual network is larger
            conflicting = [
                s for s in self.subnets
                if s.network_address == self.local_subnet.network_address
                and s.prefixlen != self.local_subnet.prefixlen
            ]
            for conflict in conflicting:
                _log.info(
                    f"Removing conflicting subnet {conflict} in favor of "
                    f"detected local subnet {self.local_subnet}"
                )
                self.subnets.remove(conflict)

            # Add local subnet at the front if not already present
            if self.local_subnet not in self.subnets:
                self.subnets.insert(0, self.local_subnet)
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

    def _get_system_interfaces(self) -> List[Dict[str, Any]]:
        """
        Detect network interfaces from the operating system using netifaces.

        This is cross-platform (Linux, macOS, Windows, BSD) and avoids
        fragile subprocess/string parsing of ifconfig or ip addr output.

        Returns:
            List of dicts with 'interface', 'ip', 'prefix', and 'network' keys
            for each IPv4 interface (excluding loopback).
        """
        interfaces = []
        try:
            for iface_name in netifaces.interfaces():
                # Get IPv4 addresses for this interface
                addrs = netifaces.ifaddresses(iface_name).get(netifaces.AF_INET, [])
                for addr in addrs:
                    ip = addr.get("addr")
                    netmask = addr.get("netmask")
                    # Skip loopback and entries without IP/netmask
                    if not ip or not netmask or ip == "127.0.0.1":
                        continue
                    try:
                        # Convert netmask to prefix length
                        prefix = ipaddress.IPv4Network(
                            f"0.0.0.0/{netmask}"
                        ).prefixlen
                        network = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
                        interfaces.append(
                            {
                                "interface": iface_name,
                                "ip": ip,
                                "prefix": prefix,
                                "network": network,
                            }
                        )
                    except (ValueError, TypeError) as e:
                        _log.debug(
                            f"Failed to parse interface {iface_name}: "
                            f"ip={ip}, netmask={netmask}: {e}"
                        )
                        continue
        except Exception as e:
            _log.debug(f"Error detecting system network interfaces: {e}")

        if not interfaces:
            _log.debug("No network interfaces detected")

        return interfaces

    def _detect_local_subnet(
        self, scanner_ip: str
    ) -> Optional[ipaddress.IPv4Network]:
        """
        Detect the local subnet by finding the system interface matching the scanner IP.

        This queries the operating system's network interfaces to find the actual
        subnet mask for the interface that matches the scanner's IP address.

        Args:
            scanner_ip: The IP address of the scanner (without CIDR or port)

        Returns:
            The detected subnet, or None if detection fails.
        """
        try:
            target_ip = ipaddress.ip_address(scanner_ip)
        except ValueError:
            _log.debug(f"Invalid scanner IP: {scanner_ip}")
            return None

        interfaces = self._get_system_interfaces()

        # First, try exact IP match
        for iface in interfaces:
            if iface["ip"] == scanner_ip:
                _log.info(
                    f"Detected local subnet from interface {iface['interface']}: "
                    f"{iface['network']} (prefix /{iface['prefix']})"
                )
                return iface["network"]

        # Second, try to find an interface whose network contains the scanner IP
        for iface in interfaces:
            if target_ip in iface["network"]:
                _log.info(
                    f"Detected local subnet from interface {iface['interface']}: "
                    f"{iface['network']} (prefix /{iface['prefix']}) "
                    f"(scanner IP {scanner_ip} is in this network)"
                )
                return iface["network"]

        _log.debug(f"No matching interface found for scanner IP {scanner_ip}")
        return None

    def _parse_local_subnet_from_address(
        self, address: str
    ) -> Union[ipaddress.IPv4Network, ipaddress.IPv6Network, None]:
        """
        Determine the local subnet, preferring OS interface detection over config parsing.

        This method first tries to detect the actual network interface configuration
        from the operating system. If that fails, it falls back to parsing the CIDR
        from the scanner's address configuration.

        Args:
            address: The BACnet address string (e.g., "192.168.1.12/24:47808")

        Returns:
            The local subnet as an IPv4Network/IPv6Network, or None if detection fails.
        """
        if not address:
            return None

        try:
            # Extract IP from address (format: "IP/CIDR:PORT" or "IP:PORT")
            addr_part = address.split(":")[0] if ":" in address else address
            scanner_ip = addr_part.split("/")[0] if "/" in addr_part else addr_part

            # First, try to detect from system interfaces (most accurate)
            detected_subnet = self._detect_local_subnet(scanner_ip)
            if detected_subnet:
                return detected_subnet

            # Fall back to parsing CIDR from address config
            if "/" in addr_part:
                local_subnet = ipaddress.ip_network(addr_part, strict=False)
                _log.info(
                    f"Using subnet from address config: {local_subnet} "
                    "(could not detect from system interfaces)"
                )
                return local_subnet
            else:
                _log.warning(
                    f"Could not detect local subnet for {scanner_ip} "
                    "and no CIDR in address config"
                )
                return None
        except (ValueError, TypeError) as e:
            _log.warning(f"Failed to determine local subnet from '{address}': {e}")
            return None

    async def set_application(self, graph: Graph) -> Application:
        """
        Set the application address for the BACnet analysis
        """
        _log.debug("bacpypes3_scanner: set_application")
        settings = self.bacpypes_settings.copy()
        bbmd_ips = self.get_bbmd_ips(graph)
        settings["bbmd"] = self.bacpypes_settings.get("bbmd", None)

        # Register VendorInfo before creating Application (required for non-999 vendor IDs)
        vendorid = settings.get("vendoridentifier", 999)
        if vendorid != 999:
            try:
                vendor_info = VendorInfo(vendorid)
                # Register standard object classes so device has proper defaults
                vendor_info.register_object_class(ObjectType.device, DeviceObject)
                _log.debug(f"Registered VendorInfo for vendor ID {vendorid}")
            except RuntimeError as e:
                # Vendor ID may already be registered
                _log.debug(f"VendorInfo for vendor ID {vendorid} already registered: {e}")

        # Use SimpleArgumentParser to get proper bacpypes3 defaults
        parser = SimpleArgumentParser()
        args = parser.parse_args([])  # Parse empty args to get all defaults

        # Override defaults with our config values
        for key, value in settings.items():
            setattr(args, key, value)

        _log.debug(f"Application config: {args}")
        return Application.from_args(args)

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
            device_identifier=self.bacpypes_settings["instance"],
            device_address=self.bacpypes_settings["address"],
            vendor_id=self.bacpypes_settings["vendoridentifier"],
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
        If the device doesn't match any known subnet:
        - If we have a local subnet and the device is on the same network, use the
          local subnet's prefix length for accuracy
        - Otherwise, fall back to /24 for remote/unknown subnets

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
            # Determine the appropriate prefix length for this unknown subnet
            if self.local_subnet:
                # Use the local subnet's prefix length - this ensures devices
                # discovered on our local network get the correct subnet mask
                prefix_len = self.local_subnet.prefixlen
                _log.debug(
                    f"Using local subnet prefix /{prefix_len} for device {ip}"
                )
            else:
                # No local subnet info available, fall back to /24
                prefix_len = 24
                _log.debug(
                    f"No local subnet info, using default /24 for device {ip}"
                )

            device_subnet = ipaddress.ip_network(f"{ip}/{prefix_len}", strict=False)
            device.add_properties(subnet=device_subnet)
            self.subnets.append(device_subnet)

        return device_subnet

    async def read_device_properties(
        self,
        app: Application,
        device: Union["BBMDNode", "DeviceNode"],
        device_address: Address,
        device_identifier: ObjectIdentifier,
    ) -> None:
        """
        Read additional device properties (model_name, firmware_revision, device_name).

        This method reads optional device properties and adds them to the device node.
        Errors are logged but do not prevent device discovery from continuing.

        Args:
            app: The BACnet application object
            device: The device node to add properties to
            device_address: The device's network address
            device_identifier: The device's object identifier
        """
        device_obj_id = ObjectIdentifier(("device", device_identifier[1]))

        # Properties to read: BACnet property name -> RDF property name
        properties_to_read = {
            "object-name": "device-name",
            "model-name": "model-name",
            "firmware-revision": "firmware-revision",
        }

        for bacnet_prop, rdf_prop in properties_to_read.items():
            try:
                value = await asyncio.wait_for(
                    app.read_property(device_address, device_obj_id, bacnet_prop),
                    timeout=10.0,
                )
                if value is not None:
                    device.add_connection(BACnetNS[rdf_prop], Literal(str(value)))
                    _log.debug(
                        f"Read {bacnet_prop}={value} from device {device_identifier[1]}"
                    )
            except asyncio.TimeoutError:
                _log.debug(
                    f"Timeout reading {bacnet_prop} from device {device_identifier[1]}"
                )
            except Exception as e:
                _log.debug(
                    f"Could not read {bacnet_prop} from device {device_identifier[1]}: {e}"
                )

    async def read_device_object_signature(
        self,
        app: Application,
        device: Union["BBMDNode", "DeviceNode"],
        device_address: Address,
        device_identifier: ObjectIdentifier,
    ) -> None:
        """
        Read the object-list from a device and count objects by type.

        This method reads the object-list property from a BACnet device and
        creates a "signature" by counting how many objects of each type exist.
        These counts are added as RDF properties (e.g., "analog-input-count": 5).

        Args:
            app: The BACnet application object
            device: The device node to add signature properties to
            device_address: The device's network address
            device_identifier: The device's object identifier
        """
        device_obj_id = ObjectIdentifier(("device", device_identifier[1]))

        try:
            # Read the object-list property
            object_list = await asyncio.wait_for(
                app.read_property(device_address, device_obj_id, "object-list"),
                timeout=30.0,  # Longer timeout for potentially large lists
            )

            if object_list is None:
                _log.debug(
                    f"No object-list returned from device {device_identifier[1]}"
                )
                return

            # Count objects by type
            type_counts: Dict[str, int] = {}
            for obj_id in object_list:
                # obj_id is an ObjectIdentifier tuple (type, instance)
                obj_type = obj_id[0]
                # Convert to string representation (e.g., "analog-input")
                if hasattr(obj_type, 'attr'):
                    # It's an ObjectType enum, get the string name
                    type_name = str(obj_type.attr)
                elif isinstance(obj_type, str):
                    type_name = obj_type
                else:
                    type_name = str(obj_type)

                type_counts[type_name] = type_counts.get(type_name, 0) + 1

            # Add total object count
            total_count = len(object_list)
            device.add_connection(
                BACnetNS["object-count"], Literal(total_count)
            )
            _log.debug(
                f"Device {device_identifier[1]} has {total_count} total objects"
            )

            # Add count for each object type
            for type_name, count in type_counts.items():
                # Create property name like "analog-input-count"
                prop_name = f"{type_name}-count"
                device.add_connection(BACnetNS[prop_name], Literal(count))
                _log.debug(
                    f"Device {device_identifier[1]}: {type_name}={count}"
                )

        except asyncio.TimeoutError:
            _log.debug(
                f"Timeout reading object-list from device {device_identifier[1]}"
            )
        except Exception as e:
            _log.debug(
                f"Could not read object-list from device {device_identifier[1]}: {e}"
            )

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

                    # Read additional device properties (model_name, firmware_revision, device_name)
                    await self.read_device_properties(
                        app, device, device_address, device_identifier
                    )

                    # Read device object signature (object types and counts)
                    await self.read_device_object_signature(
                        app, device, device_address, device_identifier
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
                    # Read additional device properties (model_name, firmware_revision, device_name)
                    await self.read_device_properties(
                        app, device, device_address, device_identifier
                    )

                    # Read device object signature (object types and counts)
                    await self.read_device_object_signature(
                        app, device, device_address, device_identifier
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
