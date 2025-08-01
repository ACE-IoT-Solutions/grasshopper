"""API endpoints for Grasshopper using FastAPI"""

import csv
import json
import os
import uuid
from concurrent.futures import ProcessPoolExecutor
from http import HTTPStatus
from io import BytesIO, StringIO
from multiprocessing import Queue
from typing import Any, Dict, List, Optional, Union, cast

import gevent
from bacpypes3.rdf.core import BACnetNS
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
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
    return str(request.app.extra.get("agent_data_path", ""))


def get_task_queue(request: Request) -> Any:
    """Get agent task queue from app state.

    Args:
        request (Request): The FastAPI request object

    Returns:
        Queue[Any]: The multiprocessing queue for tasks
    """
    return request.app.state.task_queue


def get_processing_task(request: Request) -> Any:
    """Get processing task queue from app state.

    Args:
        request (Request): The FastAPI request object

    Returns:
        Queue[Any]: The multiprocessing queue for tasks currently being processed
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

    remove_nodes: List[Any] = []
    rdf_edges: Dict[Any, Any] = {}
    device_address_edges: List[Any] = []
    rdf_diff_list: List[Any] = []
    node_data: Dict[str, Dict[str, Any]] = {}
    edge_data: Dict[str, Dict[str, Any]] = {}
    for u, v, attr in nx_graph.edges(data=True):
        edge_label = attr.get("triples", [])[0][1] if "triples" in attr else None
        if edge_label:
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
    """
    Health check endpoint that returns a simple greeting message.

    This endpoint is primarily used for testing API connectivity and ensuring
    the service is running properly.

    **HTTP Method:** GET
    **URL Path:** `/operations/hello`

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: JSON object with a greeting message
      - Content-Type: `application/json`
      - Body: `{"message": "Hello, world!"}`

    **Example Request:**
    ```
    GET /operations/hello
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "message": "Hello, world!"
    }
    ```
    """
    return {"message": "Hello, world!"}


@api_router.get("/ttl")
async def get_ttl_list(request: Request):
    """
    Retrieve a list of all available TTL (Turtle) files in the agent data directory.

    This endpoint scans the TTL directory and returns the names of all `.ttl` files
    available for processing, comparison, and visualization.

    **HTTP Method:** GET
    **URL Path:** `/operations/ttl`

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: JSON object containing an array of TTL filenames
      - Content-Type: `application/json`
      - Body: `{"data": ["file1.ttl", "file2.ttl", ...]}`

    **Example Request:**
    ```
    GET /operations/ttl
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "data": [
            "file1.ttl",
            "file2.ttl",
            "file3.ttl"
        ]
    }
    ```
    """
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
    """
    Upload a TTL (Turtle) file to the agent data directory for processing.

    This endpoint accepts TTL files via multipart/form-data upload and stores them
    in the agent's TTL directory for subsequent processing, comparison, and visualization.
    Only files with `.ttl` extension are accepted.

    **HTTP Method:** POST
    **URL Path:** `/operations/ttl`

    **Request Headers:**
    - `Content-Type: multipart/form-data` (required for file upload)
    - `Accept: application/json` (default) - Returns JSON response

    **Request Body:**
    - Form data with a file field containing the TTL file
    - File must have `.ttl` extension
    - Maximum file size depends on server configuration

    **Response:**
    - **201 Created**: File uploaded successfully
      - Content-Type: `application/json`
      - Body: `{"message": "File {filename} uploaded successfully", "file_path": "/path/to/file"}`
    - **400 Bad Request**: Invalid file or missing file
      - Content-Type: `application/json`
      - Body: `{"error": "Error description"}`

    **Example Request:**
    ```
    POST /operations/ttl
    Content-Type: multipart/form-data
    Accept: application/json

    [File data in form field 'file']
    ```

    **Example Response (Success):**
    ```json
    {
        "message": "File 2025-01-01T01-01-00.ttl uploaded successfully",
        "file_path": "/agent/data/ttl/network_scan.ttl"
    }
    ```

    **Example Response (Error):**
    ```json
    {
        "error": "File type not allowed"
    }
    ```
    """
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
    """
    Download a specific TTL (Turtle) file from the agent data directory.

    This endpoint allows retrieval of TTL files in their raw format for external
    processing, backup, or sharing. The file is returned as a binary download
    with appropriate headers for file download.

    **HTTP Method:** GET
    **URL Path:** `/operations/ttl_file/{ttl_filename}`

    **Path Parameters:**
    - `ttl_filename` (string): Name of the TTL file to download (including .ttl extension)

    **Request Headers:**
    - `Accept: */*` or `Accept: application/octet-stream` (recommended for file download)
    - `Accept: text/turtle` - Returns raw TTL content with proper MIME type

    **Response:**
    - **200 OK**: File download successful
      - Content-Type: `application/octet-stream` (for download) or `text/turtle` (for raw content)
      - Content-Disposition: `attachment; filename="{ttl_filename}"`
      - Body: Raw TTL file content
    - **404 Not Found**: File does not exist
      - Content-Type: `application/json`
      - Body: `{"detail": "File not found"}`
    - **500 Internal Server Error**: Server error during file access

    **Example Request:**
    ```
    GET /operations/ttl_file/network_scan.ttl
    Accept: application/octet-stream
    ```

    **Example Response Headers:**
    ```
    HTTP/1.1 200 OK
    Content-Type: application/octet-stream
    Content-Disposition: attachment; filename="network_scan.ttl"
    Content-Length: 12345
    ```
    """
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
    """
    Delete a specific TTL (Turtle) file from the agent data directory.

    This endpoint permanently removes a TTL file from the server's storage.
    Use with caution as this operation cannot be undone.

    **HTTP Method:** DELETE
    **URL Path:** `/operations/ttl_file/{ttl_filename}`

    **Path Parameters:**
    - `ttl_filename` (string): Name of the TTL file to delete (including .ttl extension)

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: File deleted successfully
      - Content-Type: `application/json`
      - Body: `{"message": "File deleted successfully"}`
    - **404 Not Found**: File does not exist
      - Content-Type: `application/json`
      - Body: `{"detail": "File not found"}`

    **Example Request:**
    ```
    DELETE /operations/ttl_file/network_scan.ttl
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "message": "File deleted successfully"
    }
    ```
    """
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
    """
    Convert a TTL file to network visualization data (JSON format).

    This endpoint processes a TTL file containing BACnet network topology data
    and converts it into a JSON structure suitable for network visualization.
    The output includes nodes (devices, routers) and edges (connections) with
    their associated metadata.

    **HTTP Method:** GET
    **URL Path:** `/operations/ttl_network/{ttl_filename}`

    **Path Parameters:**
    - `ttl_filename` (string): Name of the TTL file to process (including .ttl extension)

    **Request Headers:**
    - `Accept: application/json` (default) - Returns network data as JSON

    **Response:**
    - **200 OK**: Network data successfully generated
      - Content-Type: `application/json`
      - Body: JSON object with `nodes` and `edges` arrays containing network topology
    - **404 Not Found**: TTL file does not exist
      - Content-Type: `application/json`
      - Body: `{"detail": "File not found"}`

    **Response Schema:**
    ```json
    {
        "nodes": [
            {
                "id": "device_id",
                "label": "Device Name",
                "data": {
                    "type": "Device|Router",
                    "device-address": "ip_address",
                    "vendor-id": "vendor_identifier",
                    // ... other device properties
                }
            }
        ],
        "edges": [
            {
                "from": "source_node_id",
                "to": "target_node_id",
                "label": "connection_type",
                "data": {
                    // ... edge metadata
                }
            }
        ]
    }
    ```

    **Example Request:**
    ```
    GET /operations/ttl_network/network_scan.ttl
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "nodes": [
            {
                "id": "Device_123",
                "label": "Device_123",
                "data": {
                    "type": "Device",
                    "device-address": "192.168.1.100",
                    "vendor-id": "8"
                }
            }
        ],
        "edges": [
            {
                "from": "Device_123",
                "to": "Network_1",
                "label": "device-on-network"
            }
        ]
    }
    ```
    """
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
    """
    Queue a TTL file comparison task for asynchronous processing.

    This endpoint accepts two TTL filenames and queues them for comparison.
    The comparison is performed asynchronously in the background, generating
    a new TTL file that contains the differences between the two input files.

    **HTTP Method:** POST
    **URL Path:** `/operations/ttl_compare_queue`

    **Request Headers:**
    - `Content-Type: application/json` (required)
    - `Accept: application/json` (default) - Returns JSON response

    **Request Body:**
    ```json
    {
        "ttl_1": "first_file.ttl",
        "ttl_2": "second_file.ttl"
    }
    ```

    **Response:**
    - **202 Accepted**: Task queued successfully
      - Content-Type: `application/json`
      - Body: `{"message": "File accepted", "task": {...}}`
    - **400 Bad Request**: Task already exists or invalid request
      - Content-Type: `application/json`
      - Body: `{"detail": "Task already queued or in progress"}`
    - **404 Not Found**: One or both TTL files not found
      - Content-Type: `application/json`
      - Body: `{"detail": "One or both TTL files not found"}`

    **Example Request:**
    ```
    POST /operations/ttl_compare_queue
    Content-Type: application/json
    Accept: application/json

    {
        "ttl_1": "network_scan_v1.ttl",
        "ttl_2": "network_scan_v2.ttl"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "File accepted",
        "task": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "ttl_1": "network_scan_v1.ttl",
            "ttl_2": "network_scan_v2.ttl",
            "agent_data_path": "/agent/data"
        }
    }
    ```
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
    """
    Get the current status of the TTL comparison queue.

    This endpoint returns information about the current comparison task being
    processed and all queued tasks waiting for processing.

    **HTTP Method:** GET
    **URL Path:** `/operations/ttl_compare_queue`

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: Queue status retrieved successfully
      - Content-Type: `application/json`
      - Body: Object containing current processing task and queued tasks

    **Response Schema:**
    ```json
    {
        "processing_task": {
            "id": "task_uuid",
            "ttl_1": "file1.ttl",
            "ttl_2": "file2.ttl",
            "agent_data_path": "/path/to/data"
        } | null,
        "queue": [
            {
                "id": "task_uuid",
                "ttl_1": "file3.ttl",
                "ttl_2": "file4.ttl",
                "agent_data_path": "/path/to/data"
            }
        ]
    }
    ```

    **Example Request:**
    ```
    GET /operations/ttl_compare_queue
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "processing_task": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "ttl_1": "network_v1.ttl",
            "ttl_2": "network_v2.ttl",
            "agent_data_path": "/agent/data"
        },
        "queue": [
            {
                "id": "987fcdeb-51a2-43d7-b123-987654321000",
                "ttl_1": "scan_a.ttl",
                "ttl_2": "scan_b.ttl",
                "agent_data_path": "/agent/data"
            }
        ]
    }
    ```
    """
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
    """
    Remove a queued TTL comparison task by its ID.

    This endpoint allows cancellation of a queued comparison task. Tasks that are
    currently being processed cannot be cancelled and will return an error.

    **HTTP Method:** DELETE
    **URL Path:** `/operations/ttl_compare_queue_tasks/{task_id}`

    **Path Parameters:**
    - `task_id` (string): UUID of the task to remove from the queue

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: Task removed successfully
      - Content-Type: `application/json`
      - Body: `{"status": "success", "message": "Task {task_id} removed from the queue"}`
    - **400 Bad Request**: Task is currently being processed
      - Content-Type: `application/json`
      - Body: `{"status": "error", "message": "Task is currently being processed"}`
    - **404 Not Found**: Task ID not found in queue
      - Content-Type: `application/json`
      - Body: `{"status": "error", "message": "Task {task_id} not found"}`
    - **500 Internal Server Error**: Multiple processing tasks found (unexpected state)

    **Example Request:**
    ```
    DELETE /operations/ttl_compare_queue_tasks/123e4567-e89b-12d3-a456-426614174000
    Accept: application/json
    ```

    **Example Response (Success):**
    ```json
    {
        "status": "success",
        "message": "Task 123e4567-e89b-12d3-a456-426614174000 removed from the queue"
    }
    ```

    **Example Response (Error - Task in Progress):**
    ```json
    {
        "status": "error",
        "message": "Task is currently being processed"
    }
    ```
    """
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
    """
    Get a list of available TTL comparison result files.

    This endpoint returns the names of all comparison files that have been generated
    by the TTL comparison process. These files contain the differences between
    compared TTL files and can be used for visualization or further analysis.

    **HTTP Method:** GET
    **URL Path:** `/operations/ttl_compare`

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: List of comparison files retrieved successfully
      - Content-Type: `application/json`
      - Body: `{"file_list": ["comparison1.ttl", "comparison2.ttl", ...]}`

    **Example Request:**
    ```
    GET /operations/ttl_compare
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "file_list": [
            "network_v1_vs_network_v2.ttl",
            "scan_a_vs_scan_b.ttl",
            "baseline_vs_current.ttl"
        ]
    }
    ```
    """
    file_list = list_files_in_dir(folder="compare", request=request)
    return {"file_list": file_list}


@api_router.get("/ttl_compare/{ttl_filename}")
async def get_ttl_compare(ttl_filename: str, request: Request):
    """
    Get network visualization data from a TTL comparison result file.

    This endpoint processes a comparison TTL file and returns network visualization
    data showing the differences between two compared TTL files. The response includes
    nodes and edges with difference markers indicating which elements came from
    which source file.

    **HTTP Method:** GET
    **URL Path:** `/operations/ttl_compare/{ttl_filename}`

    **Path Parameters:**
    - `ttl_filename` (string): Name of the comparison TTL file (including .ttl extension)

    **Request Headers:**
    - `Accept: application/json` (default) - Returns network data as JSON

    **Response:**
    - **200 OK**: Network comparison data successfully generated
      - Content-Type: `application/json`
      - Body: JSON object with `nodes` and `edges` arrays showing network differences
    - **404 Not Found**: Comparison file does not exist
      - Content-Type: `application/json`
      - Body: `{"detail": "File not found"}`

    **Response Schema:**
    Similar to `/ttl_network/{ttl_filename}` but includes additional metadata
    indicating which source file each element came from:
    ```json
    {
        "nodes": [
            {
                "id": "device_id",
                "label": "Device Name",
                "data": {
                    "type": "Device|Router",
                    "device-address": "ip_address",
                    "rdf_diff_source": "source_file.ttl",
                    // ... other properties
                }
            }
        ],
        "edges": [
            {
                "from": "source_node_id",
                "to": "target_node_id",
                "label": "connection_type",
                "data": {
                    "rdf_diff_source": "source_file.ttl",
                    // ... other edge metadata
                }
            }
        ]
    }
    ```

    **Example Request:**
    ```
    GET /operations/ttl_compare/network_v1_vs_network_v2.ttl
    Accept: application/json
    ```
    """
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
    """
    Delete a TTL comparison result file.

    This endpoint permanently removes a comparison TTL file from the server's storage.
    Use with caution as this operation cannot be undone.

    **HTTP Method:** DELETE
    **URL Path:** `/operations/ttl_compare/{ttl_filename}`

    **Path Parameters:**
    - `ttl_filename` (string): Name of the comparison TTL file to delete (including .ttl extension)

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: Comparison file deleted successfully
      - Content-Type: `application/json`
      - Body: `{"message": "File {ttl_filename} deleted successfully"}`
    - **404 Not Found**: Comparison file does not exist
      - Content-Type: `application/json`
      - Body: `{"detail": "File not found"}`

    **Example Request:**
    ```
    DELETE /operations/ttl_compare/network_v1_vs_network_v2.ttl
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "message": "File network_v1_vs_network_v2.ttl deleted successfully"
    }
    ```
    """
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
    """
    Get a list of available network configuration files.

    This endpoint returns the names of all JSON network configuration files
    stored in the agent data directory. These files contain network settings
    and parameters used by the BACnet scanning and discovery processes.

    **HTTP Method:** GET
    **URL Path:** `/operations/network_config`

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: List of network configuration files retrieved successfully
      - Content-Type: `application/json`
      - Body: `{"data": ["config1.json", "config2.json", ...]}`

    **Example Request:**
    ```
    GET /operations/network_config
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "data": [
            "production_network.json",
            "test_environment.json",
            "backup_config.json"
        ]
    }
    ```
    """
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
    """
    Upload a network configuration JSON file to the agent data directory.

    This endpoint accepts JSON configuration files via multipart/form-data upload
    and stores them in the agent's network_config directory. These files can contain
    network settings, IP ranges, device parameters, and other configuration data
    used by the BACnet scanning processes.

    **HTTP Method:** POST
    **URL Path:** `/operations/network_config`

    **Request Headers:**
    - `Content-Type: multipart/form-data` (required for file upload)
    - `Accept: application/json` (default) - Returns JSON response

    **Request Body:**
    - Form data with a file field containing the JSON configuration file
    - File must have `.json` extension
    - Content should be valid JSON format

    **Response:**
    - **201 Created**: Configuration file uploaded successfully
      - Content-Type: `application/json`
      - Body: `{"message": "File {filename} uploaded successfully", "file_path": "/path/to/file"}`
    - **400 Bad Request**: Invalid file, missing file, or wrong file type
      - Content-Type: `application/json`
      - Body: `{"error": "Error description"}`

    **Example Request:**
    ```
    POST /operations/network_config
    Content-Type: multipart/form-data
    Accept: application/json

    [JSON file data in form field 'file']
    ```

    **Example Response (Success):**
    ```json
    {
        "message": "File production_config.json uploaded successfully",
        "file_path": "/agent/data/network_config/production_config.json"
    }
    ```

    **Example Response (Error):**
    ```json
    {
        "error": "File type not allowed"
    }
    ```
    """
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
    """
    Download a specific network configuration JSON file.

    This endpoint allows retrieval of network configuration files in their raw JSON
    format for external processing, backup, editing, or sharing. The file is returned
    as a binary download with appropriate headers.

    **HTTP Method:** GET
    **URL Path:** `/operations/network_config/{network_config_filename}`

    **Path Parameters:**
    - `network_config_filename` (string): Name of the configuration file (including .json extension)

    **Request Headers:**
    - `Accept: */*` or `Accept: application/octet-stream` (recommended for file download)
    - `Accept: application/json` - Returns raw JSON content with proper MIME type

    **Response:**
    - **200 OK**: File download successful
      - Content-Type: `application/octet-stream` (for download) or `application/json` (for raw content)
      - Content-Disposition: `attachment; filename="{network_config_filename}"`
      - Body: Raw JSON file content
    - **404 Not Found**: Configuration file does not exist
      - Content-Type: `application/json`
      - Body: `{"detail": "File not found"}`
    - **500 Internal Server Error**: Server error during file access

    **Example Request:**
    ```
    GET /operations/network_config/production_config.json
    Accept: application/octet-stream
    ```

    **Example Response Headers:**
    ```
    HTTP/1.1 200 OK
    Content-Type: application/octet-stream
    Content-Disposition: attachment; filename="production_config.json"
    Content-Length: 1234
    ```
    """
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
    """
    Delete a specific network configuration JSON file.

    This endpoint permanently removes a network configuration file from the server's
    storage. Use with caution as this operation cannot be undone.

    **HTTP Method:** DELETE
    **URL Path:** `/operations/network_config/{network_config_filename}`

    **Path Parameters:**
    - `network_config_filename` (string): Name of the configuration file to delete (including .json extension)

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: Configuration file deleted successfully
      - Content-Type: `application/json`
      - Body: `{"message": "File deleted successfully"}`
    - **404 Not Found**: Configuration file does not exist
      - Content-Type: `application/json`
      - Body: `{"detail": "File not found"}`

    **Example Request:**
    ```
    DELETE /operations/network_config/old_config.json
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "message": "File deleted successfully"
    }
    ```
    """
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
    """
    Export TTL file data to CSV format for external analysis.

    This endpoint processes a TTL file containing BACnet network topology data
    and converts it into a CSV format suitable for spreadsheet applications,
    data analysis tools, or reporting systems. The CSV includes device information
    such as device IDs, addresses, network IDs, subnets, vendor IDs, and device types.

    **HTTP Method:** GET
    **URL Path:** `/operations/csv_export/{ttl_filename}`

    **Path Parameters:**
    - `ttl_filename` (string): Name of the TTL file to export (including .ttl extension)

    **Request Headers:**
    - `Accept: text/csv` (recommended) - Returns CSV content
    - `Accept: application/octet-stream` - Returns CSV as downloadable file
    - `Accept: */*` (default) - Returns CSV as downloadable file

    **Response:**
    - **200 OK**: CSV export successful
      - Content-Type: `text/csv`
      - Content-Disposition: `attachment; filename="{ttl_filename}.csv"`
      - Body: CSV data with headers: Device Id, Device Address, Network Id, Subnet, Vendor Id, Type
    - **404 Not Found**: TTL file does not exist
      - Content-Type: `application/json`
      - Body: `{"detail": "File not found"}`

    **CSV Format:**
    ```csv
    Device Id,Device Address,Network Id,Subnet,Vendor Id,Type
    12345,192.168.1.100,"1,2",192.168.1.0/24,8,Device
    67890,192.168.1.1,1,192.168.1.0/24,8,Router
    ```

    **Example Request:**
    ```
    GET /operations/csv_export/network_scan.ttl
    Accept: text/csv
    ```

    **Example Response Headers:**
    ```
    HTTP/1.1 200 OK
    Content-Type: text/csv
    Content-Disposition: attachment; filename="network_scan.ttl.csv"
    ```
    """
    ttl_filepath = get_file_path(ttl_filename, request)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    g = Graph()
    g.parse(ttl_filepath, format="ttl")
    nx_graph, node_data, edge_data = build_networkx_graph(g)

    BACnetEdgeType_subnets = [
        BACnetEdgeType.BACNET_ROUTER_ON_SUBNET.value,
        BACnetEdgeType.DEVICE_ON_SUBNET.value,
        BACnetEdgeType.BBMD_BROADCAST_DOMAIN.value,
    ]
    BACnetEdgeType_networks = [
        BACnetEdgeType.DEVICE_ON_NETWORK.value,
    ]

    for u, v, attr in nx_graph.edges(data=True):
        edge_label = attr.get("triples", [])[0][1] if "triples" in attr else None
        if edge_label:
            if any(subnet in edge_label for subnet in BACnetEdgeType_subnets):
                node_data[str(u)]["subnet"] = "/".join(str(v).split("/")[-2:])
            elif any(network in edge_label for network in BACnetEdgeType_networks):
                if "network-id" in node_data[str(u)]:
                    node_data[str(u)]["network-id"].append(str(v).split("/")[-1])
                else:
                    node_data[str(u)]["network-id"] = [str(v).split("/")[-1]]

    output_str = StringIO(newline="")
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
            network_id_list = node_data.get(str(node), {}).get("network-id", [])
            network_id = ",".join(network_id_list) if network_id_list else ""
            subnets = node_data.get(str(node), {}).get("subnet", "")
            vendor_id = node_data.get(str(node), {}).get("vendor-id", "").split("/")[-1]

            writer.writerow(
                [device_id, device_address, network_id, subnets, vendor_id, device_type]
            )

    # Return as a downloadable CSV file
    response = StreamingResponse(content=output_str.getvalue())
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
    """
    Get the list of configured BBMD (BACnet Broadcast Management Device) IP addresses.

    This endpoint retrieves the list of BBMD IP addresses that are stored in the
    device configuration. BBMDs are used in BACnet networks to manage broadcast
    distribution across network boundaries and enable communication between
    devices on different subnets.

    **HTTP Method:** GET
    **URL Path:** `/operations/bbmds`

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: BBMD list retrieved successfully
      - Content-Type: `application/json`
      - Body: `{"ip_address_list": ["192.168.1.1", "10.0.0.1", ...]}`

    **Example Request:**
    ```
    GET /operations/bbmds
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "ip_address_list": [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1"
        ]
    }
    ```
    """
    list_of_bbmd_ips: list = device_config_read_key(agent_data_path, "bbmd_devices")
    return {"ip_address_list": list_of_bbmd_ips}


@api_router.post("/bbmds", response_model=Dict[str, List[str]])
async def add_bbmd(ip_data: IPAddress, agent_data_path=Depends(get_agent_data_path)):
    """
    Add a BBMD (BACnet Broadcast Management Device) IP address to the configuration.

    This endpoint adds a new BBMD IP address to the stored configuration list.
    The IP address will be used during BACnet network scanning and communication
    to register with BBMDs and enable broadcast distribution across subnets.
    Duplicate IP addresses are automatically ignored.

    **HTTP Method:** POST
    **URL Path:** `/operations/bbmds`

    **Request Headers:**
    - `Content-Type: application/json` (required)
    - `Accept: application/json` (default) - Returns JSON response

    **Request Body:**
    ```json
    {
        "ip_address": "192.168.1.100"
    }
    ```

    **Response:**
    - **200 OK**: BBMD IP address added successfully (or already exists)
      - Content-Type: `application/json`
      - Body: `{"list_of_bbmd_ips": ["192.168.1.1", "192.168.1.100", ...]}`

    **Example Request:**
    ```
    POST /operations/bbmds
    Content-Type: application/json
    Accept: application/json

    {
        "ip_address": "192.168.1.100"
    }
    ```

    **Example Response:**
    ```json
    {
        "list_of_bbmd_ips": [
            "192.168.1.1",
            "10.0.0.1",
            "192.168.1.100"
        ]
    }
    ```
    """
    list_of_bbmd_ips: list = device_config_read_key(agent_data_path, "bbmd_devices")
    ip = ip_data.ip_address
    if ip and ip not in list_of_bbmd_ips:
        list_of_bbmd_ips.append(ip)
        device_config_write_key(agent_data_path, "bbmd_devices", list_of_bbmd_ips)
    return {"list_of_bbmd_ips": list_of_bbmd_ips}


@api_router.delete("/bbmds", response_model=Dict[str, List[str]])
async def delete_bbmd(ip_data: IPAddress, agent_data_path=Depends(get_agent_data_path)):
    """
    Remove a BBMD (BACnet Broadcast Management Device) IP address from the configuration.

    This endpoint removes a BBMD IP address from the stored configuration list.
    The specified IP address will no longer be used during BACnet network scanning
    and communication processes. If the IP address is not in the list, no changes
    are made.

    **HTTP Method:** DELETE
    **URL Path:** `/operations/bbmds`

    **Request Headers:**
    - `Content-Type: application/json` (required)
    - `Accept: application/json` (default) - Returns JSON response

    **Request Body:**
    ```json
    {
        "ip_address": "192.168.1.100"
    }
    ```

    **Response:**
    - **200 OK**: BBMD IP address removed successfully (or was not in list)
      - Content-Type: `application/json`
      - Body: `{"list_of_bbmd_ips": ["192.168.1.1", ...]}`

    **Example Request:**
    ```
    DELETE /operations/bbmds
    Content-Type: application/json
    Accept: application/json

    {
        "ip_address": "192.168.1.100"
    }
    ```

    **Example Response:**
    ```json
    {
        "list_of_bbmd_ips": [
            "192.168.1.1",
            "10.0.0.1"
        ]
    }
    ```
    """
    list_of_bbmd_ips: list = device_config_read_key(agent_data_path, "bbmd_devices")
    ip = ip_data.ip_address
    if ip and ip in list_of_bbmd_ips:
        list_of_bbmd_ips.remove(ip)
        device_config_write_key(agent_data_path, "bbmd_devices", list_of_bbmd_ips)
    return {"list_of_bbmd_ips": list_of_bbmd_ips}


@api_router.get("/subnets", response_model=IPAddressList)
async def get_subnet_list(agent_data_path=Depends(get_agent_data_path)):
    """
    Get the list of configured subnet CIDR addresses for BACnet scanning.

    This endpoint retrieves the list of subnet CIDR addresses that are stored in
    the device configuration. These subnets define the IP address ranges that
    will be scanned during BACnet device discovery operations.

    **HTTP Method:** GET
    **URL Path:** `/operations/subnets`

    **Request Headers:**
    - `Accept: application/json` (default) - Returns JSON response

    **Response:**
    - **200 OK**: Subnet list retrieved successfully
      - Content-Type: `application/json`
      - Body: `{"ip_address_list": ["192.168.1.0/24", "10.0.0.0/16", ...]}`

    **Example Request:**
    ```
    GET /operations/subnets
    Accept: application/json
    ```

    **Example Response:**
    ```json
    {
        "ip_address_list": [
            "192.168.1.0/24",
            "10.0.0.0/16",
            "172.16.0.0/20"
        ]
    }
    ```
    """
    list_of_subnets_ips: list = device_config_read_key(agent_data_path, "subnets")
    return {"ip_address_list": list_of_subnets_ips}


@api_router.post("/subnets", response_model=Dict[str, List[str]])
async def add_subnet(ip_data: IPAddress, agent_data_path=Depends(get_agent_data_path)):
    """
    Add a subnet CIDR address to the scanning configuration.

    This endpoint adds a new subnet CIDR address to the stored configuration list.
    The subnet will be included in future BACnet device discovery scans to identify
    and catalog devices within the specified IP address range. Duplicate subnet
    addresses are automatically ignored.

    **HTTP Method:** POST
    **URL Path:** `/operations/subnets`

    **Request Headers:**
    - `Content-Type: application/json` (required)
    - `Accept: application/json` (default) - Returns JSON response

    **Request Body:**
    ```json
    {
        "ip_address": "192.168.2.0/24"
    }
    ```

    **Response:**
    - **200 OK**: Subnet CIDR address added successfully (or already exists)
      - Content-Type: `application/json`
      - Body: `{"list_of_subnets_ips": ["192.168.1.0/24", "192.168.2.0/24", ...]}`

    **Example Request:**
    ```
    POST /operations/subnets
    Content-Type: application/json
    Accept: application/json

    {
        "ip_address": "192.168.2.0/24"
    }
    ```

    **Example Response:**
    ```json
    {
        "list_of_subnets_ips": [
            "192.168.1.0/24",
            "10.0.0.0/16",
            "192.168.2.0/24"
        ]
    }
    ```
    """
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
    """
    Remove a subnet CIDR address from the scanning configuration.

    This endpoint removes a subnet CIDR address from the stored configuration list.
    The specified subnet will no longer be included in BACnet device discovery
    scans. If the subnet address is not in the list, no changes are made.

    **HTTP Method:** DELETE
    **URL Path:** `/operations/subnets`

    **Request Headers:**
    - `Content-Type: application/json` (required)
    - `Accept: application/json` (default) - Returns JSON response

    **Request Body:**
    ```json
    {
        "ip_address": "192.168.2.0/24"
    }
    ```

    **Response:**
    - **200 OK**: Subnet CIDR address removed successfully (or was not in list)
      - Content-Type: `application/json`
      - Body: `{"list_of_subnets_ips": ["192.168.1.0/24", ...]}`

    **Example Request:**
    ```
    DELETE /operations/subnets
    Content-Type: application/json
    Accept: application/json

    {
        "ip_address": "192.168.2.0/24"
    }
    ```

    **Example Response:**
    ```json
    {
        "list_of_subnets_ips": [
            "192.168.1.0/24",
            "10.0.0.0/16"
        ]
    }
    ```
    """
    list_of_subnets_ips: list = device_config_read_key(agent_data_path, "subnets")
    ip = ip_data.ip_address
    if ip and ip in list_of_subnets_ips:
        list_of_subnets_ips.remove(ip)
        device_config_write_key(agent_data_path, "subnets", list_of_subnets_ips)
    return {"list_of_subnets_ips": list_of_subnets_ips}
