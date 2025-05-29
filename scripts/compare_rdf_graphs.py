from rdflib import Graph
from rdflib.compare import to_isomorphic, graph_diff
from convert_ttl_to_html_graph import build_networkx_graph
from pyvis.network import Network


def pass_networkx_to_pyvis(nx_graph, net: Network, data, color, image=None):
    shape = "image" if image else "dot"
    for node in nx_graph.nodes:
        if "router/" in node:
            size = 30
            title = "Router Node"
        elif "network/" in node:
            size = 20
            title = "Network Node"
        else:
            size = 10
            title = str(data.get(node, {}))
        if image:
            net.add_node(
                node,
                size=size,
                title=title,
                shape=shape,
                image=image,
                data=data.get(node, {}),
                color=color,
            )
        else:
            net.add_node(
                node, size=size, title=title, data=data.get(node, {}), color=color
            )
    print("edges: ", len(nx_graph.edges))
    for edge in nx_graph.edges(data=True):
        label = edge[2].get("label", "")
        net.add_edge(edge[0], edge[1], label=label)


g1 = Graph()
g2 = Graph()
g1.parse("graph1.ttl", format="ttl")
g2.parse("graph2.ttl", format="ttl")

iso_g1 = to_isomorphic(g1)
iso_g2 = to_isomorphic(g2)

in_both, in_first, in_second = graph_diff(iso_g1, iso_g2)

nx_graph_in_both, node_data_in_both = build_networkx_graph(in_both)
nx_graph_in_first, node_data_in_first = build_networkx_graph(in_first)
nx_graph_in_second, node_data_in_second = build_networkx_graph(in_second)

net = Network(notebook=True, bgcolor="#222222", font_color="white", filter_menu=False)
pass_networkx_to_pyvis(nx_graph_in_both, net, node_data_in_both, "grey")
pass_networkx_to_pyvis(
    nx_graph_in_first, net, node_data_in_first, "red", "bacnet_scan/imgs/minus.png"
)
pass_networkx_to_pyvis(
    nx_graph_in_second, net, node_data_in_second, "green", "bacnet_scan/imgs/plus.png"
)
net.show_buttons(filter_=["physics"])
net.write_html(f"compare.html")
