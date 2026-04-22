"""
File contains the bacpypes3_scanner class which is used to scan the network for devices and routers.
"""
import asyncio
import ipaddress
import logging
import os
from typing import Any, Dict, List, Optional, Set, Union

import netifaces

import gevent
import rdflib
from bacpypes3.app import Application
from bacpypes3.apdu import AbortPDU, AbortReason, ErrorRejectAbortNack, Error
from bacpypes3.argparse import SimpleArgumentParser  
from bacpypes3.comm import ApplicationServiceElement, bind
from bacpypes3.errors import ExecutionError, PropertyError
from bacpypes3.local.device import DeviceObject
from bacpypes3.primitivedata import ObjectType
from bacpypes3.vendor import VendorInfo
from bacpypes3.ipv4.bvll import (
    LPDU,
    ForwardedNPDU,
    ReadBroadcastDistributionTable,
    ReadBroadcastDistributionTableAck,
    ReadForeignDeviceTable,
    ReadForeignDeviceTableAck,
    Result,
)
from bacpypes3.ipv4.service import BVLLServiceAccessPoint
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.pdu import Address, IPv4Address, IPv6Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.rdf.core import BACnetGraph, BACNET, BACnetURI
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
    GrasshopperNode,
    GrasshopperTypeHandler,
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
        # IPs observed as ForwardedNPDU sources — these are BBMDs
        self.forwarded_npdu_sources: set = set()

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

        elif isinstance(pdu, Result):
            # Handle NAK/Result responses from non-BBMD devices.
            # Result code 0x0020 = ReadBDT-NAK, 0x0040 = ReadFDT-NAK
            # Resolve the future with None so callers don't wait for timeout.
            source = pdu.pduSource
            code = getattr(pdu, 'bvlciResultCode', None)
            if code == 0x0020 and self.read_bdt_future.get(source):
                _log.debug(f"ReadBDT NAK from {source}")
                self.read_bdt_future[source].set_result(None)
                del self.read_bdt_future[source]
            elif code == 0x0040 and self.read_fdt_future.get(source):
                _log.debug(f"ReadFDT NAK from {source}")
                self.read_fdt_future[source].set_result(None)
                del self.read_fdt_future[source]

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
        except asyncio.CancelledError:
            _log.warning(
                f"Request cancelled for {request_class.__name__} to {destination} (transport may be in broken state)"
            )
            return None
        except ErrorRejectAbortNack as e:
            _log.error(f"BACnet error in {request_class.__name__} request: {e}")
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
        # Track which routers serve which networks (for network node attributes)
        self.network_to_routers: dict[int, list] = {}

        # Scavenge scan configuration
        self.scavenge_enabled = scavenge_enabled
        self.scavenge_margin = scavenge_margin
        self.scavenge_max_range = scavenge_max_range
        self.scavenge_gap_threshold = scavenge_gap_threshold
        self.scavenge_gap_max_range = scavenge_gap_max_range

    def _extract_ip_from_address(self, address: Address) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
        """
        Extract IP address from BACpypes3 Address object.
        
        This handles Address objects that may include port numbers, which cannot be
        directly passed to ipaddress.ip_address(). The method tries multiple approaches
        to extract just the IP portion.
        
        Args:
            address: BACpypes3 Address object
            
        Returns:
            IPv4Address or IPv6Address object containing just the IP portion
            
        Raises:
            ValueError: If the IP address cannot be extracted or parsed
        """
        try:
            # First attempt: use addrTuple if available (most reliable)
            if hasattr(address, 'addrTuple') and address.addrTuple:
                return ipaddress.ip_address(address.addrTuple[0])
            
            # Fallback: convert to string and parse
            addr_str = str(address)
            # Remove port (after ':') and network prefix (after '/')
            ip_str = addr_str.split(':')[0].split('/')[0]
            return ipaddress.ip_address(ip_str)
        except (ValueError, AttributeError, IndexError) as e:
            raise ValueError(f"Failed to extract IP address from {address}: {e}")

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
        Set the application address for the BACnet analysis.

        Builds the Application stack manually (rather than using from_args)
        so we can wire the link layer with our network port object directly.
        """
        _log.debug("bacpypes3_scanner: set_application")
        settings = self.bacpypes_settings.copy()
        settings["bbmd"] = self.bacpypes_settings.get("bbmd", None)

        # Register VendorInfo before creating Application (required for non-999 vendor IDs)
        vendorid = settings.get("vendoridentifier", 999)
        if vendorid != 999:
            try:
                vendor_info = VendorInfo(vendorid)
                vendor_info.register_object_class(ObjectType.device, DeviceObject)
                _log.debug(f"Registered VendorInfo for vendor ID {vendorid}")
            except RuntimeError as e:
                _log.debug(f"VendorInfo for vendor ID {vendorid} already registered: {e}")

        # Use SimpleArgumentParser to get proper bacpypes3 defaults
        parser = SimpleArgumentParser()
        args = parser.parse_args([])
        for key, value in settings.items():
            setattr(args, key, value)

        # Build the Application stack manually to mirror what Application.from_args
        # + from_object_list + add_object does.
        # NOTE: We do NOT pre-create a socket. bacpypes3's IPv4DatagramServer already
        # passes reuse_port=True to create_datagram_endpoint, which sets SO_REUSEPORT
        # for bare-metal coexistence. Passing a custom bind_socket breaks broadcast
        # reception: IPv4DatagramServer tries to reuse the same socket for both the
        # unicast and broadcast endpoints; the second create_datagram_endpoint(sock=...)
        # call raises RuntimeError (not OSError) and the broadcast listener is never
        # created, so all IARTN responses (sent to the subnet broadcast address) are
        # silently dropped.
        from bacpypes3.vendor import get_vendor_info
        from bacpypes3.local.networkport import NetworkPortObject
        from bacpypes3.ipv4.link import NormalLinkLayer as NormalLinkLayer_ipv4
        from bacpypes3.netservice import NetworkServiceAccessPoint, NetworkServiceElement
        from bacpypes3.appservice import ApplicationServiceAccessPoint

        vi = get_vendor_info(vendorid)
        device_object_class = vi.get_object_class(ObjectType.device)
        device_object = device_object_class(
            objectIdentifier=("device", int(args.instance)),
            objectName=args.name,
        )

        # Create the application
        app = Application(device_info_cache=None)
        app.asap = ApplicationServiceAccessPoint(device_object, app.device_info_cache)
        app.nsap = NetworkServiceAccessPoint()
        app.nse = NetworkServiceElement()
        bind(app.nse, app.nsap)
        bind(app, app.asap, app.nsap)
        app.add_object(device_object)

        # Build the network port object (but don't add_object it — we'll
        # wire the link layer manually with our socket)
        network_port_class = vi.get_object_class(ObjectType.networkPort)
        address = args.address if args.address else "host"
        network_port_object = network_port_class(
            address,
            objectIdentifier=("network-port", 1),
            objectName="NetworkPort-1",
            networkNumber=args.network,
            networkNumberQuality="configured" if args.network else "unknown",
        )

        link_address = network_port_object.address
        _log.info(f"Creating link layer on {link_address}")
        link_layer = NormalLinkLayer_ipv4(link_address)

        app.link_layers[network_port_object.objectIdentifier] = link_layer
        if args.network and args.network != 0:
            app.nsap.bind(link_layer, net=args.network, address=link_address)
        else:
            app.nsap.bind(link_layer, address=link_address)

        # Register the network port object directly in the app's dictionaries
        # without calling add_object, which would create a second link layer
        app.objectName[network_port_object.objectName] = network_port_object
        app.objectIdentifier[network_port_object.objectIdentifier] = network_port_object
        network_port_object._app = app

        _log.debug(f"Application config: {args}")
        return app

    def get_networks_from_graph(self, g: rdflib.Graph) -> Set[int]:
        """Return a set of network numbers from the graph"""
        _log.debug("bacpypes3_scanner: get_networks_from_graph")
        networks = set()
        for t in g.triples((None, RDF.type, BACNET["Network"])):
            networks.add(int(t[0].split("/")[-1]))
        return networks

    def get_bbmd_ips(
        self, g: rdflib.Graph
    ) -> Set[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """Return a set of BBMD IPs from the graph"""
        _log.debug("bacpypes3_scanner: get_bbmd_ips")
        bbmd_ips = set()
        for t in g.triples((None, RDF.type, BACNET["BBMD"])):
            for t2 in g.triples((t[0], BACNET["device-address"], None)):
                try:
                    ip = ipaddress.ip_address(t2[2].value)
                    bbmd_ips.add(ip)
                except (ValueError, TypeError, AttributeError):
                    pass
        return bbmd_ips

    def get_device_ips(
        self, g: rdflib.Graph
    ) -> Set[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
        """Return a set of device IPs from the graph"""
        _log.debug("bacpypes3_scanner: get_device_ips")
        device_ips = set()
        for t in g.triples((None, RDF.type, BACNET["Device"])):
            for t2 in g.triples((t[0], BACNET["device-address"], None)):
                try:
                    ip = ipaddress.ip_address(t2[2].value)
                    device_ips.add(ip)
                except (ValueError, TypeError, AttributeError):
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
        scanner_node = GrasshopperNode(graph, BACnetURI["//Grasshopper"])
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

    @staticmethod
    def _to_bacpypes3_address(
        ip: ipaddress.IPv4Address, port: int = 47808
    ) -> IPv4Address:
        """
        Convert a Python ipaddress.IPv4Address to a bacpypes3 IPv4Address.

        This is necessary because bacpypes3 IPv4Address and Python ipaddress.IPv4Address
        have different hash functions, so they cannot be used interchangeably as dict keys.
        BVLL operations (ReadBDT, ReadFDT) register futures keyed by address, and the
        response lookup uses bacpypes3 addresses from pduSource.

        Args:
            ip: A Python ipaddress.IPv4Address
            port: BACnet port (default 47808/0xBAC0)

        Returns:
            A bacpypes3 IPv4Address suitable for BVLL operations
        """
        return IPv4Address(f"{ip}:{port}")

    def _extract_ip_from_remote_station(
        self, device_address: Address
    ) -> Optional[ipaddress.IPv4Address]:
        """
        Extract the IPv4 address from a RemoteStation BACnet address.

        For BACnet/IP devices behind a BACnet router, the RemoteStation address
        encodes the IP (4 bytes) + port (2 bytes) in the address octets.
        This method extracts the IP from such 6-byte addresses.

        Args:
            device_address: A BACnet Address (typically a RemoteStation)

        Returns:
            The extracted IPv4Address, or None if extraction fails
        """
        try:
            addr_bytes = device_address.addrAddr
            if addr_bytes and len(addr_bytes) == 6:
                # BACnet/IP encoding: 4 bytes IP + 2 bytes port
                ip = ipaddress.IPv4Address(addr_bytes[:4])
                if not ip.is_loopback and not ip.is_unspecified:
                    return ip
        except (AttributeError, ValueError, TypeError):
            pass
        return None

    async def discover_bbmds(
        self, ase: BVLLServiceElement, graph: Graph
    ) -> None:
        """
        Discover BBMDs by probing known IPs with ReadBDT.

        BBMDs may not have BACnet device objects and thus won't respond to Who-Is.
        This method probes all known device IPs, router IPs, and follows BDT entries
        to snowball-discover BBMDs across subnets.

        Args:
            ase: The BVLL service element for sending ReadBDT
            graph: The RDF graph to update with discovered BBMDs
        """
        _log.info("bacpypes3_scanner: discover_bbmds")

        # Collect all candidate IPs to probe for BBMD status
        candidate_ips: set[ipaddress.IPv4Address] = set()

        # 1. HIGHEST PRIORITY: IPs observed as ForwardedNPDU sources during Who-Is.
        #    Any IP that forwards a broadcast IS a BBMD by definition.
        if ase.forwarded_npdu_sources:
            _log.info(
                f"Observed {len(ase.forwarded_npdu_sources)} ForwardedNPDU sources "
                f"(confirmed BBMDs): {ase.forwarded_npdu_sources}"
            )
            candidate_ips.update(ase.forwarded_npdu_sources)

        # 2. All known device IPs from scan
        for ip in self.scanned_device_ips:
            if isinstance(ip, ipaddress.IPv4Address):
                candidate_ips.add(ip)

        # 3. Infrastructure IPs on each known subnet (gateway, .1, .2, .3)
        for subnet in self.subnets:
            if isinstance(subnet, ipaddress.IPv4Network):
                for offset in [1, 2, 3]:
                    try:
                        infra_ip = subnet.network_address + offset
                        if infra_ip in subnet:
                            candidate_ips.add(infra_ip)
                    except (ValueError, OverflowError):
                        pass

        # 4. Configured BBMDs
        for bbmd_ip in self.bbmds:
            if isinstance(bbmd_ip, ipaddress.IPv4Address):
                candidate_ips.add(bbmd_ip)

        # Remove already-identified BBMDs and our own IP
        scanner_ip_str = self.bacpypes_settings.get("address", "").split(":")[0].split("/")[0]
        try:
            scanner_ip = ipaddress.IPv4Address(scanner_ip_str)
            candidate_ips.discard(scanner_ip)
        except ValueError:
            pass
        for ip in list(self.scanned_ipaddress_bbmd.keys()):
            candidate_ips.discard(ip)

        _log.info(f"Probing {len(candidate_ips)} candidate IPs for BBMD status")

        # Probe each candidate - use short timeout since most won't be BBMDs
        discovered_bbmd_ips: set[ipaddress.IPv4Address] = set()
        for ip in candidate_ips:
            try:
                bbmd_addr = self._to_bacpypes3_address(ip)
                bdt = await ase.read_broadcast_distribution_table(bbmd_addr, timeout=2)
                if bdt is not None:
                    _log.info(f"Discovered BBMD at {ip} with {len(bdt)} BDT entries")
                    self.scanned_bbmds_bdt[ip] = [
                        ipaddr
                        for bdt_entry in bdt
                        for ipaddr in [ipaddress.ip_address(bdt_entry)]
                        if isinstance(ipaddr, ipaddress.IPv4Address)
                    ]
                    discovered_bbmd_ips.add(ip)
            except asyncio.CancelledError:
                _log.debug(f"IP {ip} is not a BBMD: transport cancelled")
            except (Exception, ErrorRejectAbortNack) as e:
                _log.debug(f"IP {ip} is not a BBMD: {e}")

        # Follow BDT entries to discover BBMDs on other subnets (snowball)
        bdt_ips_to_probe = set()
        for bbmd_ip in discovered_bbmd_ips:
            for bdt_entry_ip in self.scanned_bbmds_bdt.get(bbmd_ip, []):
                if (
                    bdt_entry_ip not in discovered_bbmd_ips
                    and bdt_entry_ip not in self.scanned_ipaddress_bbmd
                ):
                    bdt_ips_to_probe.add(bdt_entry_ip)

        if bdt_ips_to_probe:
            _log.info(f"Following BDT entries to probe {len(bdt_ips_to_probe)} additional IPs")

        for ip in bdt_ips_to_probe:
            try:
                bbmd_addr = self._to_bacpypes3_address(ip)
                bdt = await ase.read_broadcast_distribution_table(bbmd_addr, timeout=2)
                if bdt is not None:
                    _log.info(f"Discovered BBMD at {ip} via BDT snowball")
                    self.scanned_bbmds_bdt[ip] = [
                        ipaddr
                        for bdt_entry in bdt
                        for ipaddr in [ipaddress.ip_address(bdt_entry)]
                        if isinstance(ipaddr, ipaddress.IPv4Address)
                    ]
                    discovered_bbmd_ips.add(ip)
            except (Exception, ErrorRejectAbortNack) as e:
                _log.debug(f"BDT entry IP {ip} is not a BBMD: {e}")

        # Create BBMDNodes for discovered BBMDs
        for bbmd_ip in discovered_bbmd_ips:
            if bbmd_ip in self.scanned_ipaddress_bbmd:
                continue

            # Check if this IP matches an existing discovered device
            existing_device = self.scanned_device_ips.get(bbmd_ip)

            if existing_device and not isinstance(existing_device, BBMDNode):
                # Convert existing device to BBMDNode
                _log.info(
                    f"Converting device at {bbmd_ip} from "
                    f"{type(existing_device).__name__} to BBMDNode"
                )
                old_iri = existing_device.node_iri
                stored_properties = [
                    (p, o) for p, o in graph.predicate_objects(old_iri)
                    if p != RDF.type
                ]
                graph.remove((old_iri, None, None))
                bbmd_node = BBMDNode(graph, old_iri)
                for predicate, obj in stored_properties:
                    bbmd_node.add_connection(predicate, obj)

                self.scanned_bbmds.append(bbmd_node)
                self.scanned_ipaddress_bbmd[bbmd_ip] = bbmd_node
                for ip_key, dev in list(self.scanned_device_ips.items()):
                    if dev is existing_device:
                        self.scanned_device_ips[ip_key] = bbmd_node
                for subnet in self.subnets:
                    if bbmd_ip in subnet:
                        self.bbmd_in_subnet[subnet] = old_iri
                        break
            elif existing_device is None:
                # BBMD not discovered via Who-Is — create new BBMDNode
                _log.info(f"Creating BBMDNode for infrastructure BBMD at {bbmd_ip}")
                bbmd_iri = BACnetURI["//bbmd/" + str(bbmd_ip)]
                bbmd_node = BBMDNode(graph, bbmd_iri)
                bbmd_node.add_properties(
                    label=bbmd_iri,
                    device_address=str(bbmd_ip),
                )
                self.scanned_bbmds.append(bbmd_node)
                self.scanned_ipaddress_bbmd[bbmd_ip] = bbmd_node
                self.scanned_device_ips[bbmd_ip] = bbmd_node
                for subnet in self.subnets:
                    if bbmd_ip in subnet:
                        bbmd_node.add_properties(subnet=subnet)
                        self.bbmd_in_subnet[subnet] = bbmd_iri
                        break

        _log.info(
            f"BBMD discovery complete: found {len(discovered_bbmd_ips)} BBMDs, "
            f"total tracked: {len(self.scanned_ipaddress_bbmd)}"
        )

    async def reconcile_configured_bbmds(
        self, ase: BVLLServiceElement, graph: Graph
    ) -> None:
        """
        Ensure configured BBMDs are properly represented as BBMDNodes in the graph.

        BBMDs on remote subnets respond to Who-Is as RemoteStations, so the
        scanner creates them as plain DeviceNodes during get_device_objects.
        This method sends ReadBDT directly to each configured BBMD IP (BVLL-layer,
        no BACnet routing needed), finds the matching discovered device, and
        converts it to a BBMDNode.

        Args:
            ase: The BVLL service element for sending ReadBDT/ReadFDT
            graph: The RDF graph to update
        """
        _log.debug("bacpypes3_scanner: reconcile_configured_bbmds")

        # Build a reverse lookup: IP -> (device_address, device_node) for
        # RemoteStation devices where we can extract the IP
        remote_ip_to_device: dict[ipaddress.IPv4Address, tuple] = {}
        for ip, device_node in self.scanned_device_ips.items():
            remote_ip_to_device[ip] = device_node

        for bbmd_ip in self.bbmds:
            if bbmd_ip in self.scanned_ipaddress_bbmd:
                _log.debug(f"BBMD {bbmd_ip} already identified, skipping")
                continue

            _log.info(f"Reconciling configured BBMD {bbmd_ip}")

            # Convert Python ipaddress to bacpypes3 Address for BVLL operations.
            # bacpypes3 IPv4Address and Python ipaddress.IPv4Address have different
            # hash functions, so dict key lookups fail if types are mixed.
            bbmd_bacpypes_addr = self._to_bacpypes3_address(bbmd_ip)

            # Try ReadBDT directly to the BBMD's IP address (BVLL-layer)
            try:
                bdt = await ase.read_broadcast_distribution_table(bbmd_bacpypes_addr)
                if bdt is not None:
                    self.scanned_bbmds_bdt[bbmd_ip] = [
                        ipaddr
                        for bdt_entry in bdt
                        for ipaddr in [ipaddress.ip_address(bdt_entry)]
                        if isinstance(ipaddr, ipaddress.IPv4Address)
                    ]
                    _log.info(
                        f"Successfully read BDT from configured BBMD {bbmd_ip}: "
                        f"{len(self.scanned_bbmds_bdt[bbmd_ip])} entries"
                    )
                else:
                    _log.warning(f"ReadBDT to {bbmd_ip} returned None")
                    continue
            except (Exception, ErrorRejectAbortNack) as e:
                _log.warning(f"ReadBDT to configured BBMD {bbmd_ip} failed: {e}")
                continue

            # Find the matching discovered device - check direct IP first
            existing_device = remote_ip_to_device.get(bbmd_ip)

            # If not found by direct IP, scan RemoteStation addresses
            if existing_device is None:
                for scanned_ip, device_node in self.scanned_device_ips.items():
                    if scanned_ip == bbmd_ip:
                        existing_device = device_node
                        break

            # Also check all devices for RemoteStation IP extraction
            if existing_device is None:
                for s, p, o in graph.triples((None, BACNET["address"], None)):
                    try:
                        addr_str = str(o)
                        # Try to parse as a direct IP
                        if ipaddress.ip_address(addr_str) == bbmd_ip:
                            # Find the device node for this IRI
                            for ip, dev in self.scanned_device_ips.items():
                                if dev.node_iri == s:
                                    existing_device = dev
                                    break
                            if existing_device:
                                break
                    except ValueError:
                        pass

            if existing_device and not isinstance(existing_device, BBMDNode):
                # Convert the existing device to a BBMDNode
                _log.info(
                    f"Converting device at {bbmd_ip} from "
                    f"{type(existing_device).__name__} to BBMDNode"
                )
                old_iri = existing_device.node_iri

                # Store all existing properties (except type)
                stored_properties = []
                for predicate, obj in graph.predicate_objects(old_iri):
                    if predicate != RDF.type:
                        stored_properties.append((predicate, obj))

                # Remove old triples
                graph.remove((old_iri, None, None))

                # Create BBMDNode with same IRI
                bbmd_node = BBMDNode(graph, old_iri)

                # Restore properties
                for predicate, obj in stored_properties:
                    bbmd_node.add_connection(predicate, obj)

                # Update tracking dicts
                self.scanned_bbmds.append(bbmd_node)
                self.scanned_ipaddress_bbmd[bbmd_ip] = bbmd_node

                # Update scanned_device_ips - find and replace the entry
                for ip, dev in list(self.scanned_device_ips.items()):
                    if dev is existing_device:
                        self.scanned_device_ips[ip] = bbmd_node

                # Track BBMD in its subnet
                for subnet in self.subnets:
                    if bbmd_ip in subnet:
                        self.bbmd_in_subnet[subnet] = old_iri
                        break

            elif existing_device is None:
                # BBMD not discovered via Who-Is at all - create a new BBMDNode
                _log.info(f"Creating new BBMDNode for undiscovered BBMD {bbmd_ip}")
                bbmd_iri = BACnetURI["//bbmd/" + str(bbmd_ip)]
                bbmd_node = BBMDNode(graph, bbmd_iri)
                bbmd_node.add_properties(
                    label=bbmd_iri,
                    device_address=str(bbmd_ip),
                )

                self.scanned_bbmds.append(bbmd_node)
                self.scanned_ipaddress_bbmd[bbmd_ip] = bbmd_node
                self.scanned_device_ips[bbmd_ip] = bbmd_node

                # Associate with subnet
                for subnet in self.subnets:
                    if bbmd_ip in subnet:
                        bbmd_node.add_properties(subnet=subnet)
                        self.bbmd_in_subnet[subnet] = bbmd_iri
                        break

            else:
                _log.debug(f"BBMD {bbmd_ip} already a BBMDNode, updating tracking")
                self.scanned_ipaddress_bbmd[bbmd_ip] = existing_device

        _log.debug("reconcile_configured_bbmds Completed")

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
        try:
            # local_adapter is a NetworkAdapter; its clientPeer is the
            # NormalLinkLayer which IS the BVLLServiceAccessPoint.
            # BVLL management requests (ReadBDT, ReadFDT) go via
            # sap_indication → Client.request → BVLLCodec → UDP.
            local_adapter = app.nsap.local_adapter
            sap = local_adapter.clientPeer
            if not isinstance(sap, BVLLServiceAccessPoint):
                _log.error("Expected BVLLServiceAccessPoint but got %s", type(sap).__name__)
                return
            ase = BVLLServiceElement()
            bind(ase, sap)

            # Wrap BIPNormal.confirmation to observe ForwardedNPDU sources.
            # When a BBMD forwards a broadcast, the UDP source is the BBMD's IP.
            # BIPNormal.confirmation receives ForwardedNPDU with pduSource = BBMD IP
            # but replaces it with bvlciAddress (original device) before sending upstream.
            # We intercept here to record BBMD IPs passively during normal traffic.
            _original_sap_confirmation = sap.confirmation

            async def _observing_confirmation(lpdu):
                if isinstance(lpdu, ForwardedNPDU) and lpdu.pduSource:
                    try:
                        bbmd_ip = ipaddress.ip_address(lpdu.pduSource)
                        ase.forwarded_npdu_sources.add(bbmd_ip)
                    except (ValueError, TypeError):
                        pass
                return await _original_sap_confirmation(lpdu)

            sap.confirmation = _observing_confirmation

            await self.set_scanner_node(graph)
            await self.get_device_objects(app, ase, graph)
            await self.get_router_networks(app, graph)
            await self.discover_bbmds(ase, graph)
            # Read FDT from all discovered BBMDs
            for bbmd_ip in list(self.scanned_ipaddress_bbmd.keys()):
                await self.read_bbmd_fdt(ase, self._to_bacpypes3_address(bbmd_ip))
            await self.set_subnet_network(graph)
        finally:
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

        # First, send a global Who-Is-Router-To-Network (no specific network)
        # to discover all routers on the local network. This is the standard
        # BACnet approach — all routers respond with their full network list.
        # The 2-second timeout in bacpypes3 collects all responses.
        try:
            _log.info("Sending global Who-Is-Router-To-Network broadcast")
            global_routers = await app.nse.who_is_router_to_network()
            _log.info(f"Global Who-Is-Router-To-Network returned {len(global_routers)} response(s)")
            for adapter, i_am_router_to_network in global_routers:
                _log.info(
                    f"Router {i_am_router_to_network.pduSource} serves networks: "
                    f"{list(i_am_router_to_network.iartnNetworkList)}"
                )
                router_pdu_source = i_am_router_to_network.pduSource
                ip = self._extract_ip_from_address(router_pdu_source)

                existing_device = self.scanned_device_ips.get(ip)

                if existing_device and isinstance(existing_device, DeviceNode):
                    _log.debug(f"Merging device at {ip} into router (from global query)")
                    device_iri = existing_device.node_iri
                    device_instance = graph.value(subject=device_iri, predicate=BACNET["device-instance"])
                    stored_properties = []
                    for predicate, obj in graph.predicate_objects(device_iri):
                        if predicate != RDF.type:
                            stored_properties.append((predicate, obj))
                    graph.remove((device_iri, None, None))
                    router_device_iri = BACnetURI["//router/" + str(device_instance)]
                    router_node = DeviceRouterNode(graph, router_device_iri)
                    for predicate, obj in stored_properties:
                        router_node.device.add_connection(predicate, obj)
                    self.scanned_device_ips[ip] = router_node
                elif existing_device and isinstance(existing_device, (RouterNode, DeviceRouterNode)):
                    router_node = existing_device
                else:
                    router_iri = BACnetURI["//router/" + str(router_pdu_source)]
                    router_node = RouterNode(graph, router_iri)
                    self.scanned_device_ips[ip] = router_node

                for net in i_am_router_to_network.iartnNetworkList:
                    router_node.add_properties(network_id=net)
                    if net not in self.network_to_routers:
                        self.network_to_routers[net] = []
                    if router_node.node_iri not in self.network_to_routers[net]:
                        self.network_to_routers[net].append(router_node.node_iri)
                    # Also add newly discovered networks to scanned_networks
                    self.scanned_networks.add(net)

                not_in_network = True
                for subnet in self.subnets:
                    if ip in subnet:
                        not_in_network = False
                        router_node.add_properties(subnet=subnet)
                if not_in_network:
                    self.scanner_node.add_properties(device_iri=router_node.node_iri)
        except (Exception, ErrorRejectAbortNack) as e:
            _log.error(f"Global Who-Is-Router-To-Network failed: {e}")

        # Then send directed queries for any remaining networks not yet covered
        networks_with_routers = set()
        for net, rlist in self.network_to_routers.items():
            if rlist:
                networks_with_routers.add(net)

        networks_to_query = self.scanned_networks - networks_with_routers
        if networks_to_query:
            _log.info(f"Sending directed Who-Is-Router-To-Network for {len(networks_to_query)} network(s) without routers: {sorted(networks_to_query)}")

        for network_id in networks_to_query:
          try:
            _log.debug(f"Currently Processing network {network_id}")
            routers = await app.nse.who_is_router_to_network(network=network_id)
            _log.info(f"Directed Who-Is-Router-To-Network for network {network_id} returned {len(routers)} response(s)")
            for adapter, i_am_router_to_network in routers:
                _log.debug(
                    f"adapter: {adapter} i_am_router_to_network: {i_am_router_to_network}"
                )
                router_pdu_source = i_am_router_to_network.pduSource
                # Extract IP address from Address object (removing port if present)
                ip = self._extract_ip_from_address(router_pdu_source)
                
                # Check if we already have a device at this IP address
                existing_device = self.scanned_device_ips.get(ip)
                
                if existing_device and isinstance(existing_device, DeviceNode):
                    # Convert existing device to a device+router by creating a new DeviceRouterNode
                    _log.debug(f"Merging device at {ip} into router")
                    
                    # Use the existing device's IRI (which is based on device instance, not IP)
                    device_iri = existing_device.node_iri
                    
                    # Extract device instance before removing triples from graph
                    device_instance = graph.value(subject=device_iri, predicate=BACNET["device-instance"])
                    
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
                    # Track network -> router mapping for network node attributes
                    if net not in self.network_to_routers:
                        self.network_to_routers[net] = []
                    if router_node.node_iri not in self.network_to_routers[net]:
                        self.network_to_routers[net].append(router_node.node_iri)

                not_in_network = True
                for subnet in self.subnets:
                    if ip in subnet:
                        not_in_network = False
                        router_node.add_properties(subnet=subnet)
                if not_in_network:
                    self.scanner_node.add_properties(device_iri=router_node.node_iri)
          except (Exception, ErrorRejectAbortNack) as e:
            _log.error(f"Error processing network {network_id}: {e}")
            continue

        networks_without_routers = sorted(self.scanned_networks - set(n for n, r in self.network_to_routers.items() if r))
        if networks_without_routers:
            _log.warning(f"get_router_networks completed: {len(self.network_to_routers)} network(s) have routers, "
                         f"{len(networks_without_routers)} network(s) still without routers: {networks_without_routers}")
        else:
            _log.info(f"get_router_networks completed: all {len(self.scanned_networks)} network(s) have routers assigned")
        _log.debug(f"network_to_routers: {dict(self.network_to_routers)}")

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
            # Extract IP address from Address object (removing port if present)
            ip = self._extract_ip_from_address(device_address)
            if bdt is not None and isinstance(ip, ipaddress.IPv4Address):
                self.scanned_bbmds_bdt[ip] = [
                    ipaddr
                    for bdt_entry in bdt
                    for ipaddr in [ipaddress.ip_address(bdt_entry)]
                    if isinstance(ipaddr, ipaddress.IPv4Address)
                ]
                return True
        except (Exception, ErrorRejectAbortNack) as e:
            _log.debug(f"Device {device_address} is not a BBMD or check failed: {e}")
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
            fdt = await ase.read_foreign_device_table(device_address)
            if fdt is not None:
                # Store keyed by Python ipaddress for consistent lookup with
                # scanned_ipaddress_bbmd (also keyed by Python ipaddress)
                ip_key = ipaddress.ip_address(device_address)
                self.scanned_bbmds_fdt[ip_key] = fdt
                _log.debug(f"FDT entries for {device_address}: {fdt}")
        except (Exception, ErrorRejectAbortNack) as e:
            _log.debug(f"Failed to read FDT from {device_address}: {e}")

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
                    device.add_connection(BACNET[rdf_prop], Literal(str(value)))
                    _log.debug(
                        f"Read {bacnet_prop}={value} from device {device_identifier[1]}"
                    )
            except asyncio.TimeoutError:
                _log.debug(
                    f"Timeout reading {bacnet_prop} from device {device_identifier[1]}"
                )
            except ErrorRejectAbortNack as e:
                _log.debug(
                    f"BACnet error reading {bacnet_prop} from device {device_identifier[1]}: {e}"
                )
            except PropertyError as e:
                # Handle specific BACnet property errors (like unknown-property)
                _log.debug(
                    f"BACnet property error reading '{bacnet_prop}' from device {device_identifier[1]}: {e.errorCode}"
                )
            except ExecutionError as e:
                # Handle other BACnet execution errors
                _log.debug(
                    f"BACnet execution error reading '{bacnet_prop}' from device {device_identifier[1]}: {e.errorClass}.{e.errorCode}"
                )
            except Error as e:
                # Handle BACnet Error PDUs
                _log.debug(
                    f"BACnet Error PDU reading '{bacnet_prop}' from device {device_identifier[1]}: {e}"
                )
            except Exception as e:
                _log.error(e)
                # Comprehensive BACnet error handling without imports
                error_str = str(e)
                error_type = type(e).__name__
                error_module = getattr(type(e), '__module__', '')
                
                # Check if this is a BACnet property error (like "unknown-property")
                if 'unknown-property' in error_str or 'property' in error_str.lower():
                    _log.debug(
                        f"BACnet property not supported: {bacnet_prop} on device {device_identifier[1]} - {error_str}"
                    )
                elif 'bacpypes3' in error_module:
                    _log.debug(
                        f"BACnet error reading {bacnet_prop} from device {device_identifier[1]}: {error_type} - {error_str}"
                    )
                else:
                    _log.debug(
                        f"Error reading {bacnet_prop} from device {device_identifier[1]}: {error_type} ({error_module}) - {error_str}"
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
        object_list = None

        try:
            # Try to read the entire object-list property at once
            object_list = await asyncio.wait_for(
                app.read_property(device_address, device_obj_id, "object-list"),
                timeout=30.0,  # Longer timeout for potentially large lists
            )
        except (asyncio.TimeoutError, ErrorRejectAbortNack, AbortPDU) as err:
            if hasattr(err, 'apduAbortRejectReason') and err.apduAbortRejectReason in (
                AbortReason.bufferOverflow,
                AbortReason.segmentationNotSupported,
            ):
                _log.debug(
                    f"Buffer overflow reading object-list from device {device_identifier[1]}, "
                    f"falling back to reading individual elements: {err}"
                )
                # Fall back to reading the length and each element one at a time
                try:
                    # Read the array length (index 0)
                    object_list_length = await asyncio.wait_for(
                        app.read_property(
                            device_address,
                            device_obj_id,
                            "object-list",
                            array_index=0,
                        ),
                        timeout=10.0,
                    )
                    
                    # Read each element individually
                    object_list = []
                    for i in range(object_list_length):
                        try:
                            obj_id = await asyncio.wait_for(
                                app.read_property(
                                    device_address,
                                    device_obj_id,
                                    "object-list",
                                    array_index=i + 1,
                                ),
                                timeout=5.0,
                            )
                            object_list.append(obj_id)
                        except (asyncio.TimeoutError, ErrorRejectAbortNack, AbortPDU, PropertyError, ExecutionError, Error) as e:
                            _log.debug(
                                f"Error reading object-list[{i+1}] from device {device_identifier[1]}: {e}"
                            )
                            # Continue with next object, don't fail the entire operation
                            continue
                            
                    _log.debug(
                        f"Successfully read {len(object_list)} objects individually from device {device_identifier[1]}"
                    )
                        
                except (asyncio.TimeoutError, ErrorRejectAbortNack, AbortPDU, PropertyError, ExecutionError, Error) as e:
                    _log.debug(
                        f"Failed to read object-list length from device {device_identifier[1]}: {e}"
                    )
                    return
            else:
                _log.debug(
                    f"AbortPDU error reading object-list from device {device_identifier[1]}: {err}"
                )
                return
        except ErrorRejectAbortNack as err:
            _log.debug(
                f"Error/reject reading object-list from device {device_identifier[1]}: {err}"
            )
            return
        except PropertyError as err:
            _log.debug(
                f"BACnet property error reading object-list from device {device_identifier[1]}: {err.errorCode}"
            )
            return
        except ExecutionError as err:
            _log.debug(
                f"BACnet execution error reading object-list from device {device_identifier[1]}: {err.errorClass}.{err.errorCode}"
            )
            return
        except Error as err:
            _log.debug(
                f"BACnet Error PDU reading object-list from device {device_identifier[1]}: {err}"
            )
            return
        except asyncio.TimeoutError:
            _log.debug(
                f"Timeout reading object-list from device {device_identifier[1]}"
            )
            return
        except ErrorRejectAbortNack as e:
            _log.debug(
                f"BACnet error reading object-list from device {device_identifier[1]}: {e}"
            )
            return
        except Exception as e:
            _log.debug(
                f"Could not read object-list from device {device_identifier[1]}: {e}"
            )
            return

        if object_list is None or len(object_list) == 0:
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
            BACNET["object-count"], Literal(total_count)
        )
        _log.debug(
            f"Device {device_identifier[1]} has {total_count} total objects"
        )

        object_dict = {}
        # Add count for each object type
        for type_name, count in type_counts.items():
            # Create property name like "analog-input-count"
            prop_name = f"{type_name}-count"
            # device.add_connection(BACNET[prop_name], Literal(count))
            object_dict[prop_name] = count
            _log.debug(
                f"Device {device_identifier[1]}: {type_name}={count}"
            )
        device.add_connection(BACNET["total-objects"], Literal(str(object_dict)))

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
            except (Exception, ErrorRejectAbortNack) as e:
                _log.error(f"Error in Who Is: {e}")
                track_lower = track_upper + 1
                continue

            _log.debug(f"Finished Scanning for devices at {track_lower}")

            for i_am in i_ams:
                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
                device_iri = BACnetURI["//" + str(device_identifier[1])]
                try:
                    # Extract IP address from Address object (removing port if present)
                    ip: Union[IPv4Address, IPv6Address] = self._extract_ip_from_address(device_address)
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
                    # RemoteStation device — try to extract its real IP
                    # For BACnet/IP devices behind a router, the 6-byte address
                    # encodes IP (4 bytes) + port (2 bytes)
                    extracted_ip = self._extract_ip_from_remote_station(device_address)
                    is_bbmd = False

                    if extracted_ip:
                        _log.debug(
                            f"Extracted IP {extracted_ip} from RemoteStation "
                            f"{device_address} for device {device_identifier[1]}"
                        )
                        # Try ReadBDT directly to the extracted IP (BVLL-layer)
                        bbmd_addr = self._to_bacpypes3_address(extracted_ip)
                        is_bbmd = await self.check_if_device_is_bbmd(
                            ase, bbmd_addr
                        )

                    if is_bbmd:
                        device = BBMDNode(graph, device_iri)
                        _log.info(
                            f"Remote device {device_identifier[1]} at "
                            f"{extracted_ip} identified as BBMD"
                        )
                    else:
                        device = DeviceNode(graph, device_iri)

                    device.add_properties(
                        label=device_iri,
                        device_identifier=device_identifier[1],
                        device_address=device_address,
                        vendor_id=i_am.vendorID,
                        network_id=device_address.addrNet,
                    )
                    try:
                        await self.read_device_properties(
                            app, device, device_address, device_identifier
                        )
                        await self.read_device_object_signature(
                            app, device, device_address, device_identifier
                        )
                    except (Exception, ErrorRejectAbortNack) as e:
                        _log.debug(
                            f"Could not read properties for remote device {device_identifier[1]}: {e}"
                        )
                    self.scanned_networks.add(device_address.addrNet)

                    if extracted_ip:
                        self.scanned_device_ips[extracted_ip] = device
                        if isinstance(device, BBMDNode):
                            # Track BBMD in subnet and lookup dicts
                            device_subnet = await self.add_subnet_to_device(
                                device, bbmd_addr
                            )
                            self.bbmd_in_subnet[device_subnet] = device_iri
                            self.scanned_bbmds.append(device)
                            self.scanned_ipaddress_bbmd[extracted_ip] = device

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
            subnet_node = SubnetNode(graph, BACnetURI["//subnet/" + str(subnet)])
            # Add subnet CIDR and BBMD if applicable
            bbmd_iri = self.bbmd_in_subnet.get(subnet)
            subnet_node.add_properties(subnet_cidr=str(subnet), bbmd_iri=bbmd_iri)

        for net in self.scanned_networks:
            network_node = NetworkNode(graph, BACnetURI["//network/" + str(net)])
            # Add network number and router(s) if known
            routers = self.network_to_routers.get(net, [])
            # Add the first router as the primary router attribute
            router_iri = routers[0] if routers else None
            router_num = router_iri.split("bacnet://router/")[-1] if router_iri else None
            if router_iri:
                _log.info(f"Network {net}: assigned router {router_iri}")
            else:
                _log.warning(f"Network {net}: no router discovered (Who-Is-Router-To-Network returned no results for this network)")
            network_node.add_properties(network=net, router_iri=router_num)

        # Process BDT entries - create edges between BBMDs in same BDT
        try:
            for bbmd_ipaddress, bdt in self.scanned_bbmds_bdt.items():
                bbmd: BBMDNode = self.scanned_ipaddress_bbmd[bbmd_ipaddress]
                for bdt_entry in bdt:
                    if bdt_entry in self.scanned_ipaddress_bbmd:
                        bdt_entry_bbmd: BBMDNode = self.scanned_ipaddress_bbmd[
                            bdt_entry
                        ]
                        bbmd.add_properties(bdt_device_iri=bdt_entry_bbmd.node_iri)
        except (Exception, ErrorRejectAbortNack) as e:
            _log.error(f"Error in setting BDT: {e}")

        # Process FDT entries - create edges from BBMD to registered foreign devices
        try:
            for bbmd_ipaddress, fdt in self.scanned_bbmds_fdt.items():
                if bbmd_ipaddress not in self.scanned_ipaddress_bbmd:
                    continue
                bbmd: BBMDNode = self.scanned_ipaddress_bbmd[bbmd_ipaddress]
                for fdt_entry in fdt:
                    # FDT entries have fdAddress attribute (IPv4Address)
                    fd_address = fdt_entry.fdAddress
                    # Convert to ipaddress for lookup
                    fd_ip = ipaddress.IPv4Address(fd_address.addrTuple[0])

                    # Check if foreign device is a known BBMD
                    if fd_ip in self.scanned_ipaddress_bbmd:
                        fd_node = self.scanned_ipaddress_bbmd[fd_ip]
                        bbmd.add_properties(fdt_device_iri=fd_node.node_iri)
                        _log.debug(f"Added FDT edge: {bbmd_ipaddress} -> {fd_ip} (BBMD)")
                    # Check if foreign device is a known device
                    elif fd_ip in self.scanned_device_ips:
                        fd_node = self.scanned_device_ips[fd_ip]
                        bbmd.add_properties(fdt_device_iri=fd_node.node_iri)
                        _log.debug(f"Added FDT edge: {bbmd_ipaddress} -> {fd_ip} (Device)")
                    else:
                        _log.debug(f"FDT entry {fd_ip} not found in scanned devices")
        except (Exception, ErrorRejectAbortNack) as e:
            _log.error(f"Error in setting FDT: {e}")

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
        for triple in self.prev_graph.triples((None, BACNET["device-instance"], None)):
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
        if not isinstance(sap, BVLLServiceAccessPoint):
            _log.error("Expected BVLLServiceAccessPoint but got %s", type(sap).__name__)
            app.close()
            return
        ase = BVLLServiceElement()
        bind(ase, sap)

        # Wrap BIPNormal.confirmation to observe ForwardedNPDU sources (BBMD IPs)
        _original_sap_confirmation = sap.confirmation

        async def _observing_confirmation(lpdu):
            if isinstance(lpdu, ForwardedNPDU) and lpdu.pduSource:
                try:
                    bbmd_ip = ipaddress.ip_address(lpdu.pduSource)
                    ase.forwarded_npdu_sources.add(bbmd_ip)
                except (ValueError, TypeError):
                    pass
            return await _original_sap_confirmation(lpdu)

        sap.confirmation = _observing_confirmation

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
                            # Extract IP address from Address object (removing port if present)
                            ip: Union[IPv4Address, IPv6Address] = self._extract_ip_from_address(device_address)
                            
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

                            # Read additional device properties (model_name, firmware_revision, device_name)
                            await self.read_device_properties(
                                app, device, device_address, device_identifier
                            )

                            # Read device object signature (object types and counts)
                            await self.read_device_object_signature(
                                app, device, device_address, device_identifier
                            )

                            device_subnet = await self.add_subnet_to_device(device, device_address)

                            # Track device by IP address for router merging
                            self.scanned_device_ips[ip] = device

                            if isinstance(device, BBMDNode):
                                self.bbmd_in_subnet[device_subnet] = device_iri
                                self.scanned_bbmds.append(device)
                                self.scanned_ipaddress_bbmd[ip] = device

                        except ValueError:
                            extracted_ip = self._extract_ip_from_remote_station(device_address)
                            is_bbmd = False

                            if extracted_ip:
                                _log.debug(
                                    f"Extracted IP {extracted_ip} from RemoteStation "
                                    f"{device_address} for device {device_identifier[1]}"
                                )
                                bbmd_addr = self._to_bacpypes3_address(extracted_ip)
                                is_bbmd = await self.check_if_device_is_bbmd(
                                    ase, bbmd_addr
                                )

                            if is_bbmd:
                                device = BBMDNode(graph, device_iri)
                                _log.info(
                                    f"Remote device {device_identifier[1]} at "
                                    f"{extracted_ip} identified as BBMD"
                                )
                            else:
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

                            if extracted_ip:
                                self.scanned_device_ips[extracted_ip] = device
                                if isinstance(device, BBMDNode):
                                    device_subnet = await self.add_subnet_to_device(
                                        device, bbmd_addr
                                    )
                                    self.bbmd_in_subnet[device_subnet] = device_iri
                                    self.scanned_bbmds.append(device)
                                    self.scanned_ipaddress_bbmd[extracted_ip] = device

                except (Exception, ErrorRejectAbortNack) as e:
                    _log.error(f"Error during scavenge scan {i}: {e}")

            # Discover routers and complete the scan
            await self.get_router_networks(app, graph)
            await self.discover_bbmds(ase, graph)
            # Read FDT from all discovered BBMDs
            for bbmd_ip in list(self.scanned_ipaddress_bbmd.keys()):
                await self.read_bbmd_fdt(ase, self._to_bacpypes3_address(bbmd_ip))
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
