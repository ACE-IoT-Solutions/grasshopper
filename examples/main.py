from grasshopper.graph import GraphBuilder

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
    builder.graph_to_file(file_path="graph.ttl", format="turtle")
