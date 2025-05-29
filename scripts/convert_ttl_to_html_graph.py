"""
node attributes:
label: The text label shown next to the node.
title: A tooltip that appears when you hover over the node.
color: The color of the node. You can specify a color name, HEX code, or RGB value.
size: The size of the node. This is usually given in pixels.
shape: The shape of the node. Possible values include "dot", "star", "triangle", "box", "diamond", "square", "ellipse", and more.
image: If the shape is "image", this specifies the URL of the image to display.
physics: Whether the node is affected by physics (e.g., repulsion, attraction). Set to False if you want the node to be fixed.
group: Nodes with the same group are often given similar visual properties. This can be used to cluster nodes visually.
borderWidth: The width of the border around the node.
hidden: Whether the node is hidden (i.e., not displayed).

edge attributes:
label: The text label shown next to the edge.
title: A tooltip that appears when you hover over the edge.
color: The color of the edge. You can specify a color name, HEX code, or RGB value. You can also specify colors for the hover and highlight states.
width: The width of the edge line.
arrows: Specifies if and where arrows should be shown on the edge. Possible values include "from", "to", "middle", "from;to", etc.
dashes: If set to True, the edge line will be dashed. You can also specify a list of dash lengths (e.g., [5, 10]).
length: The length of the edge (affects the spacing between nodes).
smooth: Defines whether and how the edge is drawn smoothly. Possible values include "dynamic", "continuous", "discrete", "diagonalCross", "straightCross", "horizontal", "vertical", "curvedCW", "curvedCCW", "cubicBezier", etc.
hidden: Whether the edge is hidden (i.e., not displayed).
"""
from rdflib import Graph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
import networkx as nx
from pyvis.network import Network
from bacpypes3.rdf.core import BACnetNS
from rdflib.namespace import RDFS

def build_networkx_graph(g):
    """
    Build a networkx graph from the BACnet graph
    """
    def custom_edge_attrs(s, p, o):
        if RDFS._NS in p:
            label = p
        else:
            label = f"{str(p).split('#')[-1]}"
        return {
            "label": label,
            "color": "red",
        }

    def custom_transform_node_str(s):
        if RDFS._NS in s:
            return s
        elif BACnetNS in s:
            return f"{str(s).split('#')[-1]}"
        else:
            return s

    nx_graph = rdflib_to_networkx_digraph(
        g, 
        edge_attrs=custom_edge_attrs,
        transform_s=custom_transform_node_str,
        transform_o=custom_transform_node_str,
    )

    is_directed = nx_graph.is_directed()
    print(f"Is the graph directed? {is_directed}")

    remove_nodes = []
    rdf_edges = {}
    device_address_edges = []
    data = {}
    for u, v, attr in nx_graph.edges(data=True):
        label = attr.get("label", "")
        if RDFS._NS in label:
            print("rdfs: ", u, v)
            rdf_edges[u] = v
            remove_nodes.append(u)
            remove_nodes.append(v)
        elif 'device-address' in label:
            device_address_edges.append((u, v))
        elif 'device-instance' in label:
            if u in data:
                data[u]['device instance'] = str(v)
            else:
                data[u] = {'device instance': str(v)}
            remove_nodes.append(v)
        elif str(label) == 'a':
            if u in data:
                data[u]['bacnet type'] = str(v)
            else:
                data[u] = {'bacnet type': str(v)}
            remove_nodes.append(v)
        elif label not in ['device-on-network', 'router-to-network']:
            remove_nodes.append(v)
        elif label == 'device-on-network' and 'network/None' in v:
            remove_nodes.append(v)
            remove_nodes.append(u)

    for u, v in device_address_edges:
        if u in data:
            data[u]['device address'] = str(rdf_edges[v])
        else:
            data[u] = {'device address': str(rdf_edges[v])}

    nx_graph.remove_nodes_from(remove_nodes)
    
    return nx_graph, data

def pass_networkx_to_pyvis(nx_graph, net:Network, data):
    for node in nx_graph.nodes:
        if "router/" in node:
            color = "cyan"
            size = 30
            title = "Router Node"
        elif "network/" in node:
            color = "green"
            size = 20
            title = "Network Node"
        else:
            color = "red"
            size = 10
            title = str(data.get(node, {}))

        net.add_node(node, size=size, title=title, data=data.get(node, {}), color=color)

    print("edges: ", len(nx_graph.edges))
    for edge in nx_graph.edges(data=True):
        label = edge[2].get("label", "")
        net.add_edge(edge[0], edge[1], label=label)


g = Graph()
g.parse("/home/jlee/.volttron/agents/458aa06c-40ac-4b3f-9390-43dc87ae3f96/grasshopperagent-0.1/grasshopper/webroot/grasshopper/graphs/ttl/test_low.ttl", format="ttl")
nx_graph, node_data = build_networkx_graph(g)
    

net = Network(notebook=True, bgcolor="#222222", font_color="white", filter_menu=False)
pass_networkx_to_pyvis(nx_graph, net, node_data)
net.show_buttons(filter_=['physics'])
net.write_html(f"test_low.html")
