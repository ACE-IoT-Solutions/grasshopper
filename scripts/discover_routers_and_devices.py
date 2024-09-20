"""
Example script that runs a BACnet scan and creates an RDF graph of the devices relative to the router.

Usage:

python discover_routers_and_devices.py 1000 10000 --output test.ttl --address 192.168.1.203/24:47809 --bbmd 10.1.1.1 > log.txt

adding bbmd ip address will allow the system to find devices connected in that bbmd network
"""

import sys
import asyncio

from typing import List, Optional

from bacpypes3.debugging import bacpypes_debugging, ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser

from bacpypes3.pdu import Address, IPv4Address
from bacpypes3.primitivedata import ObjectIdentifier, ObjectType
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.basetypes import PropertyIdentifier
from bacpypes3.apdu import AbortReason, AbortPDU, ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.comm import ApplicationServiceElement, bind
from bacpypes3.vendor import get_vendor_info
from bacpypes3.ipv4.bvll import (
    LPDU,
    ReadBroadcastDistributionTable,
    ReadBroadcastDistributionTableAck,
    ReadForeignDeviceTable,
    ReadForeignDeviceTableAck,
)
from bacpypes3.basetypes import (
    BDTEntry,
    HostNPort,
    IPMode,
)
from bacpypes3.ipv4.service import BVLLServiceAccessPoint

from rdflib import Graph, Namespace  # type: ignore
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI


# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
show_warnings: bool = False


async def object_identifiers(
    app: Application, device_address: Address, device_identifier: ObjectIdentifier
) -> List[ObjectIdentifier]:
    """
    Read the entire object list from a device at once, or if that fails, read
    the object identifiers one at a time.
    """
    # segmentation isn't supported
    try:
        object_list = await app.read_property(
            device_address, device_identifier, "object-list"
        )
        return object_list
    except AbortPDU as err:
        if err.apduAbortRejectReason in (
            AbortReason.bufferOverflow,
            AbortReason.segmentationNotSupported,
        ):
            if _debug:
                # object_identifiers._debug("    - object_list err: %r", err)
                print("    - object_list err: %r", err)
        else:
            if show_warnings:
                sys.stderr.write(f"{device_identifier} object-list abort: {err}\n")
            return []
    except ErrorRejectAbortNack as err:
        if show_warnings:
            sys.stderr.write(f"{device_identifier} object-list error/reject: {err}\n")
        return []

    # fall back to reading the length and each element one at a time
    object_list = []
    try:
        # read the length
        object_list_length = await app.read_property(
            device_address,
            device_identifier,
            "object-list",
            array_index=0,
        )
        # read each element individually
        for i in range(object_list_length):
            object_identifier = await app.read_property(
                device_address,
                device_identifier,
                "object-list",
                array_index=i + 1,
            )
            object_list.append(object_identifier)
    except ErrorRejectAbortNack as err:
        if show_warnings:
            sys.stderr.write(
                f"{device_identifier} object-list length error/reject: {err}\n"
            )

    return object_list

async def get_router_networks(app, g):
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


async def get_device_objects(low_limit, high_limit, batch_broadcast_size, app:Application, bacnet_graph, get_properties):
    """
    Get the device objects from the graph
    """
    _log.debug("get_device_objects")
    track_lower = low_limit
    print("starting bounds: ", track_lower)
    while track_lower <= high_limit:
        print("current bounds at ", track_lower)
        track_upper = track_lower + batch_broadcast_size
        if track_upper > high_limit:
            track_upper = high_limit
        i_ams = await app.who_is(track_lower, track_upper)
        for i_am in i_ams:
            print('////////////////////////////////////////////////////////////////////////////')
            print(f"i am: {i_am.pduSource}")
            device_address: Address = i_am.pduSource
            for attr in dir(device_address):
                print(f"{attr}: {getattr(device_address,attr)}")
            device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
            device_graph = bacnet_graph.create_device(device_address, device_identifier)
            bacnet_graph.graph.add((device_graph.device_iri, BACnetNS["vendor_id"], BACnetURI["//vendor/"+str(i_am.vendorID)]))

            # Need to add bbmd subnet to figure out which bbmd to connect to as well
            bacnet_graph.graph.add((device_graph.device_iri, BACnetNS["device-on-network"], BACnetURI["//network/"+str(device_address.addrNet)]))

            if get_properties:
                object_list = await object_identifiers(app, device_address, device_identifier)

                vendor_info = get_vendor_info(i_am.vendorID)
                
                for object_identifier in object_list:
                    object_proxy = device_graph.create_object(object_identifier)
                    # read the property list
                    object_class = vendor_info.get_object_class(object_identifier[0])
                    property_list: Optional[List[PropertyIdentifier]] = None
                    try:
                        property_list = await app.read_property(
                            device_address, object_identifier, "property-list"
                        )
                        if _debug:
                            _log.debug("    - property_list: %r", property_list)
                        # print("    - property_list: %r", property_list)
                        assert isinstance(property_list, list)

                        setattr(
                            object_proxy,
                            "property-list",
                            property_list,
                        )
                    except ErrorRejectAbortNack as err:
                        if show_warnings:
                            sys.stderr.write(
                                f"{object_identifier} property-list error: {err}\n"
                            )
                    except Exception as e:
                        print("Error found identifying property list: ", e)


        track_lower += batch_broadcast_size
    print("get_device_objects Completed")

async def main() -> None:
    app = None
    g = Graph()
    bacnet_graph = BACnetGraph(g)

    try:
        parser = SimpleArgumentParser()
        parser.add_argument(
            "lower",
            type=int,
            nargs='?',  # Makes this argument optional
            default=0,  # Default value if not provided
            help="lower bound of who-is range (optional)"
        )
        parser.add_argument(
            "upper",
            type=int,
            nargs='?',  # Makes this argument optional
            default=4194303,  # Default value if not provided
            help="upper bound of who-is range (optional)"
        )
        parser.add_argument(
            "-o",
            "--output",
            help="output to a file",
        )
        parser.add_argument(
            "-f",
            "--format",
            help="output format",
            default="turtle",
        )

        # add an option to show warnings (argparse.BooleanOptionalAction is 3.9+)
        warnings_parser = parser.add_mutually_exclusive_group(required=False)
        warnings_parser.add_argument("--warnings", dest="warnings", action="store_true")
        warnings_parser.add_argument(
            "--no-warnings", dest="warnings", action="store_false"
        )
        parser.set_defaults(warnings=False)

        args = parser.parse_args()
        if _debug:
            _log.debug("args: %r", args)

        # percolate up to the global
        show_warnings = args.warnings

        # build an application
        app = Application.from_args(args)
        print("App Started")


        # Check router to network
        await get_router_networks(app, g)
        
        # Check device objects
        print("lower bounds: ", args.lower, "   upper bounds: ", args.upper)
        await get_device_objects(args.lower, args.upper, 10000, app, bacnet_graph)

        # dump the graph
        if args.output:
            with open(args.output, "wb") as ttl_file:
                g.serialize(ttl_file, format=args.format)
        else:
            g.serialize(sys.stdout.buffer, format=args.format)

    finally:
        if app:
            app.close()


if __name__ == "__main__":
    asyncio.run(main())
