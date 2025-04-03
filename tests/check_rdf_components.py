
from rdflib import Graph, Literal, RDF
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI

from typing import Set
from Grasshopper.grasshopper.rdf_components import BACnetNode, DeviceTypeHandler, SubnetTypeHandler, NetworkTypeHandler, AttachDeviceComponent, NetworkComponent, SubnetComponent

def get_networks_from_graph(g: Graph) -> Set[int]:
    """Return a set of network numbers from the graph"""
    networks = set()
    for t in g.triples((None, RDF.type, BACnetNS["Network"])):
        networks.add(int(t[0].split('/')[-1]))
    return networks


graph = Graph()

scanner_node = BACnetNode(graph, BACnetURI["//Grasshopper"], DeviceTypeHandler(), [AttachDeviceComponent(), NetworkComponent(), SubnetComponent()])
scanner_node.add_common_properties(
    label="Grasshopper",
    device_identifier=123,
    device_address='123.123.123.123',
    vendor_id='999'
)

subnet = BACnetNode(graph, BACnetURI["//subnet/1"], SubnetTypeHandler())
subnet.add_common_properties(
    label="Subnet 1",
)

network = BACnetNode(graph, BACnetURI["//network/1"], NetworkTypeHandler())
network.add_common_properties(
    label="Network 1",
)


scanner_node.add_component_properties(
    subnet=1
)

print(isinstance(scanner_node.device.type_handler, DeviceTypeHandler))

print(graph.serialize(format='turtle'))