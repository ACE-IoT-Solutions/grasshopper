import csv
import os
import uuid
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO, StringIO

import gevent
from bacpypes3.rdf.core import BACnetNS
from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from gevent.queue import Queue
from networkx import DiGraph
from pyvis.network import Network
from rdflib import Graph, Literal
from rdflib.compare import graph_diff, to_isomorphic
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
from rdflib.namespace import RDFS

from .models import Data, Message, MessageFile, MessageStatus, NetworkData
from .serializers import CompareTTLFiles, FileList, IPAddress, IPAddressList

# Create a router for API operations
router = APIRouter(prefix="/api/operations")

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

            if not os.path.exists(ttl_filepath_1):
                raise FileNotFoundError(
                    f"The file '{ttl_filename_2}' does not exist in the current directory."
                )

            g1 = Graph()
            g2 = Graph()
            g1.parse(ttl_filepath_1, format="ttl")
            gevent.sleep(0)

            g2.parse(ttl_filepath_2, format="ttl")
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
                combined_graph.add(
                    (triple_id, BACnetNS["rdf_diff_source"], Literal(ttl_filename_1))
                )

            for s, p, o in in_second:
                gevent.sleep(0)
                combined_graph.add((s, p, o))
                triple_id = Literal(f"{s} {p} {o}")
                combined_graph.add(
                    (triple_id, BACnetNS["rdf_diff_source"], Literal(ttl_filename_2))
                )

            for s, p, o in in_both:
                gevent.sleep(0)
                combined_graph.add((s, p, o))

            compare_folder_path = os.path.join(agent_data_path, "compare")
            combined_filename = f"{ttl_filename_1.replace('.ttl', '')}_vs_{ttl_filename_2.replace('.ttl', '')}.ttl"
            combined_filepath = os.path.join(compare_folder_path, combined_filename)
            combined_graph.serialize(destination=combined_filepath, format="ttl")

            processing_task = None
        except Exception as e:
            print(f"Error processing task: {e}")


gevent.spawn(process_compare_rdf_queue)


def build_networkx_graph(
    g: Graph,
) -> tuple[DiGraph, dict, dict]:
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
        edge_label = attr.get("triples", [])[0][1] if "triples" in attr else None
        if RDFS["label"] in edge_label:
            rdf_edges[u] = v
            remove_nodes.append(u)
            remove_nodes.append(v)
        elif "rdf_diff_source" in edge_label:
            rdf_diff_list.append((u, v, edge_label))
        elif "device-address" in edge_label:
            device_address_edges.append((u, v))
            remove_nodes.append(v)
        elif (
            "device-on-network" not in edge_label
            and "router-to-network" not in edge_label
        ):
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
    nx_graph: DiGraph,
    net: Network,
    node_data: dict,
    edge_data: dict,
):
    for node in nx_graph.nodes:
        net.add_node(node, data=node_data.get(str(node), {}))

    for u, v, attr in nx_graph.edges(data=True):
        edge_label = attr.get("triples", [])[0][1] if "triples" in attr else None
        edge_id = f"{u} {edge_label} {v}"
        net.add_edge(u, v, label=edge_label, data=edge_data.get(edge_id, {}))


def get_file_path(
    request: Request,
    file_name: str,
    folder: str = "ttl",
) -> str | None:
    current_dir = request.app.state.agent_data_path
    folder_path = os.path.join(current_dir, folder)
    if not os.path.exists(folder_path):
        raise FileNotFoundError(
            f"The folder '{folder}' does not exist in the current directory."
        )

    for root, dirs, files in os.walk(folder_path):
        if file_name in files:
            return os.path.join(root, file_name)

    return None


def list_files_in_dir(
    request: Request,
    folder: str = "ttl",
) -> list[str]:
    current_dir = request.app.state.agent_data_path
    folder_path = os.path.join(current_dir, folder)
    files = [
        f
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]
    return files


@router.get("/hello")
async def hello() -> Message:
    """Returns a simple greeting message."""
    return Message(message="Hello, world!")


@router.get("/ttl")
async def get_ttl_list(
    request: Request,
) -> Data:
    """Gets ttl list"""
    data = []
    agent_data_path = request.app.state.agent_data_path
    graph_ttl_roots = os.path.join(agent_data_path, "ttl/")
    if os.path.exists(graph_ttl_roots):
        for filename in os.listdir(graph_ttl_roots):
            if filename.endswith(".ttl"):
                data.append(filename)
    return Data(data=data)


@router.post("/ttl", status_code=status.HTTP_201_CREATED)
async def upload_ttl_file(
    request: Request,
    file: UploadFile = File(...),
) -> MessageFile:
    """Upload ttl file"""
    ALLOWED_EXTENSIONS = {"ttl"}

    def allowed_file(filename: str) -> bool:
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    agent_data_path = request.app.state.agent_data_path
    ttl_dir = os.path.join(agent_data_path, "ttl")

    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file part in the request",
        )

    if file.filename == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No selected file"
        )

    if file.filename and allowed_file(file.filename):
        file_path = os.path.join(ttl_dir, file.filename)
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        return MessageFile(
            message=f"File {file.filename} uploaded successfully", file_path=file_path
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed"
        )


@router.get("/ttl_file/{ttl_filename}")
async def download_ttl_file(
    request: Request,
    ttl_filename: str,
) -> FileResponse:
    """Download ttl file"""
    ttl_filepath = get_file_path(request, ttl_filename)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    try:
        return FileResponse(ttl_filepath, filename=ttl_filename)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/ttl_file/{ttl_filename}")
async def delete_ttl_file(
    request: Request,
    ttl_filename: str,
) -> Message:
    """Delete ttl file"""
    ttl_filepath = get_file_path(request, ttl_filename)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if os.path.exists(ttl_filepath):
        os.remove(ttl_filepath)
        return Message(message="File deleted successfully")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )


@router.get("/ttl_network/{ttl_filename}")
async def get_ttl_network(
    request: Request,
    ttl_filename: str,
) -> NetworkData:
    """Get ttl file network in json"""
    ttl_filepath = get_file_path(request, ttl_filename)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    g = Graph()
    g.parse(ttl_filepath, format="ttl")
    nx_graph, node_data, edge_data = build_networkx_graph(g)

    net = Network()
    pass_networkx_to_pyvis(nx_graph, net, node_data, edge_data)
    return NetworkData(nodes=net.nodes, edges=net.edges)


@router.post("/ttl_compare_queue", status_code=status.HTTP_202_ACCEPTED)
async def post_ttl_compare_queue(
    request: Request,
    compare_data: CompareTTLFiles,
) -> MessageStatus:
    """Adds ttl compare file request to queue"""
    ttl_filename_1 = compare_data.ttl_1
    ttl_filename_2 = compare_data.ttl_2
    ttl_filepath_1 = get_file_path(request, ttl_filename_1)
    ttl_filepath_2 = get_file_path(request, ttl_filename_2)
    if not ttl_filepath_1 or not ttl_filepath_2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    queue_contents = list(compare_rdf_queue.queue)
    if processing_task:
        queue_contents.append(processing_task)

    for task in queue_contents:
        if (
            task.get("ttl_1") == ttl_filename_1 and task.get("ttl_2") == ttl_filename_2
        ) or (
            task.get("ttl_1") == ttl_filename_2 and task.get("ttl_2") == ttl_filename_1
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Task already in queue"
            )

    compare_rdf_queue.put(
        {
            "id": str(uuid.uuid4()),
            "ttl_1": ttl_filename_1,
            "ttl_2": ttl_filename_2,
            "agent_data_path": request.app.state.agent_data_path,
        }
    )

    return MessageStatus(status="accepted", message="File accepted")


@router.get("/ttl_compare_queue")
async def get_ttl_compare_queue():
    """Gets current queue and processing task"""
    queue_contents = list(compare_rdf_queue.queue)
    return {
        "processing_task": processing_task if processing_task else "None",
        "queue": queue_contents,
    }


@router.delete("/ttl_compare_queue_tasks/{task_id}")
async def delete_ttl_compare_queue_task(
    task_id: str,
) -> MessageStatus:
    """Removes task from queue"""
    global compare_rdf_queue
    if processing_task and processing_task.get("id") == task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MessageStatus(
                status="error", message="Task is currently being processed"
            ),
        )
    queue_contents = list(compare_rdf_queue.queue)
    new_queue = [task for task in queue_contents if task["id"] != task_id]

    if len(new_queue) == len(queue_contents):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MessageStatus(status="error", message=f"Task {task_id} not found"),
        )

    compare_rdf_queue = Queue()
    for task in new_queue:
        compare_rdf_queue.put(task)

    return MessageStatus(
        status="success", message=f"Task {task_id} removed from the queue"
    )


@router.get("/ttl_compare", response_model=FileList)
async def get_ttl_compare_list(
    request: Request,
):
    """Get list of comparison ttl files"""
    file_list = list_files_in_dir(request, folder="compare")
    return {"file_list": file_list}


@router.get("/ttl_compare/{ttl_filename}")
async def get_ttl_compare_network(
    request: Request,
    ttl_filename: str,
) -> NetworkData:
    """Get network json from compare file"""
    ttl_filepath = get_file_path(request, ttl_filename, folder="compare")
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    g = Graph()
    g.parse(ttl_filepath, format="ttl")
    nx_graph, node_data, edge_data = build_networkx_graph(g)

    net = Network()
    pass_networkx_to_pyvis(nx_graph, net, node_data, edge_data)

    return NetworkData(nodes=net.nodes, edges=net.edges)


@router.delete("/ttl_compare/{ttl_filename}")
async def delete_ttl_compare_file(
    request: Request,
    ttl_filename: str,
) -> Message:
    """Delete ttl compare file"""
    ttl_filepath = get_file_path(request, ttl_filename, folder="compare")
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if os.path.exists(ttl_filepath):
        os.remove(ttl_filepath)
        return Message(message="File deleted successfully")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )


@router.get("/network_config")
async def get_network_config_list(
    request: Request,
):
    """Gets network config list"""
    data = []
    agent_data_path = request.app.state.agent_data_path
    network_config_roots = os.path.join(agent_data_path, "network_config")
    if os.path.exists(network_config_roots):
        for filename in os.listdir(network_config_roots):
            if filename.endswith(".json"):
                data.append(filename)
    return Data(data=data)


@router.post("/network_config", status_code=status.HTTP_201_CREATED)
async def upload_network_config(
    request: Request,
    file: UploadFile = File(...),
) -> MessageFile:
    """Upload network config json file"""
    ALLOWED_EXTENSIONS = {"json"}

    def allowed_file(filename):
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    agent_data_path = request.app.state.agent_data_path
    network_config_path = os.path.join(agent_data_path, "network_config")

    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file part in the request",
        )

    if file.filename == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No selected file"
        )

    if file.filename and allowed_file(file.filename):
        file_path = os.path.join(network_config_path, file.filename)
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        return MessageFile(
            message=f"File {file.filename} uploaded successfully", file_path=file_path
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed"
        )


@router.get("/network_config/{network_config_filename}")
async def download_network_config(request: Request, network_config_filename: str):
    """Download network config json file"""
    network_config_filepath = get_file_path(
        request, network_config_filename, "network_config"
    )
    if not network_config_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    try:
        return FileResponse(network_config_filepath, filename=network_config_filename)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/network_config/{network_config_filename}")
async def delete_network_config(
    request: Request,
    network_config_filename: str,
) -> Message:
    """Delete network config json file"""
    network_config_filepath = get_file_path(
        request, network_config_filename, "network_config"
    )
    if not network_config_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if os.path.exists(network_config_filepath):
        os.remove(network_config_filepath)
        return Message(message="File deleted successfully")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )


@router.get("/csv_export/{ttl_filename}")
async def export_csv(
    request: Request,
    ttl_filename: str,
) -> Response:
    """Export ttl file to csv"""
    ttl_filepath = get_file_path(request, ttl_filename)
    if not ttl_filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    g = Graph()
    g.parse(ttl_filepath, format="ttl")
    nx_graph, node_data, edge_data = build_networkx_graph(g)

    for u, v, attr in nx_graph.edges(data=True):
        edge_label = attr.get("triples", [])[0][1] if "triples" in attr else None
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
    output_str.seek(0)
    output_bytes = BytesIO(output_str.getvalue().encode("utf-8"))

    filename = f"{ttl_filename}.csv"
    return Response(
        content=output_bytes.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Function to add subnet and bbmd device configuration API routes
def setup_bbmd_routes(app):
    bbmd_router = APIRouter(prefix="/api")

    @bbmd_router.get("/subnets", response_model=IPAddressList)
    async def get_subnets(request: Request):
        """Gets the list of Subnets CIDR Addresses stored in the config"""
        # This function would be implemented inside the agent.py
        # To be called from the agent instance
        return {"ip_address_list": []}

    @bbmd_router.post("/subnets")
    async def add_subnet(
        request: Request,
        data: IPAddress,
    ) -> MessageStatus:
        """Adds ip address to the list of Subnets CIDR Addresses stored in the config"""
        # This function would be implemented inside the agent.py
        return MessageStatus(status="success", message="Subnet added")

    @bbmd_router.delete("/subnets")
    async def delete_subnet(request: Request, data: IPAddress):
        """Removes ip address from the list of subnets IP Addresses stored in the config"""
        # This function would be implemented inside the agent.py
        return MessageStatus(status="success", message="Subnet removed")

    @bbmd_router.get("/bbmds", response_model=IPAddressList)
    async def get_bbmds(
        request: Request,
    ):
        """Gets the list of BBMD IP Addresses stored in the config"""
        # This function would be implemented inside the agent.py
        return {"ip_address_list": []}

    @bbmd_router.post("/bbmds")
    async def add_bbmd(
        request: Request,
        data: IPAddress,
    ) -> MessageStatus:
        """Adds ip address to the list of BBMD IP Addresses stored in the config"""
        # This function would be implemented inside the agent.py
        return MessageStatus(status="success", message="BBMD added")

    @bbmd_router.delete("/bbmds")
    async def delete_bbmd(
        request: Request,
        data: IPAddress,
    ) -> MessageStatus:
        """Removes ip address from the list of BBMD IP Addresses stored in the config"""
        # This function would be implemented inside the agent.py
        return MessageStatus(status="success", message="BBMD removed")

    app.include_router(bbmd_router)


def setup_routes(app):
    app.include_router(router)
    # Note: setup_bbmd_routes is not called here as it would be called from agent.py
    # setup_bbmd_routes(app)
