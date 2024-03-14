import hashlib
import re

from rdflib import BNode, Graph, Literal, Namespace, URIRef  # noqa: F401
from rdflib.namespace import OWL, RDF, RDFS, SH, SKOS  # noqa: F401


class GraphBuilder(object):
    """
    The GraphBuilder class is a utility class to help build a graph.
    The class can be provided an existing graph or create a new graph.
    The class provides methods to create BACnet objects in the graph that \
        represent network topology.
    """

    def __init__(self, site_namespace: str = "site", graph: Graph = None):
        """
        Initialize a GraphBuilder instance and optionally provide an existing graph.
        Bind the default namespaces to the graph.
        """
        self.graph = graph or Graph()
        self.site_namespace = Namespace(f"urn:{site_namespace}/")
        self.bacnet_namespace = Namespace("http://data.ashrae.org/bacnet/2020#")

        if hasattr(self.graph, "namespace_manager"):
            self.graph.namespace_manager.bind("bacnet", self.bacnet_namespace, override=True)
            self.graph.namespace_manager.bind("site", self.site_namespace, override=True)

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

    def graph_to_file(self, file_path: str, format: str = "turtle") -> None:
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

        device_node = self.site_namespace[f"{device_address}_{device_identifier}"]

        if device_identifier >= 4194303:
            raise ValueError("Device ID must be less than 4194303")

        elif device_identifier < 0:
            raise ValueError("Device ID must be greater than 0")

        else:
            self.graph.add(
                triple=(
                    device_node,
                    RDF.type,
                    self.bacnet_namespace["Device"],
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
        bacnet_point = {
            "device_address": device_address,
            "device_identifier": device_identifier,
            "object_type": object_type,
            "object_instance": object_instance,
            "object_name": object_name,
            "description": "A BACnet object",
            "units": "unknown",
        }

        this_point = self.site_namespace[f"{device_address}_{device_identifier}_{object_type}_{object_instance}"]

        # Add a RDFS label for the object name
        self.graph.add(
            triple=(
                this_point,
                RDFS.label,
                Literal(f"{object_name}"),
            )
        )

        # Iterate over a list of object properties and add them to the object
        for key, value in bacnet_point.items():
            self.graph.add(
                triple=(
                    this_point,
                    self.bacnet_namespace[key],
                    Literal(value),
                )
            )
