"""
Custom IPv4 Datagram Server with SO_REUSEPORT support.

This module provides a modified IPv4DatagramServer that creates sockets with
SO_REUSEPORT enabled, allowing multiple BACnet applications to listen on the
same broadcast port (47808) simultaneously.

Based on bacpypes3.ipv4.__init__.IPv4DatagramServer but modified to create
custom sockets before passing to create_datagram_endpoint, similar to the
IPv6 implementation in bacpypes3.ipv6.__init__.IPv6DatagramServer.
"""

import asyncio
import functools
import os
import socket
from typing import Any, Callable, List, Optional, Set, Tuple, cast

from bacpypes3.comm import Server, bind
from bacpypes3.debugging import ModuleLogger, bacpypes_debugging
from bacpypes3.ipv4.bvll import BVLLCodec
from bacpypes3.ipv4.service import BIPNormal, BIPForeign, BIPBBMD, UDPMultiplexer
from bacpypes3.pdu import IPv4Address, LocalBroadcast, PDU

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# move this to settings sometime
BACPYPES_ENDPOINT_RETRY_INTERVAL = 1.0


@bacpypes_debugging
class IPv4DatagramProtocol(asyncio.DatagramProtocol):
    """
    IPv4 datagram protocol handler.

    Handles datagram events and routes them to the server instance.
    """
    _debug: Callable[..., None]

    server: Optional["IPv4DatagramServerWithReusePort"]

    def __init__(self) -> None:
        self.server = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        if _debug:
            IPv4DatagramProtocol._debug("connection_made %r", transport)

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        if _debug:
            IPv4DatagramProtocol._debug("datagram_received %r %r", data, addr)

        # Don't process if server not yet set or is closing
        if self.server is None or self.server._closing:
            return

        pdu = PDU(data, source=IPv4Address(addr))
        self.server._schedule_confirmation(pdu)

    def error_received(self, exc: Exception) -> None:
        if _debug:
            IPv4DatagramProtocol._debug("error_received %r", exc)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if _debug:
            IPv4DatagramProtocol._debug("connection_lost %r", exc)


@bacpypes_debugging
class IPv4DatagramServerWithReusePort(Server[PDU]):
    """
    IPv4 datagram server with SO_REUSEPORT support.

    This server creates sockets with SO_REUSEPORT (and SO_REUSEADDR on Windows)
    to allow multiple BACnet applications to bind to the same broadcast port.

    This is critical for running multiple BACnet tools simultaneously, as they
    all need to listen on UDP port 47808 for broadcasts.

    Based on bacpypes3.ipv4.__init__.IPv4DatagramServer but creates custom
    sockets before passing to create_datagram_endpoint().
    """
    _debug: Callable[..., None]
    _exception: Callable[..., None]
    _transport_tasks: List[Any]
    _pending_tasks: Set[asyncio.Task]
    _closing: bool

    local_address: Tuple[str, int]
    local_transport: Optional[asyncio.DatagramTransport]
    local_protocol: Optional[IPv4DatagramProtocol]
    broadcast_address: Optional[Tuple[str, int]]
    broadcast_transport: Optional[asyncio.DatagramTransport]
    broadcast_protocol: Optional[IPv4DatagramProtocol]

    def __init__(
        self,
        address: IPv4Address,
        no_broadcast: bool = False,
    ) -> None:
        if _debug:
            IPv4DatagramServerWithReusePort._debug(
                "__init__ %r no_broadcast=%r", address, no_broadcast
            )

        # grab the loop to create tasks and endpoints
        loop: asyncio.events.AbstractEventLoop = asyncio.get_running_loop()

        # track pending tasks for clean shutdown
        self._pending_tasks = set()
        self._closing = False

        # save the address
        self.local_address = address.addrTuple
        if _debug:
            IPv4DatagramServerWithReusePort._debug("    - local_address: %r", self.local_address)

        # initialized in set_local_transport_protocol callback
        self.local_transport = None
        self.local_protocol = None

        # initialized in set_broadcast_transport_protocol callback
        self.broadcast_address = None
        self.broadcast_transport = None
        self.broadcast_protocol = None

        # no broadcast if this is an ephemeral port
        if self.local_address[1] == 0:
            no_broadcast = True

        # Use create_datagram_endpoint with reuse_port=True
        # This is simpler and cleaner than pre-creating sockets
        local_endpoint_task = loop.create_task(
            self.retrying_create_datagram_endpoint(loop, address.addrTuple)
        )
        if _debug:
            IPv4DatagramServerWithReusePort._debug(
                "    - local_endpoint_task: %r", local_endpoint_task
            )
        local_endpoint_task.add_done_callback(
            functools.partial(self.set_local_transport_protocol, address)
        )

        # keep a list of things that need to complete before sending stuff
        self._transport_tasks = [local_endpoint_task]

        # see if we need a broadcast listener
        if no_broadcast or (address.addrBroadcastTuple == address.addrTuple):
            pass
        else:
            self.broadcast_address = address.addrBroadcastTuple
            if _debug:
                IPv4DatagramServerWithReusePort._debug(
                    "    - broadcast_address: %r", self.broadcast_address
                )

            # Windows takes care of the broadcast, but Linux needs a broadcast endpoint
            if "nt" not in os.name:
                broadcast_endpoint_task = loop.create_task(
                    self.retrying_create_datagram_endpoint(
                        loop, address.addrBroadcastTuple
                    )
                )
                if _debug:
                    IPv4DatagramServerWithReusePort._debug(
                        "    - broadcast_endpoint_task: %r", broadcast_endpoint_task
                    )
                broadcast_endpoint_task.add_done_callback(
                    functools.partial(self.set_broadcast_transport_protocol, address)
                )
                self._transport_tasks.append(broadcast_endpoint_task)

    def _create_reuseport_socket(self, addrTuple: Tuple[str, int]) -> socket.socket:
        """
        Create a UDP socket with SO_REUSEPORT (and SO_REUSEADDR) enabled.

        This allows multiple BACnet applications to bind to the same port.

        Args:
            addrTuple: (host, port) tuple to bind to

        Returns:
            Configured and bound socket
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Enable SO_REUSEADDR (required on all platforms)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Enable SO_REUSEPORT on platforms that support it (Linux, macOS)
        # This is the key setting that allows multiple processes to bind to the same port
        if hasattr(socket, 'SO_REUSEPORT'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Enable broadcast
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Bind to the address
        sock.bind(addrTuple)

        # Set non-blocking for asyncio
        sock.setblocking(False)

        if _debug:
            IPv4DatagramServerWithReusePort._debug(
                "    - created socket with REUSEPORT: %r bound to %r", sock, addrTuple
            )

        return sock

    async def retrying_create_datagram_endpoint(
        self, loop: asyncio.events.AbstractEventLoop, addrTuple: Tuple[str, int],
        max_retries: int = 3
    ):
        """
        Create datagram endpoint with SO_REUSEPORT enabled.

        Repeat attempts if needed, sometimes during boot the interface isn't ready.
        Contributed by PretentiousPotatoPeeler.

        Creates a pre-built socket with SO_REUSEPORT and passes it to
        create_datagram_endpoint, as Python 3.10+ doesn't support the
        reuse_port parameter directly.

        Args:
            loop: Event loop
            addrTuple: (host, port) tuple to bind to
            max_retries: Maximum number of retry attempts (default 3)

        Returns:
            Tuple of (transport, protocol)

        Raises:
            OSError: If socket creation fails after max_retries attempts
        """
        last_error: Optional[OSError] = None
        for attempt in range(max_retries + 1):
            sock = None
            try:
                # Create socket with SO_REUSEPORT enabled
                sock = self._create_reuseport_socket(addrTuple)

                # Pass the pre-built socket to create_datagram_endpoint
                # The custom bacpypes3 version supports the sock= parameter
                return await loop.create_datagram_endpoint(
                    IPv4DatagramProtocol,
                    sock=sock,
                )
            except OSError as e:
                last_error = e
                if sock:
                    sock.close()
                # Always log the error so we can diagnose issues
                _log.warning(
                    "Could not create datagram endpoint on %s (attempt %d/%d): %s",
                    addrTuple, attempt + 1, max_retries + 1, e
                )
                if attempt < max_retries:
                    await asyncio.sleep(BACPYPES_ENDPOINT_RETRY_INTERVAL)

        # All retries exhausted
        _log.error("Failed to create datagram endpoint on %s after %d attempts", addrTuple, max_retries + 1)
        raise last_error or OSError(f"Failed to create datagram endpoint on {addrTuple}")

    def set_local_transport_protocol(self, address, task):
        if _debug:
            IPv4DatagramServerWithReusePort._debug(
                "set_local_transport_protocol %r, %r", address, task
            )

        # get the results of creating the datagram endpoint
        # Handle cancellation gracefully during shutdown
        try:
            if task.cancelled():
                if _debug:
                    IPv4DatagramServerWithReusePort._debug(
                        "    - task was cancelled (shutdown)"
                    )
                return
            transport, protocol = task.result()
        except asyncio.CancelledError:
            # Task was cancelled during shutdown - this is expected
            if _debug:
                IPv4DatagramServerWithReusePort._debug(
                    "    - task cancelled during shutdown"
                )
            return

        if _debug:
            IPv4DatagramServerWithReusePort._debug(
                "    - transport, protocol: %r, %r", transport, protocol
            )

        # make these the correct type
        self.local_transport = cast(asyncio.DatagramTransport, transport)
        self.local_protocol = cast(IPv4DatagramProtocol, protocol)

        # tell the protocol instance created that it should talk back to us
        self.local_protocol.server = self
        # self.local_protocol.destination = address

        # Windows will use the same transport and protocol for broadcasts
        if "nt" in os.name:
            # make these the correct type
            self.broadcast_transport = cast(asyncio.DatagramTransport, transport)
            self.broadcast_protocol = cast(IPv4DatagramProtocol, protocol)

            # tell the protocol instance created that it should talk back to us
            self.broadcast_protocol.server = self
            self.broadcast_protocol.destination = LocalBroadcast()

    def set_broadcast_transport_protocol(self, address, task):
        if _debug:
            IPv4DatagramServerWithReusePort._debug(
                "set_broadcast_transport_protocol %r, %r", address, task
            )

        # get the results of creating the datagram endpoint
        # Handle cancellation gracefully during shutdown
        try:
            if task.cancelled():
                if _debug:
                    IPv4DatagramServerWithReusePort._debug(
                        "    - task was cancelled (shutdown)"
                    )
                return
            transport, protocol = task.result()
        except asyncio.CancelledError:
            # Task was cancelled during shutdown - this is expected
            if _debug:
                IPv4DatagramServerWithReusePort._debug(
                    "    - task cancelled during shutdown"
                )
            return

        if _debug:
            IPv4DatagramServerWithReusePort._debug(
                "    - transport, protocol: %r, %r", transport, protocol
            )

        # make these the correct type
        self.broadcast_transport = cast(asyncio.DatagramTransport, transport)
        self.broadcast_protocol = cast(IPv4DatagramProtocol, protocol)

        # tell the protocol instance created that it should talk back to us
        self.broadcast_protocol.server = self

    async def indication(self, pdu: PDU) -> None:
        if _debug:
            IPv4DatagramServerWithReusePort._debug("indication %r", pdu)

        # Don't send if we're closing
        if self._closing:
            if _debug:
                IPv4DatagramServerWithReusePort._debug("    - skipping, server closing")
            return

        # wait for set_local_transport_protocol to have been called
        if self._transport_tasks:
            if _debug:
                IPv4DatagramServerWithReusePort._debug(
                    "    - waiting for tasks: %r", self._transport_tasks
                )
            await asyncio.gather(*self._transport_tasks)
            self._transport_tasks = []

        # downstream packets can have a specific or local broadcast address
        if isinstance(pdu.pduDestination, LocalBroadcast):
            pdu_destination = self.broadcast_address
        else:
            pdu_destination = pdu.pduDestination.addrTuple
        if _debug:
            IPv4DatagramServerWithReusePort._debug("    - pdu_destination: %r", pdu_destination)

        # Always send via local_transport to respect the configured source IP.
        # The broadcast_transport (bound to broadcast address) is only for receiving.
        # When bound to a broadcast address, Linux uses routing table to pick source IP,
        # which may not match the configured address. Using local_transport ensures
        # the source IP matches what was configured in BACpypes.ini.
        # Wrap in try/except to handle race conditions during shutdown
        try:
            if self.local_transport:
                self.local_transport.sendto(pdu.pduData, pdu_destination)
        except Exception as e:
            # Transport may be closing/closed - don't crash
            if _debug:
                IPv4DatagramServerWithReusePort._debug("    - send failed: %s", e)

    def _schedule_confirmation(self, pdu: PDU) -> None:
        """Schedule a confirmation task and track it for clean shutdown."""
        if self._closing:
            return

        task = asyncio.ensure_future(self.confirmation(pdu))
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def confirmation(self, pdu: PDU) -> None:
        if _debug:
            IPv4DatagramServerWithReusePort._debug("confirmation %r", pdu)

        # check for reflection (getting our own broadcasts back)
        assert isinstance(pdu.pduSource, IPv4Address)
        if pdu.pduSource.addrTuple == self.local_address:
            if _debug:
                IPv4DatagramServerWithReusePort._debug("    - broadcast/reflected?")

        # up the stack it goes
        await self.response(pdu)

    def close(self) -> None:
        if _debug:
            IPv4DatagramServerWithReusePort._debug("close")

        # Mark as closing to prevent new tasks
        self._closing = True

        # Cancel any pending transport tasks
        for task in self._transport_tasks:
            if not task.done():
                task.cancel()

        # Cancel any pending confirmation tasks
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()

        # close the transports
        if self.local_transport:
            self.local_transport.close()
        if self.broadcast_transport and self.broadcast_transport != self.local_transport:
            self.broadcast_transport.close()


#
#   NormalLinkLayerWithReusePort
#


@bacpypes_debugging
class NormalLinkLayerWithReusePort(BIPNormal):
    """
    Create a link layer mini-stack with SO_REUSEPORT support.

    This extends the standard BIPNormal with a custom datagram server
    that enables SO_REUSEPORT, allowing multiple BACnet applications
    to bind to the same broadcast port simultaneously.
    """

    codec: BVLLCodec
    multiplexer: UDPMultiplexer
    server: IPv4DatagramServerWithReusePort

    def __init__(self, local_address: IPv4Address, **kwargs) -> None:
        if _debug:
            NormalLinkLayerWithReusePort._debug(
                "__init__ %r %r",
                local_address,
                kwargs,
            )
        BIPNormal.__init__(self, **kwargs)

        # create a normal B/IP stack with REUSEPORT server
        self.codec = BVLLCodec()
        self.multiplexer = UDPMultiplexer()
        self.server = IPv4DatagramServerWithReusePort(local_address)

        bind(self, self.codec, self.multiplexer.annexJ)  # type: ignore[arg-type]
        bind(self.multiplexer, self.server)  # type: ignore[arg-type]

    def close(self):
        if _debug:
            NormalLinkLayerWithReusePort._debug("close")
        self.server.close()


#
#   ForeignLinkLayerWithReusePort
#


@bacpypes_debugging
class ForeignLinkLayerWithReusePort(BIPForeign):
    """
    Create a foreign link layer mini-stack with SO_REUSEPORT support.

    This extends the standard BIPForeign with a custom datagram server
    that enables SO_REUSEPORT for BBMD foreign device registration scenarios.
    """

    codec: BVLLCodec
    multiplexer: UDPMultiplexer
    server: IPv4DatagramServerWithReusePort

    def __init__(self, local_address: IPv4Address, **kwargs) -> None:
        if _debug:
            ForeignLinkLayerWithReusePort._debug(
                "__init__ %r %r",
                local_address,
                kwargs,
            )
        BIPForeign.__init__(self, **kwargs)

        # create a foreign B/IP stack with REUSEPORT server
        self.codec = BVLLCodec()
        self.multiplexer = UDPMultiplexer()
        self.server = IPv4DatagramServerWithReusePort(local_address)

        bind(self, self.codec, self.multiplexer.annexJ)  # type: ignore[arg-type]
        bind(self.multiplexer, self.server)  # type: ignore[arg-type]

    def close(self):
        if _debug:
            ForeignLinkLayerWithReusePort._debug("close")
        self.server.close()


#
#   BBMDLinkLayerWithReusePort
#


@bacpypes_debugging
class BBMDLinkLayerWithReusePort(BIPBBMD):
    """
    Create a BBMD link layer mini-stack with SO_REUSEPORT support.

    This extends the standard BIPBBMD with a custom datagram server
    that enables SO_REUSEPORT for BBMD scenarios.
    """

    codec: BVLLCodec
    multiplexer: UDPMultiplexer
    server: IPv4DatagramServerWithReusePort

    def __init__(self, local_address: IPv4Address, **kwargs) -> None:
        if _debug:
            BBMDLinkLayerWithReusePort._debug(
                "__init__ %r %r",
                local_address,
                kwargs,
            )
        BIPBBMD.__init__(self, **kwargs)

        # create a BBMD B/IP stack with REUSEPORT server
        self.codec = BVLLCodec()
        self.multiplexer = UDPMultiplexer()
        self.server = IPv4DatagramServerWithReusePort(local_address)

        bind(self, self.codec, self.multiplexer.annexJ)  # type: ignore[arg-type]
        bind(self.multiplexer, self.server)  # type: ignore[arg-type]

    def close(self):
        if _debug:
            BBMDLinkLayerWithReusePort._debug("close")
        self.server.close()
