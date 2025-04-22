"""
This module contains the base class for all devices in the RDF graph.
Uses composition for building devices
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Union

from bacpypes3.rdf.core import BACnetNS, BACnetURI
from rdflib import RDF, Graph, Literal, Namespace, URIRef  # type: ignore
from rdflib.namespace import RDFS


class BACnetEdgeType(Enum):
    """Enum for BACnet edge types."""

    BBMD_BROADCAST_DOMAIN = "bbmd-broadcast-domain"  # bbmd->subnet
    BACNET_ROUTER_ON_SUBNET = "bacnet-router-on-subnet"  # bacnet-router->subnet
    DEVICE_ON_SUBNET = "device-on-subnet"  # device->subnet
    DEVICE_ON_NETWORK = "device-on-network"  # device->bacnet-network (this can be an MSTP network id, or a a bacnet global network ID on a ip subnet, by default 1 on IP) it should be hidden by default for IP devices
    ROUTER_FOR_SUBNET = "router-for-subnet"  # ip-router->subnet (this is a new device class that we haven't implemented yet)
    BDT_ENTRY = "bdt-entry"  # bbmd->bbmd
    FDR_ENTRY = "fdr-entry"  # bbmd->device


class BaseTypeHandler(ABC):
    """Abstract base class for BACnet device type handlers."""

    @abstractmethod
    def set_type(self, device):
        """Assign RDF.type for the given device."""
        raise NotImplementedError("Subclasses must implement this method")


class DeviceTypeHandler(BaseTypeHandler):
    """Handles assigning RDF.type for a standard BACnet device."""

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Device)


class BBMDTypeHandler(BaseTypeHandler):
    """Handles assigning RDF.type for a BBMD device."""

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.BBMD)


class RouterTypeHandler(BaseTypeHandler):
    """Handles assigning RDF.type for a Router device."""

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Router)


class SubnetTypeHandler(BaseTypeHandler):
    """Handles assigning RDF.type for a Subnet device."""

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Subnet)


class NetworkTypeHandler(BaseTypeHandler):
    """Handles assigning RDF.type for a Network device."""

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Network)


class BaseNode:
    """Core BACnet node that assigns an IRI and manages RDF properties."""

    def __init__(
        self, graph: Graph, node_iri: URIRef, type_handler: BaseTypeHandler
    ) -> None:
        self.graph = graph
        self.node_iri = node_iri
        self.type_handler = type_handler
        self.set_type()

    def overwrite_triple(
        self, predicate: URIRef, new_object: Union[URIRef, Literal]
    ) -> None:
        """Overwrites existing triples, except reserved ones."""
        if "device-on-network" not in str(predicate) and "router-to-network" not in str(
            predicate
        ):
            self.graph.set((self.node_iri, predicate, new_object))  # type: ignore
        else:
            self.graph.add((self.node_iri, predicate, new_object))  # type: ignore

    def set_type(self):
        """Delegate type setting to the assigned handler."""
        if self.type_handler:
            self.type_handler.set_type(self)

    def add_properties(self, label: Optional[str] = None, **kwargs) -> None:
        """Add properties to the node."""
        if label:
            self.overwrite_triple(RDFS.label, Literal(label))


class SubnetNode(BaseNode):
    """A BACnet subnet node that can include network, or additional behavior via composition."""

    def __init__(self, graph, node_iri):
        super().__init__(graph, node_iri, SubnetTypeHandler())


class NetworkNode(BaseNode):
    """A BACnet network node that can include subnet, or additional behavior via composition."""

    def __init__(self, graph, node_iri):
        super().__init__(graph, node_iri, NetworkTypeHandler())


class BaseBACnetComponent(ABC):
    """Abstract base class for BACnet device components."""

    def __init__(self, edge_type: BACnetEdgeType):
        self.edge_type = edge_type

    @abstractmethod
    def add_properties(self, device: BaseNode, **kwargs):
        """Each component must implement this method."""
        raise NotImplementedError("Subclasses must implement this method")


class SubnetComponent(BaseBACnetComponent):
    """Component for handling subnet properties."""

    def add_properties(self, device: BaseNode, **kwargs):
        subnet = kwargs.get("subnet")
        if subnet:
            device.overwrite_triple(
                BACnetNS[self.edge_type.value], BACnetURI["//subnet/" + str(subnet)]
            )


class NetworkComponent(BaseBACnetComponent):
    """Component for handling network properties."""

    def add_properties(self, device: BaseNode, **kwargs):
        network_id = kwargs.get("network_id")
        if network_id:
            device.overwrite_triple(
                BACnetNS[self.edge_type.value],
                BACnetURI["//network/" + str(network_id)],
            )


class AttachDeviceComponent(BaseBACnetComponent):
    """Component for attaching devices to a network/another device."""

    def add_properties(self, device: BaseNode, **kwargs):
        device_iri = kwargs.get("device_iri")
        if device_iri:
            device.overwrite_triple(BACnetNS[self.edge_type.value], device_iri)


class BACnetNode(BaseNode):
    """A BACnet node that can include subnet, network, or additional behavior via composition."""

    def __init__(
        self,
        graph,
        device_iri,
        type_handler,
        components: Optional[List[BaseBACnetComponent]] = None,
    ):
        super().__init__(graph, device_iri, type_handler)
        self.device = BaseNode(graph, device_iri, type_handler)
        self.components = components or []

    def add_properties(
        self,
        label: Optional[str] = None,
        device_identifier: Optional[str] = None,
        device_address: Optional[str] = None,
        vendor_id: Optional[int] = None,
        **kwargs
    ) -> None:
        """Add properties common to all devices."""
        super().add_properties(label=label, **kwargs)
        if device_identifier:
            self.overwrite_triple(
                BACnetNS["device-instance"], Literal(device_identifier)
            )
        if device_address:
            self.overwrite_triple(BACnetNS["address"], Literal(str(device_address)))
        if vendor_id:
            self.overwrite_triple(
                BACnetNS["vendor-id"], BACnetURI["//vendor/" + str(vendor_id)]
            )

        for component in self.components:
            component.add_properties(self.device, **kwargs)


class BBMDNode(BACnetNode):
    """A BBMD node that can include subnet, network, or additional behavior via composition."""

    def __init__(self, graph, device_iri):
        components = [
            AttachDeviceComponent(BACnetEdgeType.BDT_ENTRY),
            # AttachDeviceComponent(BACnetEdgeType.FDR_ENTRY),
            # NetworkComponent(BACnetEdgeType.DEVICE_ON_NETWORK),
            SubnetComponent(BACnetEdgeType.BBMD_BROADCAST_DOMAIN),
        ]
        super().__init__(graph, device_iri, BBMDTypeHandler(), components)


class DeviceNode(BACnetNode):
    """A standard BACnet device node that can include subnet, network, or additional behavior via composition."""

    def __init__(self, graph, device_iri):
        components = [
            NetworkComponent(BACnetEdgeType.DEVICE_ON_NETWORK),
            SubnetComponent(BACnetEdgeType.DEVICE_ON_SUBNET),
        ]
        super().__init__(graph, device_iri, DeviceTypeHandler(), components)


class RouterNode(BACnetNode):
    """A BACnet router node that can include subnet, network, or additional behavior via composition."""

    def __init__(self, graph, device_iri):
        components = [
            NetworkComponent(BACnetEdgeType.DEVICE_ON_NETWORK),
            SubnetComponent(BACnetEdgeType.DEVICE_ON_SUBNET),
        ]
        super().__init__(graph, device_iri, RouterTypeHandler(), components)
