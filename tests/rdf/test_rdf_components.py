import os
import sys
from typing import Set

from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI
from rdflib import RDF, Graph, Literal

# Add the parent directory (A) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("Current working directory:", os.getcwd())
from Grasshopper.grasshopper.rdf_components import (
    BBMDNode,
    DeviceNode,
    NetworkNode,
    RouterNode,
    SubnetNode,
)

EXPECTED_TURTLE = """
@prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<bacnet://Grasshopper> a bacnet:Device ;
    rdfs:label "Grasshopper" ;
    bacnet:address "123.123.123.123" ;
    bacnet:device-instance 123 ;
    bacnet:device-on-subnet <bacnet://subnet/1> ;
    bacnet:vendor-id <bacnet://vendor/999> .

<bacnet://network/1> a bacnet:Network ;
    rdfs:label "Network 1" .

<bacnet://subnet/1> a bacnet:Subnet ;
    rdfs:label "Subnet 1" .
"""

def test_rdf_components():
    """Test the creation of RDF components for BACnet"""
    # Create a new graph
    graph = Graph()
    graph.bind("bacnet", BACnetNS)
    scanner_node = DeviceNode(graph, BACnetURI["//Grasshopper"])
    scanner_node.add_properties(
        label="Grasshopper",
        device_identifier=123,
        device_address="123.123.123.123",
        vendor_id="999",
    )

    subnet = SubnetNode(graph, BACnetURI["//subnet/1"])
    subnet.add_properties(
        label="Subnet 1",
    )

    network = NetworkNode(graph, BACnetURI["//network/1"])
    network.add_properties(
        label="Network 1",
    )

    scanner_node.add_properties(subnet=1)

    actual = graph.serialize(format="turtle")
    norm = lambda s: "\n".join(line.rstrip() for line in s.strip().splitlines())
    print(norm(actual))
    print('///////////////////////////////////////////////////')
    print(norm(EXPECTED_TURTLE))
    assert norm(actual) == norm(EXPECTED_TURTLE)
