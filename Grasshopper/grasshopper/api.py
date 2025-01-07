import os
import json
import gevent
import uuid
from gevent.queue import Queue
from concurrent.futures import ProcessPoolExecutor
from http import HTTPStatus
from rdflib import Graph, Namespace, Literal  # type: ignore
from rdflib.compare import to_isomorphic, graph_diff
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph, rdflib_to_networkx_graph
from rdflib.namespace import RDFS
from bacpypes3.rdf.core import BACnetGraph, BACnetNS, BACnetURI

import networkx as nx
from pyvis.network import Network
from bacpypes3.rdf.core import BACnetNS
from pyvis.network import Network
from flask import Blueprint, jsonify, request, send_file, abort
from flask_restx import Namespace, Resource, fields
from .restplus import api
from .serializers import file_list, compare_ttl_files
from .parser import file_upload_parser


api = Namespace('operations', __name__, url_prefix='/operations')

compare_rdf_queue = Queue()
processing_task = None
executor = ProcessPoolExecutor(max_workers=1)  

def process_compare_rdf_queue():
    global processing_task
    while True:
        try:
            task = compare_rdf_queue.get()
            if task is None:
                break
            processing_task = task
            ttl_filename_1 = task.get('ttl_1')
            ttl_filename_2 = task.get('ttl_2')
            print(f"{task=}")
            print(f"task ttl1 get {task.get('ttl_1')} and task ttl2 get {task.get('ttl_2')}")
            ttl_filepath_1 = get_file_path(ttl_filename_1)
            ttl_filepath_2 = get_file_path(ttl_filename_2)

            g1 = Graph()
            g2 = Graph()
            g1.parse(ttl_filepath_1, format='ttl')
            gevent.sleep(0)

            g2.parse(ttl_filepath_2, format='ttl')
            gevent.sleep(0)

            iso_g1 = to_isomorphic(g1)
            iso_g2 = to_isomorphic(g2)
            gevent.sleep(0)

            # in_both, in_first, in_second = graph_diff(iso_g1, iso_g2)
            future = executor.submit(graph_diff, iso_g1, iso_g2)
            while not future.done():
                gevent.sleep(0)

            in_both, in_first, in_second = future.result()  

            combined_graph = Graph()

            for s, p, o in in_first:
                gevent.sleep(0)
                combined_graph.add((s, p, o))
                triple_id = Literal(f"{s} {p} {o}")
                combined_graph.add((triple_id, BACnetNS["rdf_diff_source"], Literal(ttl_filename_1)))
            
            for s, p, o in in_second:
                gevent.sleep(0)
                combined_graph.add((s, p, o))
                triple_id = Literal(f"{s} {p} {o}")
                combined_graph.add((triple_id, BACnetNS["rdf_diff_source"], Literal(ttl_filename_2)))

            for s, p, o in in_both:
                gevent.sleep(0)
                combined_graph.add((s, p, o))

            current_dir = os.path.dirname(os.path.abspath(__file__))
            compare_folder_path = os.path.join(current_dir, 'compare')
            combined_filename = f"{ttl_filename_1.replace('.ttl', '')}_vs_{ttl_filename_2.replace('.ttl', '')}.ttl"
            combined_filepath = os.path.join(compare_folder_path, combined_filename)
            combined_graph.serialize(destination=combined_filepath, format='ttl')

            processing_task = None
        except Exception as e:
            print(f"Error processing task: {e}")

gevent.spawn(process_compare_rdf_queue)

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


def get_file_path(file_name, folder = 'ttl'):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(current_dir, folder)
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"The folder '{folder}' does not exist in the current directory.")

    for root, dirs, files in os.walk(folder_path):
        if file_name in files:
            return os.path.join(root, file_name)

    return None

def list_files_in_dir(folder = 'ttl'):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(current_dir, folder)
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    return files


@api.route('/hello')
class HelloWorld(Resource):
    def get(self):
        """Returns a simple greeting message."""
        return {"message": "Hello, world!"}

@api.route('/ttl')
class TTL(Resource):
    def get(self):
        """Gets ttl list"""
        data = []
        graph_ttl_roots = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ttl/'))
        if os.path.exists(graph_ttl_roots):
            for filename in os.listdir(graph_ttl_roots):
                if filename.endswith('.ttl'):
                    data.append(filename)
        return jsonify({"data": data})

    @api.expect(file_upload_parser)
    def post(self):
        """Upload ttl file"""
        ALLOWED_EXTENSIONS = {'ttl'}

        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        current_dir = os.path.dirname(os.path.abspath(__file__))
        ttl_dir = os.path.join(current_dir, 'ttl')
        if 'file' not in request.files:
            return {"error": "No file part in the request"}, HTTPStatus.BAD_REQUEST

        file = request.files['file']
        if file.filename == '':
            return {"error": "No selected file"}, HTTPStatus.BAD_REQUEST

        if file and allowed_file(file.filename):
            file_path = os.path.join(ttl_dir, file.filename)
            file.save(file_path)
            return {"message": f"File {file.filename} uploaded successfully", "file_path": file_path}, HTTPStatus.CREATED
        else:
            return {"error": "File type not allowed"}, HTTPStatus.BAD_REQUEST


# Upload, delete, download ttl file
@api.route('/ttl_file/<ttl_filename>')
class ttl_file(Resource):
    def get(self, ttl_filename):
        """Download ttl file"""
        ttl_filepath = get_file_path(ttl_filename)
        if not ttl_filepath:
            return "File not found", HTTPStatus.NOT_FOUND

        try:
            return send_file(ttl_filepath, as_attachment=True)
        except FileNotFoundError:
            abort(404, description="File not found")
        except Exception as e:
            abort(500, description=str(e))

    def delete(self, ttl_filename):
        """Delete ttl file"""
        ttl_filepath = get_file_path(ttl_filename)
        if not ttl_filepath:
            return "File not found", HTTPStatus.NOT_FOUND

        if os.path.exists(ttl_filepath):
            os.remove(ttl_filepath)
            return jsonify({"message": "File deleted successfully"})
        else:
            return jsonify({"error": "File not found"}), HTTPStatus.NOT_FOUND
        

@api.route('/ttl_network/<ttl_filename>')
class ttl_network(Resource):
    def get(self, ttl_filename):
        """Get ttl file network in json"""
        ttl_filepath = get_file_path(ttl_filename)
        if not ttl_filepath:
            return "File not found", HTTPStatus.NOT_FOUND

        g = Graph()
        g.parse(ttl_filepath, format="ttl")
        nx_graph, node_data, edge_data = build_networkx_graph(g)

        net = Network()
        pass_networkx_to_pyvis(nx_graph, net, node_data, edge_data)
        net_data = {
            "nodes": net.nodes,
            "edges": net.edges
        }
        return jsonify(net_data)

@api.route('/ttl_compare_queue')
class ttl_compare_queue(Resource):
    @api.expect(compare_ttl_files)
    @api.response(400, "Bad Request")
    def post(self):
        """Adds ttl compare file request to queue"""
        data = request.json
        ttl_filename_1 = data.get('ttl_1')
        ttl_filename_2 = data.get('ttl_2')
        ttl_filepath_1 = get_file_path(ttl_filename_1)
        ttl_filepath_2 = get_file_path(ttl_filename_2)
        if not ttl_filepath_1 or not ttl_filepath_2:
            return "File not found", HTTPStatus.NOT_FOUND
        
        queue_contents = list(compare_rdf_queue.queue)
        if processing_task:
            queue_contents.append(processing_task)
        
        for task in queue_contents:
            if (task.get("ttl_1") == ttl_filename_1 and task.get("ttl_2") == ttl_filename_2) or \
                (task.get("ttl_1") == ttl_filename_2 and task.get("ttl_2") == ttl_filename_1):
                return "Task already in queue ", HTTPStatus.BAD_REQUEST

        compare_rdf_queue.put({"id": str(uuid.uuid4()),"ttl_1": ttl_filename_1, "ttl_2": ttl_filename_2})
        return "File accepted", HTTPStatus.ACCEPTED

    def get(self):
        """Gets current queue and processing task"""
        queue_contents = list(compare_rdf_queue.queue)
        return {
            "processing_task": processing_task if processing_task else "None",
            "queue": queue_contents
        }, HTTPStatus.OK

@api.route('/ttl_compare_queue_tasks/<string:task_id>')
class ttl_compare_queue(Resource):
    def delete(self, task_id):
        """Removes task from queue"""
        global compare_rdf_queue
        if processing_task and processing_task.get("id") == task_id:
            return {"status": "error", "message": "Task is currently being processed"}, HTTPStatus.BAD_REQUEST
        queue_contents = list(compare_rdf_queue.queue)
        new_queue = [task for task in queue_contents if task["id"] != task_id]

        if len(new_queue) == len(queue_contents):
            return {"status": "error", "message": f"Task {task_id} not found"}, HTTPStatus.NOT_FOUND

        compare_rdf_queue = Queue()
        for task in new_queue:
            compare_rdf_queue.put(task)

        return {"status": "success", "message": f"Task {task_id} removed from the queue"}, HTTPStatus.OK

# /compare_rdf_graphs
@api.route('/ttl_compare')
class ttl_compare(Resource):
    @api.marshal_with(file_list)
    def get(self):
        """Get list of comparison ttl files"""
        file_list = list_files_in_dir(folder = 'compare')
        return {"file_list": file_list}

    # @api.expect(compare_ttl_files)
    # def post(self):
    #     """Create a new ttl compare file and returns json"""
    #     data = request.json
    #     ttl_filename_1 = data.get('ttl_1')
    #     ttl_filename_2 = data.get('ttl_2')
    #     ttl_filepath_1 = get_file_path(ttl_filename_1)
    #     ttl_filepath_2 = get_file_path(ttl_filename_2)
    #     if not ttl_filepath_1 or not ttl_filepath_2:
    #         return "File not found", HTTPStatus.NOT_FOUND

    #     g1 = Graph()
    #     g2 = Graph()
    #     g1.parse(ttl_filepath_1, format='ttl')
    #     g2.parse(ttl_filepath_2, format='ttl')

    #     iso_g1 = to_isomorphic(g1)
    #     iso_g2 = to_isomorphic(g2)
    #     in_both, in_first, in_second = graph_diff(iso_g1, iso_g2)

    #     combined_graph = Graph()

    #     for s, p, o in in_first:
    #         combined_graph.add((s, p, o))
    #         triple_id = Literal(f"{s} {p} {o}")
    #         combined_graph.add((triple_id, BACnetNS["rdf_diff_source"], Literal(ttl_filename_1)))
        
    #     for s, p, o in in_second:
    #         combined_graph.add((s, p, o))
    #         triple_id = Literal(f"{s} {p} {o}")
    #         combined_graph.add((triple_id, BACnetNS["rdf_diff_source"], Literal(ttl_filename_2)))

    #     for s, p, o in in_both:
    #         combined_graph.add((s, p, o))

    #     current_dir = os.path.dirname(os.path.abspath(__file__))
    #     compare_folder_path = os.path.join(current_dir, 'compare')
    #     combined_filename = f"{ttl_filename_1.replace('.ttl', '')}_vs_{ttl_filename_2.replace('.ttl', '')}.ttl"
    #     combined_filepath = os.path.join(compare_folder_path, combined_filename)
    #     combined_graph.serialize(destination=combined_filepath, format='ttl')

    #     nx_graph, node_data, edge_data = build_networkx_graph(combined_graph)

    #     net = Network()
    #     pass_networkx_to_pyvis(nx_graph, net, node_data, edge_data)
    #     net_data = {
    #         "nodes": net.nodes,
    #         "edges": net.edges
    #     }
    #     return jsonify(net_data)



@api.route('/ttl_compare/<ttl_filename>')
class ttl_compare_file(Resource):
    def get(self, ttl_filename):
        """Get network json from compare file"""
        ttl_filepath = get_file_path(ttl_filename, folder='compare')
        if not ttl_filepath:
            return "File not found", HTTPStatus.NOT_FOUND

        g = Graph()
        g.parse(ttl_filepath, format="ttl")
        nx_graph, node_data, edge_data = build_networkx_graph(g)

        net = Network()
        pass_networkx_to_pyvis(nx_graph, net, node_data, edge_data)
        net_data = {
            "nodes": net.nodes,
            "edges": net.edges
        }
        return jsonify(net_data)

    def delete(self, ttl_filename):
        """Delete ttl compare file"""
        ttl_filepath = get_file_path(ttl_filename, folder='compare')
        if not ttl_filepath:
            return "File not found", HTTPStatus.NOT_FOUND

        if os.path.exists(ttl_filepath):
            os.remove(ttl_filepath)
            return jsonify({"message": f"File {ttl_filename} deleted successfully"})
        else:
            return jsonify({"error": "File not found"}), HTTPStatus.NOT_FOUND
