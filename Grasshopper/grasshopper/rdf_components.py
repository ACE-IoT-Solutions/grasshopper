"""
This module contains the base class for all devices in the RDF graph.
Uses composition for building devices
"""
from abc import ABC, abstractmethod
from typing import List
from rdflib import Graph, Namespace, RDF, Literal, URIRef  # type: ignore
from rdflib.namespace import RDFS
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI



class BaseTypeHandler(ABC):
    """Abstract base class for BACnet device type handlers."""
    
    @abstractmethod
    def set_type(self, device):
        """Assign RDF.type for the given device."""
        raise NotImplementedError("Subclasses must implement this method")


class DeviceTypeHandler:
    """Handles assigning RDF.type for a standard BACnet device."""
    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Device)

class BBMDTypeHandler:
    """Handles assigning RDF.type for a BBMD device."""
    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.BBMD)

class RouterTypeHandler:
    """Handles assigning RDF.type for a Router device."""
    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Router)

class SubnetTypeHandler:
    """Handles assigning RDF.type for a Router device."""
    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Subnet)

class NetworkTypeHandler:
    """Handles assigning RDF.type for a Router device."""
    def set_type(self, device):
        device.overwrite_triple(RDF.type, BACnetNS.Network)


class BaseNode:
    """Core BACnet node that assigns an IRI and manages RDF properties."""
    
    def __init__(self, graph: Graph, node_iri: URIRef, type_handler: BaseTypeHandler)->None:
        self.graph = graph
        self.node_iri = node_iri
        self.type_handler = type_handler 
        self.set_type()

    def overwrite_triple(self, predicate:str, new_object:str)->None:
        """Overwrites existing triples, except reserved ones."""
        if 'device-on-network' not in predicate and 'router-to-network' not in predicate:
            self.graph.set((self.node_iri, predicate, new_object))
        else:
            self.graph.add((self.node_iri, predicate, new_object))

    def set_type(self):
        """Delegate type setting to the assigned handler."""
        if self.type_handler:
            self.type_handler.set_type(self)


class BaseBACnetComponent(ABC):
    """Abstract base class for BACnet device components."""

    @abstractmethod
    def add_properties(self, device: BaseNode, **kwargs):
        """Each component must implement this method."""
        raise NotImplementedError("Subclasses must implement this method")


class SubnetComponent(BaseBACnetComponent):
    """Component for handling subnet properties."""
    def add_properties(self, device: BaseNode, subnet=None, **kwargs):
        if subnet:
            device.overwrite_triple(
                BACnetNS["device-on-network"],
                BACnetURI["//subnet/" + str(subnet)]
            )

class NetworkComponent(BaseBACnetComponent):
    """Component for handling network properties."""
    def add_properties(self, device: BaseNode, network_id=None, **kwargs):
        if network_id:
            device.overwrite_triple(
                BACnetNS["device-on-network"],
                BACnetURI["//network/" + str(network_id)]
            )

class AttachDeviceComponent(BaseBACnetComponent):
    """Component for attaching devices to a network/another device."""
    def add_properties(self, device: BaseNode, device_iri=None, **kwargs):
        if device_iri:
            device.overwrite_triple(
                BACnetNS["device-on-network"],
                device_iri
            )


class BACnetNode:
    """A BACnet node that can include subnet, network, or additional behavior via composition."""

    def __init__(self, graph, device_iri, type_handler, components:List[BaseBACnetComponent]=None):
        self.device = BaseNode(graph, device_iri, type_handler)
        self.components = components or []

    def add_common_properties(self, label:str=None, device_identifier:str=None, device_address:str=None, vendor_id:int=None)->None:
        """Add properties common to all devices. Used if the Bacnet nodes is a device."""
        if label:
            self.overwrite_triple(RDFS.label, Literal(label))
        if device_identifier:
            self.overwrite_triple(BACnetNS["device-instance"], Literal(device_identifier[1]))
        if device_address:
            self.overwrite_triple(BACnetNS["address"], Literal(str(device_address)))
        if vendor_id:
            self.overwrite_triple(BACnetNS["vendor-id"], BACnetURI["//vendor/" + str(vendor_id)])

    def add_component_properties(self, device_identifier, device_address, vendor_id, **kwargs):
        """Delegates property addition to components. Good for everything"""
        for component in self.components:
            component.add_properties(self, self.device, **kwargs)

    


# # Creating valid components
# subnet = SubnetComponent()
# network = NetworkComponent()

# # Passing them into BACnetDevice
# device = BACnetDevice(graph, device_iri, type_handler, components=[subnet, network])

# # This will fail (Solution 2 only) because "InvalidComponent" is not a subclass of BaseComponent
# device.components.append("InvalidComponent")