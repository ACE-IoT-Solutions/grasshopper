import hashlib
import re

from rdflib import BNode, Graph, Literal, Namespace, URIRef  # noqa: F401
from rdflib.namespace import OWL, RDF, RDFS, SH, SKOS  # noqa: F401

# Namespaces - TODO: Better way to handle these?
BACNET = Namespace("http://data.ashrae.org/bacnet/2020#")
SITE = Namespace("urn:site/")


class GraphBuilder(object):
    """
    The GraphBuilder class is a utility class to help build a graph.
    The class can be provided an existing graph or create a new graph.
    The class provides methods to create BACnet objects in the graph that \
        represent network topology.
    """

    def __init__(self, graph: Graph = None):
        """
        Initialize a GraphBuilder instance and optionally provide an existing graph.
        Bind the default namespaces to the graph.
        """
        self.graph = graph or Graph()

        if hasattr(self.graph, "namespace_manager"):
            self.graph.namespace_manager.bind("bacnet", BACNET, override=True)
            self.graph.namespace_manager.bind("site", SITE, override=True)

    def generate_graph_hash(self) -> str:
        """
        Generate a hash of the graph data.
        """
        return hashlib.sha256(string=self.serialize()).hexdigest()

    @staticmethod
    def clean_rdf_name(name: str) -> str:
        """
        Clean a string using regex to replace spaces, hyphens, periods, and slashes with underscores.
        """
        return re.sub(r"[ -./\\]", "_", name)

    def serialize(self, format: str = "turtle") -> bytes:
        """
        Serialize the graph to a string using the specified format.
        The format must be supported by the rdflib library.
        """
        return self.graph.serialize(format=format, encoding="utf-8")

    def graph_to_file(self, file_path: str = "../_stash/graph.ttl", format: str = "turtle") -> None:
        """
        Serialize the graph to a file using the specified format.
        The format must be supported by the rdflib library.

        """
        self.graph.serialize(destination=file_path, format=format)

    def parse_remote(self, uri: str, format: str = "turtle") -> None:
        """
        Parse a remote graph from a URI.
        """
        self.graph.parse(uri, format=format)

    def add_namespace(
        self,
        prefix: str,
        uri: str,
    ) -> None:
        """
        Add a namespace to the graph.
        """
        self.graph.bind(prefix=prefix, namespace=Namespace(uri), override=False)

    def add_bacnet_device(
        self,
        device_address: str,
        device_identifier: int,
    ):
        """
        Add a BACnet device to the graph.
        Use common name?
        """

        device_node = SITE[f"{device_address}_{device_identifier}"]

        if device_identifier >= 4194303:
            raise ValueError("Device ID must be less than 4194303")

        elif device_identifier < 0:
            raise ValueError("Device ID must be greater than 0")

        else:
            self.graph.add(
                triple=(
                    device_node,
                    RDF.type,
                    BACNET["Device"],
                )
            )

    def add_bacnet_object(
        self,
        device_address: str,
        device_identifier: int,
        object_type: str,
        object_instance: int,
        object_name: str,
    ):
        """
        Add a BACnet object to the graph.
        """
        self.graph.add(
            triple=(
                SITE[f"{device_address}_{device_identifier}"],
                BACNET["contains"],
                SITE[f"{device_address}_{device_identifier}_{object_type}_{object_instance}"],
            )
        )

        # Add a RDFS label for the object name
        self.graph.add(
            triple=(
                SITE[f"{device_address}_{device_identifier}_{object_type}_{object_instance}"],
                RDFS.label,
                Literal(f"{object_name}"),
            )
        )

        self.graph.add(
            triple=(
                SITE[f"{device_address}_{device_identifier}_{object_type}_{object_instance}"],
                RDF.type,
                BACNET[object_type],
            )
        )


if __name__ == "__main__":
    # Create a new graph builder
    builder = GraphBuilder()

    # Bind the site namespace to the graph
    builder.add_namespace(prefix="site", uri="urn:site/")

    # Create a dict of a BACnet device
    bacnet_device = {
        "device_address": "10.0.0.100",
        "device_identifier": 1000,
    }

    # Add a BACnet device to the graph
    builder.add_bacnet_device(**bacnet_device)

    # Create a dict of a BACnet object for the device
    bacnet_object = {
        "device_address": "10.0.0.100",
        "device_identifier": 1000,
        "object_type": "AnalogInput",
        "object_instance": int(1000),
        "object_name": "Zone Temperature",
    }

    # Add the BACnet object to the graph
    builder.add_bacnet_object(**bacnet_object)

    # Serialize the graph to a string
    data: str = builder.serialize(format="turtle")

    # Generate a hash of the graph data
    hash = builder.generate_graph_hash()

    if hash != hash:
        print("Graph has changed. Update the version number.")
    else:
        print("Graph has not changed.")

    bacnet_object_1 = {
        "device_address": "10.0.0.101",
        "device_identifier": 1001,
        "object_type": "AnalogInput",
        "object_instance": int(1001),
        "object_name": "Room Temperature",
    }

    # Add the BACnet object to the graph
    builder.add_bacnet_object(**bacnet_object_1)

    # Serialize the graph to a string
    updated_hash = builder.generate_graph_hash()

    # Compare the hashes using hashlib and if they do not match update the version number
    if hash != updated_hash:
        print("Graph has changed. Update the version number.")
    else:
        print("Graph has not changed.")

    # Serialize the graph to a file
    builder.graph_to_file()
