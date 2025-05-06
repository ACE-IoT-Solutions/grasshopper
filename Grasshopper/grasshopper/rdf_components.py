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
    """
    Enumeration defining the relationship types between BACnet entities in the RDF graph.
    
    These edge types represent the various relationships between BACnet entities such as
    devices, routers, BBMDs, networks, and subnets in the network topology. They are used
    to create consistent edge predicates in the RDF graph.
    """

    # BBMD connects to a subnet
    BBMD_BROADCAST_DOMAIN = "bbmd-broadcast-domain"
    
    # Router is connected to a subnet
    BACNET_ROUTER_ON_SUBNET = "bacnet-router-on-subnet"
    
    # Device is connected to a subnet
    DEVICE_ON_SUBNET = "device-on-subnet"
    
    # Device is assigned to a BACnet network
    # This can be an MSTP network ID or a BACnet global network ID on an IP subnet
    # By default 1 on IP, typically hidden for IP devices
    DEVICE_ON_NETWORK = "device-on-network"
    
    # Router provides routing for a subnet (not yet implemented)
    ROUTER_FOR_SUBNET = "router-for-subnet"
    
    # BBMD has another BBMD in its Broadcast Distribution Table
    BDT_ENTRY = "bdt-entry"
    
    # BBMD has a device registered as a Foreign Device
    FDR_ENTRY = "fdr-entry"


class BaseTypeHandler(ABC):
    """
    Abstract base class for BACnet device type handlers.
    
    Type handlers are responsible for assigning the correct RDF type to BACnet nodes
    in the graph. This class defines the interface that all type handlers must implement.
    The Strategy pattern is used here to allow different types of BACnet entities to be
    handled by specialized type handlers.
    """

    @abstractmethod
    def set_type(self, device):
        """
        Assign RDF.type for the given device.
        
        Args:
            device: The BACnet node to assign a type to
        
        Raises:
            NotImplementedError: If the subclass does not implement this method
        """
        raise NotImplementedError("Subclasses must implement this method")


class DeviceTypeHandler(BaseTypeHandler):
    """
    Handles assigning RDF.type for a standard BACnet device.
    
    This type handler assigns the BACnet Device type to nodes in the RDF graph.
    Standard devices are the most common type of BACnet entity.
    """

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Device)


class BBMDTypeHandler(BaseTypeHandler):
    """
    Handles assigning RDF.type for a BBMD (BACnet Broadcast Management Device).
    
    This type handler assigns the BACnet BBMD type to nodes in the RDF graph.
    BBMDs are special devices that manage broadcast communications across IP subnets.
    """

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.BBMD)


class RouterTypeHandler(BaseTypeHandler):
    """
    Handles assigning RDF.type for a BACnet Router device.
    
    This type handler assigns the BACnet Router type to nodes in the RDF graph.
    Routers connect different BACnet networks and allow devices to communicate across them.
    """

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Router)


class SubnetTypeHandler(BaseTypeHandler):
    """
    Handles assigning RDF.type for a Subnet entity.
    
    This type handler assigns the BACnet Subnet type to nodes in the RDF graph.
    Subnets represent IP subnets that contain BACnet devices.
    """

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Subnet)


class NetworkTypeHandler(BaseTypeHandler):
    """
    Handles assigning RDF.type for a Network entity.
    
    This type handler assigns the BACnet Network type to nodes in the RDF graph.
    Networks represent BACnet networks, which can be IP, MSTP, or other types.
    """

    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Network)


class BaseNode:
    """
    Core BACnet node that assigns an IRI and manages RDF properties.
    
    This is the base class for all BACnet entities in the RDF graph. It provides
    common functionality for managing node properties and types in the graph.
    It uses the Strategy pattern with type handlers to determine the RDF type
    of the node.
    """

    def __init__(
        self, graph: Graph, node_iri: URIRef, type_handler: BaseTypeHandler
    ) -> None:
        """
        Initialize a BaseNode with the given graph, IRI, and type handler.
        
        Args:
            graph (Graph): The RDF graph to add this node to
            node_iri (URIRef): The IRI that uniquely identifies this node
            type_handler (BaseTypeHandler): The handler that sets the RDF type for this node
        """
        self.graph = graph
        self.node_iri = node_iri
        self.type_handler = type_handler
        self.set_type()

    def overwrite_triple(
        self, predicate: URIRef, new_object: Union[URIRef, Literal]
    ) -> None:
        """
        Overwrites existing triples, except for special network relationships.
        
        For most predicates, this method removes existing triples with the same
        subject and predicate before adding the new triple. For network relationship
        predicates like 'device-on-network' and 'router-to-network', it preserves
        existing triples and just adds the new one.
        
        Args:
            predicate (URIRef): The predicate (relationship) to set
            new_object (Union[URIRef, Literal]): The object (value) to set
        """
        if str(predicate) in BACnetEdgeType._value2member_map_:
            self.graph.set((self.node_iri, predicate, new_object))  # type: ignore
        else:
            self.graph.add((self.node_iri, predicate, new_object))  # type: ignore

    def set_type(self):
        """
        Delegate type setting to the assigned handler.
        
        This method calls the set_type method of the type handler to assign
        the appropriate RDF type to this node.
        """
        if self.type_handler:
            self.type_handler.set_type(self)

    def add_properties(self, label: Optional[str] = None, **kwargs) -> None:
        """
        Add properties to the node.
        
        This method adds a label to the node if provided. Subclasses can override
        this method to add additional properties.
        
        Args:
            label (Optional[str], optional): The label for the node. Defaults to None.
            **kwargs: Additional properties to add to the node
        """
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
