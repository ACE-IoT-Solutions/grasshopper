"""API endpoints for Grasshopper using FastAPI"""

import csv
import json
import os
import uuid
from concurrent.futures import ProcessPoolExecutor
from http import HTTPStatus
from io import BytesIO, StringIO
from multiprocessing import Queue
from typing import Any, Dict, List, Optional, Union

import gevent
from bacpypes3.rdf.core import BACnetNS
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from pyvis.network import Network
from rdflib import Graph, Literal, Namespace  # type: ignore
from rdflib.compare import graph_diff, to_isomorphic
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph

from .rdf_components import BACnetEdgeType
from .serializers import (
    CompareTTLFiles,
    ErrorResponse,
    FileList,
    FileUploadResponse,
    IPAddress,
    IPAddressList,
    MessageResponse,
)

# Create a multiprocessing queue for compare_rdf operations
compare_rdf_queue = Queue()

DEVICE_STATE_CONFIG: str = "device_config.json"

# Create FastAPI router
api_router = APIRouter(prefix="/operations", tags=["operations"])


def get_agent_data_path(request: Request) -> str:
    """Get agent data path from app state.

    Args:
        request (Request): The FastAPI request object

    Returns:
        str: Path to the agent data directory, or empty string if not found
    """
    return request.app.extra.get("agent_data_path", "")


def get_task_queue(request: Request) -> Queue:
    """Get agent task queue from app state.

    Args:
        request (Request): The FastAPI request object

    Returns:
        Queue: The multiprocessing queue for tasks
    """
    return request.app.state.task_queue


def get_processing_task(request: Request) -> Queue:
    """Get processing task queue from app state.

    Args:
        request (Request): The FastAPI request object

    Returns:
        Queue: The multiprocessing queue for tasks currently being processed
    """
    return request.app.state.processing_task_queue


def process_compare_rdf_queue(task_queue: Queue, processing_task_queue: Queue) -> None:
    """Process the compare RDF queue in background.

    This function runs as a separate process and continually processes tasks from the queue.
    For each task, it:
    1. Gets two TTL files from the queue
    2. Parses them into RDF graphs
    3. Computes the difference between the graphs
    4. Creates a combined graph with difference markers
    5. Serializes the combined graph to a new TTL file

    Args:
        task_queue (Queue): Queue containing tasks to be processed
        processing_task_queue (Queue): Queue for tracking tasks currently being processed

    Returns:
        None: This function runs indefinitely until the process is terminated
    """
    while True:
        try:
            task = task_queue.get()
            if task is None:
                break
            processing_task_queue.put(task)
            ttl_filename_1 = task.get("ttl_1")
            ttl_filename_2 = task.get("ttl_2")
            agent_data_path = task.get("agent_data_path")
            print(f"{task=}")
            print(
                f"task ttl1 get {task.get('ttl_1')} and task ttl2 get {task.get('ttl_2')}"
            )
            ttl_filepath_1 = os.path.join(agent_data_path, f"ttl/{ttl_filename_1}")
            ttl_filepath_2 = os.path.join(agent_data_path, f"ttl/{ttl_filename_2}")
            if not os.path.exists(ttl_filepath_1):
                raise FileNotFoundError(
                    f"The file '{ttl_filename_1}' does not exist in the current directory."
                )

            if not os.path.exists(ttl_filepath_2):
                raise FileNotFoundError(
                    f"The file '{ttl_filename_2}' does not exist in the current directory."
                )

            g1 = Graph()
            g2 = Graph()
            g1.parse(ttl_filepath_1, format="ttl")
            g2.parse(ttl_filepath_2, format="ttl")

            # Convert to isomorphic graphs for accurate comparison
            iso_g1 = to_isomorphic(g1)
            iso_g2 = to_isomorphic(g2)

            # Get differences between graphs
            in_both, in_first, in_second = graph_diff(iso_g1, iso_g2)

            combined_graph = Graph()

            # Add triples from first graph with source marker
            for s, p, o in in_first:
                combined_graph.add((s, p, o))
                triple_id = Literal(f"{s} {p} {o}")
                combined_graph.add(
                    (triple_id, BACnetNS["rdf_diff_source"], Literal(ttl_filename_1))
                )

            # Add triples from second graph with source marker
            for s, p, o in in_second:
                combined_graph.add((s, p, o))
                triple_id = Literal(f"{s} {p} {o}")
                combined_graph.add(
                    (triple_id, BACnetNS["rdf_diff_source"], Literal(ttl_filename_2))
                )

            # Add triples present in both graphs
            for s, p, o in in_both:
                combined_graph.add((s, p, o))

            # Save the combined graph
            compare_folder_path = os.path.join(agent_data_path, "compare")
            combined_filename = f"{ttl_filename_1.replace('.ttl', '')}_vs_{ttl_filename_2.replace('.ttl', '')}.ttl"
            combined_filepath = os.path.join(compare_folder_path, combined_filename)
            combined_graph.serialize(destination=combined_filepath, format="ttl")

            # Mark task as complete
            processing_task_queue.get()
        except Exception as e:
            print(f"Error processing task: {e}")


def build_networkx_graph(g: Graph):
    """
    Build a networkx graph from the BACnet RDF graph.

    This function converts an RDFLib graph to a NetworkX graph that can be used
    for visualization and network analysis. It also extracts node and edge attributes
    for display in the UI.

    Args:
        g (Graph): The RDFLib graph containing BACnet network information

    Returns:
        tuple: Contains:
            - nx_graph: The NetworkX graph object
            - node_data: Dictionary of node attributes
            - edge_data: Dictionary of edge attributes

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
        edge_label = attr.get("triples", [])[0][1] if "triples" in attr else None
        if "rdf_diff_source" in edge_label:
            rdf_diff_list.append((u, v, edge_label))
        elif all(edge.value not in edge_label for edge in BACnetEdgeType):
            label = edge_label.split("#")[-1]
            val = str(v).split("#")[-1]
            if str(u) in node_data:
                node_data[str(u)][label] = val
            else:
                node_data[str(u)] = {label: val}
            remove_nodes.append(v)

    for u, v in device_address_edges:
        if str(u) in node_data:
            if v in rdf_edges:
                node_data[str(u)]["device-address"] = str(rdf_edges[v])
            else:
                node_data[str(u)]["device-address"] = str(v)
        else:
            if v in rdf_edges:
                node_data[str(u)] = {"device-address": str(rdf_edges[v])}
            else:
                node_data[str(u)] = {"device-address": str(v)}

    for u, v, edge_label in rdf_diff_list:
        edge_id = str(u)
        s, p, o = edge_id.split(" ")
        if "device-on-network" in p or "router-to-network" in p:
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


def pass_networkx_to_pyvis(
    nx_graph, net: Network, node_data: dict, edge_data: dict
) -> None:
    """Convert networkx graph to pyvis network for visualization.

    This function takes a NetworkX graph and converts it to a PyVis network object,
    which can be used for interactive visualization. It adds nodes and edges with
    their associated metadata.

    Args:
        nx_graph: The NetworkX graph object
        net (Network): The PyVis network object to populate
        node_data (dict): Dictionary of node attributes
        edge_data (dict): Dictionary of edge attributes

    Returns:
        None: The network object is modified in-place
    """
    for node in nx_graph.nodes:
        net.add_node(node, data=node_data.get(str(node), {}))

    for u, v, attr in nx_graph.edges(data=True):
        edge_label = attr.get("triples", [])[0][1] if "triples" in attr else None
        edge_id = f"{u} {edge_label} {v}"
        net.add_edge(u, v, label=edge_label, data=edge_data.get(edge_id, {}))


def get_file_path(
    file_name: str, request: Request, folder: str = "ttl"
) -> Optional[str]:
    """Get absolute file path for a file in the agent data directory.

    This function looks for a specified file within the agent data directory
    and returns its absolute path if found.

    Args:
        file_name (str): The name of the file to find
        request (Request): The FastAPI request object containing app state
        folder (str, optional): The subdirectory to search in. Defaults to "ttl".

    Returns:
        Optional[str]: The absolute path to the file if found, None otherwise

    Raises:
        FileNotFoundError: If the specified folder doesn't exist
    """
    agent_data_path = get_agent_data_path(request)
    folder_path = os.path.join(agent_data_path, folder)
    if not os.path.exists(folder_path):
        raise FileNotFoundError(
            f"The folder '{folder}' does not exist in the current directory."
        )

    for root, dirs, files in os.walk(folder_path):
        if file_name in files:
            return os.path.join(root, file_name)

    return None


def list_files_in_dir(request: Request, folder: str = "ttl") -> List[str]:
    """List files in the specified directory within the agent data path.

    Args:
        request (Request): The FastAPI request object containing app state
        folder (str, optional): The subdirectory to list files from. Defaults to "ttl".

    Returns:
        List[str]: A list of filenames in the specified directory
    """
    agent_data_path = get_agent_data_path(request)
    folder_path = os.path.join(agent_data_path, folder)
    files = [
        f
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]
    return files


@api_router.get("/hello", response_model=MessageResponse)
async def hello_world():
    """Returns a simple greeting message."""
    return {"message": "Hello, world!"}


@api_router.get("/ttl")
async def get_ttl_list(request: Request):
    """Gets ttl list"""
    data = []
    agent_data_path = get_agent_data_path(request)
    graph_ttl_roots = os.path.join(agent_data_path, "ttl/")
    if os.path.exists(graph_ttl_roots):
        for filename in os.listdir(graph_ttl_roots):
            if filename.endswith(".ttl"):
                data.append(filename)
    return {"data": data}


@api_router.post(
    "/ttl",
    status_code=status.HTTP_201_CREATED,
    response_model=Union[FileUploadResponse, ErrorResponse],
)
async def upload_ttl_file(request: Request, file: UploadFile = File(...)):
    """Upload ttl file"""
    ALLOWED_EXTENSIONS = {"ttl"}

    def allowed_file(filename):
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    agent_data_path = get_agent_data_path(request)
    ttl_dir = os.path.join(agent_data_path, "ttl")

    if not file:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "No file part in the request"},
        )

    if file.filename == "" or not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "No selected file"},
        )

    if file and allowed_file(file.filename):
        file_path = os.path.join(ttl_dir, file.filename)

        # Save the file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        return {
            "message": f"File {file.filename} uploaded successfully",
            "file_path": file_path,
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "File type not allowed"},
        )


@api_router.get("/ttl_file/{ttl_filename}")
async def download_ttl_file(ttl_filename: str, request: Request):
    """Download ttl file"""
    ttl_filepath = get_file_path(ttl_filename, request)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    try:
        return FileResponse(ttl_filepath, filename=ttl_filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@api_router.delete("/ttl_file/{ttl_filename}", response_model=MessageResponse)
async def delete_ttl_file(ttl_filename: str, request: Request):
    """Delete ttl file"""
    ttl_filepath = get_file_path(ttl_filename, request)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if os.path.exists(ttl_filepath):
        os.remove(ttl_filepath)
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )


@api_router.get("/ttl_network/{ttl_filename}")
async def get_ttl_network(ttl_filename: str, request: Request):
    """Get ttl file network in json"""
    ttl_filepath = get_file_path(ttl_filename, request)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    g = Graph()
    g.parse(ttl_filepath, format="ttl")
    nx_graph, node_data, edge_data = build_networkx_graph(g)

    net = Network()
    pass_networkx_to_pyvis(nx_graph, net, node_data, edge_data)
    net_data = {"nodes": net.nodes, "edges": net.edges}
    return net_data


def get_list_from_queue(queue: Queue) -> List[Dict[str, Any]]:
    """Get list of tasks from the queue without removing them.

    This function extracts all items from a queue, saves them to a list,
    and then puts them back into the queue, effectively allowing inspection
    of queue contents without consuming them.

    Args:
        queue (Queue): The multiprocessing queue to inspect

    Returns:
        List[Dict[str, Any]]: A list of all tasks currently in the queue
    """
    tasks = []
    while not queue.empty():
        task = queue.get()
        tasks.append(task)

    for task in tasks:
        queue.put(task)

    return tasks


@api_router.post("/ttl_compare_queue", status_code=status.HTTP_202_ACCEPTED)
async def add_ttl_compare_queue(
    compare_files: CompareTTLFiles,
    request: Request,
    queue=Depends(get_task_queue),
    processing_task=Depends(get_processing_task),
):
    """Add TTL comparison request to the processing queue.

    This endpoint allows clients to request a comparison between two TTL files.
    The comparison is performed asynchronously, with the result saved as a new TTL file.

    Args:
        compare_files (CompareTTLFiles): Object containing the names of TTL files to compare
        request (Request): The FastAPI request object
        queue (Queue): The task queue (injected by FastAPI)
        processing_task (Queue): The processing task queue (injected by FastAPI)

    Returns:
        dict: A message confirming the task was accepted and the task details

    Raises:
        HTTPException: If files are not found or a duplicate task already exists
    """
    ttl_filename_1 = compare_files.ttl_1
    ttl_filename_2 = compare_files.ttl_2
    ttl_filepath_1 = get_file_path(ttl_filename_1, request=request)
    ttl_filepath_2 = get_file_path(ttl_filename_2, request=request)

    if not ttl_filepath_1 or not ttl_filepath_2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both TTL files not found",
        )

    queue_contents = get_list_from_queue(queue)
    current_task = get_list_from_queue(processing_task)
    if current_task:
        queue_contents.append(current_task[0])

    for task in queue_contents:
        if (
            task.get("ttl_1") == ttl_filename_1 and task.get("ttl_2") == ttl_filename_2
        ) or (
            task.get("ttl_1") == ttl_filename_2 and task.get("ttl_2") == ttl_filename_1
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task already queued or in progress",
            )

    # enqueue a new task
    task = {
        "id": str(uuid.uuid4()),
        "ttl_1": ttl_filename_1,
        "ttl_2": ttl_filename_2,
        "agent_data_path": get_agent_data_path(request),
    }
    queue.put(task)
    return {"message": "File accepted", "task": task}


@api_router.get("/ttl_compare_queue")
async def get_ttl_compare_queue(
    queue=Depends(get_task_queue),
    processing=Depends(get_processing_task),
):
    """Gets current queue and processing task"""
    processing_task = get_list_from_queue(processing)
    if processing_task:
        current_task = processing_task[0]
    else:
        current_task = None
    queued_tasks = get_list_from_queue(queue)
    return {
        "processing_task": current_task,
        "queue": queued_tasks,
    }


@api_router.delete("/ttl_compare_queue_tasks/{task_id}")
async def delete_ttl_compare_queue_task(
    task_id: str,
    request: Request,
    queue=Depends(get_task_queue),
    processing=Depends(get_processing_task),
):
    """Removes a queued task by ID (unless it’s in progress)."""
    try:
        processing_task = get_list_from_queue(processing)
        if processing_task:
            assert len(processing_task) == 1
            current_task = processing_task[0]
        else:
            current_task = None
    except AssertionError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Multiple processing tasks found",
        )
    # can’t remove the one in progress
    if current_task and current_task.get("id") == task_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": "Task is currently being processed"},
        )

    # drain the queue into a temp list
    all_tasks = []
    while not queue.empty():
        all_tasks.append(queue.get())

    # filter out the one to delete
    new_tasks = [t for t in all_tasks if t.get("id") != task_id]

    if len(new_tasks) == len(all_tasks):
        # nothing was removed
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": "error", "message": f"Task {task_id} not found"},
        )

    # re-enqueue the survivors
    for t in new_tasks:
        queue.put(t)

    return {"status": "success", "message": f"Task {task_id} removed from the queue"}


@api_router.get("/ttl_compare", response_model=FileList)
async def get_ttl_compare_list(request: Request):
    """Get list of comparison ttl files"""
    file_list = list_files_in_dir(folder="compare", request=request)
    return {"file_list": file_list}


@api_router.get("/ttl_compare/{ttl_filename}")
async def get_ttl_compare(ttl_filename: str, request: Request):
    """Get network json from compare file"""
    ttl_filepath = get_file_path(ttl_filename, request, folder="compare")
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    g = Graph()
    g.parse(ttl_filepath, format="ttl")
    nx_graph, node_data, edge_data = build_networkx_graph(g)

    net = Network()
    pass_networkx_to_pyvis(nx_graph, net, node_data, edge_data)
    net_data = {"nodes": net.nodes, "edges": net.edges}
    return net_data


@api_router.delete("/ttl_compare/{ttl_filename}", response_model=MessageResponse)
async def delete_ttl_compare(ttl_filename: str, request: Request):
    """Delete ttl compare file"""
    ttl_filepath = get_file_path(ttl_filename, request, folder="compare")
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if os.path.exists(ttl_filepath):
        os.remove(ttl_filepath)
        return {"message": f"File {ttl_filename} deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )


@api_router.get("/network_config")
async def get_network_config_list(request: Request):
    """Gets network config list"""
    data = []
    agent_data_path = get_agent_data_path(request)
    network_config_roots = os.path.join(agent_data_path, "network_config")
    if os.path.exists(network_config_roots):
        for filename in os.listdir(network_config_roots):
            if filename.endswith(".json"):
                data.append(filename)
    return {"data": data}


@api_router.post(
    "/network_config",
    status_code=status.HTTP_201_CREATED,
    response_model=Union[FileUploadResponse, ErrorResponse],
)
async def upload_network_config(request: Request, file: UploadFile = File(...)):
    """Upload network config json file"""
    ALLOWED_EXTENSIONS = {"json"}

    def allowed_file(filename):
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    agent_data_path = get_agent_data_path(request)
    network_config_path = os.path.join(agent_data_path, "network_config")

    if not file:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "No file part in the request"},
        )

    if file.filename == "" or not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "No selected file"},
        )

    if file and allowed_file(file.filename):
        file_path = os.path.join(network_config_path, file.filename)

        # Save the file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        return {
            "message": f"File {file.filename} uploaded successfully",
            "file_path": file_path,
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "File type not allowed"},
        )


@api_router.get("/network_config/{network_config_filename}")
async def download_network_config(network_config_filename: str, request: Request):
    """Download network config json file"""
    network_config_filepath = get_file_path(
        network_config_filename, request, "network_config"
    )
    if not network_config_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    try:
        return FileResponse(network_config_filepath, filename=network_config_filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@api_router.delete(
    "/network_config/{network_config_filename}", response_model=MessageResponse
)
async def delete_network_config(network_config_filename: str, request: Request):
    """Delete network config json file"""
    network_config_filepath = get_file_path(
        network_config_filename, request, folder="network_config"
    )
    if not network_config_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if os.path.exists(network_config_filepath):
        os.remove(network_config_filepath)
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )


@api_router.get("/csv_export/{ttl_filename}")
async def export_csv(ttl_filename: str, request: Request):
    """Export ttl file to csv"""
    ttl_filepath = get_file_path(ttl_filename, request)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    g = Graph()
    g.parse(ttl_filepath, format="ttl")
    nx_graph, node_data, edge_data = build_networkx_graph(g)

    for u, v, attr in nx_graph.edges(data=True):
        edge_label = attr.get("triples", [])[0][1] if "triples" in attr else None
        if edge_label:
            if "device-on-network" in edge_label:
                if "router" in str(u):
                    node_data[str(u)]["subnet"] = "/".join(str(v).split("/")[-2:])
                else:
                    node_data[str(u)]["network-id"] = [str(v).split("/")[-1]]
            if "router-to-network" in edge_label:
                if "network-id" in node_data[str(u)]:
                    node_data[str(u)]["network-id"].append(str(v).split("/")[-1])
                else:
                    node_data[str(u)]["network-id"] = [str(v).split("/")[-1]]

    output_str = StringIO()
    writer = csv.writer(output_str)

    # Write header
    writer.writerow(
        ["Device Id", "Device Address", "Network Id", "Subnet", "Vendor Id", "Type"]
    )

    # Write Rows
    for node in nx_graph.nodes:
        device_type = node_data.get(str(node), {}).get("type", "")
        if device_type in ["Device", "Router"]:
            device_id = str(node).split("/")[-1]
            device_address = node_data.get(str(node), {}).get("device-address", "")
            network_id = node_data.get(str(node), {}).get("network-id", [])
            subnets = node_data.get(str(node), {}).get("subnet", "")
            vendor_id = node_data.get(str(node), {}).get("vendor-id", "").split("/")[-1]

            writer.writerow(
                [device_id, device_address, network_id, subnets, vendor_id, device_type]
            )

    # Return as a downloadable CSV file
    response = JSONResponse(content=output_str.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={ttl_filename}.csv"
    response.headers["Content-Type"] = "text/csv"

    return response


def device_config_read_key(agent_data_path: str, key: str) -> Any:
    """
    Read a key from the device configuration file.

    Args:
        agent_data_path (str): Path to the agent data directory
        key (str): The configuration key to read

    Returns:
        Any: The value associated with the key, or None if the key doesn't exist
              or there was an error reading the configuration file
    """
    try:
        config_path = os.path.join(agent_data_path, DEVICE_STATE_CONFIG)
        if not os.path.exists(config_path):
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            if key in config:
                return config[key]
            else:
                return []
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def device_config_write_key(agent_data_path: str, key: str, value: Any) -> bool:
    """
    Write a single key/value into the device config JSON file.

    This function writes or updates a key in the device configuration file,
    creating the file if it doesn't exist. It uses a safe write pattern with
    a temporary file to prevent corruption if the process is interrupted.

    Args:
        agent_data_path (str): Path to the agent data directory
        key (str): The configuration key to write
        value (Any): The value to associate with the key

    Returns:
        bool: True on success, False on any error
    """
    config_path = os.path.join(agent_data_path, DEVICE_STATE_CONFIG)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if not isinstance(config, dict):
                    config = {}
        else:
            config = {}

        config[key] = value
        tmp_path = config_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, config_path)

        return True

    except (OSError, json.JSONDecodeError):
        return False


@api_router.get("/bbmds", response_model=IPAddressList)
async def get_bbmd_list(agent_data_path=Depends(get_agent_data_path)):
    """Gets the list of BBMD IP Addresses stored in the config"""
    list_of_bbmd_ips: list = device_config_read_key(agent_data_path, "bbmd_devices")
    return {"ip_address_list": list_of_bbmd_ips}


@api_router.post("/bbmds", response_model=Dict[str, List[str]])
async def add_bbmd(ip_data: IPAddress, agent_data_path=Depends(get_agent_data_path)):
    """Adds IP address to the list of BBMD IP Addresses stored in the config"""
    list_of_bbmd_ips: list = device_config_read_key(agent_data_path, "bbmd_devices")
    ip = ip_data.ip_address
    if ip and ip not in list_of_bbmd_ips:
        list_of_bbmd_ips.append(ip)
        device_config_write_key(agent_data_path, "bbmd_devices", list_of_bbmd_ips)
    return {"list_of_bbmd_ips": list_of_bbmd_ips}


@api_router.delete("/bbmds", response_model=Dict[str, List[str]])
async def delete_bbmd(ip_data: IPAddress, agent_data_path=Depends(get_agent_data_path)):
    """Removes IP address from the list of BBMD IP Addresses stored in the config"""
    list_of_bbmd_ips: list = device_config_read_key(agent_data_path, "bbmd_devices")
    ip = ip_data.ip_address
    if ip and ip in list_of_bbmd_ips:
        list_of_bbmd_ips.remove(ip)
        device_config_write_key(agent_data_path, "bbmd_devices", list_of_bbmd_ips)
    return {"list_of_bbmd_ips": list_of_bbmd_ips}


@api_router.get("/subnets", response_model=IPAddressList)
async def get_subnet_list(agent_data_path=Depends(get_agent_data_path)):
    """Gets the list of Subnets CIDR Addresses stored in the config"""
    list_of_subnets_ips: list = device_config_read_key(agent_data_path, "subnets")
    return {"ip_address_list": list_of_subnets_ips}


@api_router.post("/subnets", response_model=Dict[str, List[str]])
async def add_subnet(ip_data: IPAddress, agent_data_path=Depends(get_agent_data_path)):
    """Adds IP address to the list of Subnets CIDR Addresses stored in the config"""
    list_of_subnets_ips: list = device_config_read_key(agent_data_path, "subnets")
    ip = ip_data.ip_address
    if ip and ip not in list_of_subnets_ips:
        list_of_subnets_ips.append(ip)
        device_config_write_key(agent_data_path, "subnets", list_of_subnets_ips)
    return {"list_of_subnets_ips": list_of_subnets_ips}


@api_router.delete("/subnets", response_model=Dict[str, List[str]])
async def delete_subnet(
    ip_data: IPAddress, agent_data_path=Depends(get_agent_data_path)
):
    """Removes IP address from the list of subnets IP Addresses stored in the config"""
    list_of_subnets_ips: list = device_config_read_key(agent_data_path, "subnets")
    ip = ip_data.ip_address
    if ip and ip in list_of_subnets_ips:
        list_of_subnets_ips.remove(ip)
        device_config_write_key(agent_data_path, "subnets", list_of_subnets_ips)
    return {"list_of_subnets_ips": list_of_subnets_ips}
