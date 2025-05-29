
import json
import argparse

from rdflib import Graph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
from rdflib.namespace import RDFS
from pyvis.network import Network
from pyvis.network import Network


def build_networkx_graph(g):
    """
    Build a networkx graph from the BACnet graph

    Note: device_address_edges is utilized to deal with Bacpypes3 original format, however it is no longer utilized.
    This is utilized for backward compatibility support. It may be removed in the future.
    """
    nx_graph = rdflib_to_networkx_digraph(g)

    is_directed = nx_graph.is_directed()
    print(f"Is the graph directed? {is_directed}")

    remove_nodes = []
    rdf_edges = {}
    device_address_edges = []
    rdf_diff_list = []
    node_data = {}
    edge_data = {}
    for u, v, attr in nx_graph.edges(data=True):
        edge_label = attr.get('triples', [])[0][1] if 'triples' in attr else None
        if RDFS['label'] in edge_label:
            rdf_edges[u] = v
            remove_nodes.append(u)
            remove_nodes.append(v)
        elif 'rdf_diff_source' in edge_label:
            rdf_diff_list.append((u,v,edge_label))
        elif 'device-address' in edge_label:
            device_address_edges.append((u, v))
            remove_nodes.append(v)
        elif 'device-on-network' not in edge_label and 'router-to-network' not in edge_label:
            label = edge_label.split('#')[-1]
            val = str(v).split('#')[-1]
            if str(u) in node_data:
                node_data[str(u)][label] = val
            else:
                node_data[str(u)] = {label: val}
            remove_nodes.append(v)


    for u, v in device_address_edges:
        if str(u) in node_data:
            if v in rdf_edges:
                node_data[str(u)]['device-address'] = str(rdf_edges[v])
            else:
                node_data[str(u)]['device-address'] = str(v)
        else:
            if v in rdf_edges:
                node_data[str(u)] = {'device-address': str(rdf_edges[v])}
            else:
                node_data[str(u)] = {'device-address': str(v)}

    for u, v, edge_label in rdf_diff_list:
        edge_id = str(u)
        s, p, o = edge_id.split(' ')
        if 'device-on-network' in p or 'router-to-network' in p:
            if s in node_data:
                node_data[s][edge_label] = str(v)
            else:
                node_data[s] = {edge_label: str(v)}
            if o in node_data:
                node_data[o][edge_label] = str(v)
            else:
                node_data[o] = {edge_label: str(v)}
        if u in edge_data:
            edge_data[edge_id][edge_label] = str(v)
        else:
            edge_data[edge_id] = {edge_label: str(v)}

        remove_nodes.append(u)
        remove_nodes.append(v)


    nx_graph.remove_nodes_from(remove_nodes)
    
    return nx_graph, node_data, edge_data

def pass_networkx_to_pyvis(nx_graph, net:Network, node_data, edge_data):
    for node in nx_graph.nodes:
        net.add_node(node, data=node_data.get(str(node), {}))

    for u, v, attr in nx_graph.edges(data=True):
        edge_label = attr.get('triples', [])[0][1] if 'triples' in attr else None
        edge_id = f"{u} {edge_label} {v}"
        net.add_edge(u, v, label=edge_label, data=edge_data.get(edge_id, {}))


def convert_ttl_to_json(ttl_filepath):
    """Get ttl file network in json"""
    if not ttl_filepath:
        return None

    g = Graph()
    g.parse(ttl_filepath, format="ttl")
    nx_graph, node_data, edge_data = build_networkx_graph(g)

    net = Network()
    pass_networkx_to_pyvis(nx_graph, net, node_data, edge_data)
    net_data = {
        "nodes": net.nodes,
        "edges": net.edges
    }
    return net_data

def main():
    parser = argparse.ArgumentParser(description="Convert TTL file to JSON format.")
    parser.add_argument("input", help="Path to the input TTL file.")
    parser.add_argument("output", help="Path to the output JSON file.")
    args = parser.parse_args()

    try:
        print(f"Reading from: {args.input}")
        net_data = convert_ttl_to_json(args.input)
        if net_data:
            with open(args.output, "w") as json_file:
                json.dump(net_data, json_file, indent=4)
            print(f"JSON data written to: {args.output}")
        else:
            print("Conversion failed. Ensure the input TTL file is valid.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()