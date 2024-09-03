"""
Example script that runs a BACnet scan and creates an RDF graph of the devices relative to the router.

Usage:

python discover_routers_and_devices.py 1000 10000 --output test.ttl --address 192.168.1.203/24:47809 > log.txt
"""

import sys
import asyncio

from typing import List, Optional

from bacpypes3.debugging import bacpypes_debugging, ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser

from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.basetypes import PropertyIdentifier
from bacpypes3.apdu import AbortReason, AbortPDU, ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.vendor import get_vendor_info

from rdflib import Graph, Namespace  # type: ignore
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI


# some debugging
_debug = 1
_log = ModuleLogger(globals())

# globals
show_warnings: bool = False

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
            default=None,  # Default value if not provided
            help="lower bound of who-is range (optional)"
        )
        parser.add_argument(
            "upper",
            type=int,
            nargs='?',  # Makes this argument optional
            default=None,  # Default value if not provided
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
        routers = await app.nse.who_is_router_to_network()
        print("routers: ", routers)
        for adapter, i_am_router_to_network in routers:
            for net in i_am_router_to_network.iartnNetworkList:
                g.add((BACnetURI["//router/"+str(i_am_router_to_network.pduSource)], BACnetNS["router-to-network"], BACnetURI["//network/"+str(net)]))
        print("done checking routers") 
        
        # look for the device
        if args.lower and args.upper:
            i_ams = await app.who_is(args.lower, args.upper, timeout=300)
        else:
            i_ams = await app.who_is()
        if not i_ams:
            sys.stderr.write("device not found\n")
            sys.exit(1)

        for i_am in i_ams:
            if _debug:
                _log.debug("    - i_am: %r", i_am)

            device_address: Address = i_am.pduSource
            device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier

            # create a device object in the graph and return it like a context
            device_graph = bacnet_graph.create_device(device_address, device_identifier)
            g.add((device_graph.device_iri, BACnetNS["i-am"], BACnetURI["//network/"+str(device_address.addrNet)]))
            g.add((device_graph.device_iri, BACnetNS["vendor_id"], BACnetURI["//vendor/"+str(i_am.vendorID)]))


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
