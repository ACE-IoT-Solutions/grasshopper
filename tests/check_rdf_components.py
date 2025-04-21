
from rdflib import Graph, Literal, RDF
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI

from typing import Set
import os
import sys

# Add the parent directory (A) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Current working directory:", os.getcwd())
from Grasshopper.grasshopper.rdf_components import DeviceNode, BBMDNode, RouterNode, BACnetNode, SubnetNode, NetworkNode

def get_networks_from_graph(g: Graph) -> Set[int]:
    """Return a set of network numbers from the graph"""
    networks = set()
    for t in g.triples((None, RDF.type, BACnetNS["Network"])):
        networks.add(int(t[0].split('/')[-1]))
    return networks


graph = Graph()
graph.bind('bacnet', BACnetNS)
scanner_node = DeviceNode(graph, BACnetURI["//Grasshopper"])
scanner_node.add_properties(
    label="Grasshopper",
    device_identifier=123,
    device_address='123.123.123.123',
    vendor_id='999'
)

subnet = SubnetNode(graph, BACnetURI["//subnet/1"])
subnet.add_properties(
    label="Subnet 1",
)

network = NetworkNode(graph, BACnetURI["//network/1"])
network.add_properties(
    label="Network 1",
)


scanner_node.add_properties(
    subnet=1
)

print(graph.serialize(format='turtle'))