# Grasshopper

## Description

Grasshopper is an open-source project designed to tackle the complex world of smart building networks. It provides a comprehensive view of building automation systems (BAS) network to help facility managers and integrators understand, manage, and optimize their networks.

**Grasshopper addresses this challenge by:**

Autonomous Network Mapping: Grasshopper intelligently scans and maps building automation networks, creating comprehensive network graphs that visualize device relationships and communication pathways.

Change Tracking: The tool monitors the network in real-time, logging and highlighting any changes to the configuration – new devices, altered connections, protocol modifications.

Insightful Visualization: Collected data is presented in a user-friendly, interactive dashboard. This helps facility managers easily see the health of their BAS.

**Grasshopper Solves:**

Opaque Networks: Building automation networks frequently become black boxes, their inner workings poorly documented and difficult to decipher.

Reactive Troubleshooting: Without network visibility, issues are often addressed only after they cause problems, leading to downtime and inefficient operations.

Vendor Lock-In: The complexity of many BAS environments makes it difficult to integrate new devices or solutions, increasing vendor dependence.

**Benefits:**

Proactive Management: Network visibility empowers proactive maintenance, reducing unexpected downtime.

Troubleshooting Efficiency: Pinpoint issues rapidly by tracing communication paths and identifying configuration errors.

Data-Driven Optimization: Track changes over time to analyze network performance and guide upgrade decisions.

Greater Adaptability: Reduce reliance on specific vendors by understanding your network as a whole.

## Setup

1. Download the Volttron platform unto the host server and follow developer's instructions in setting it up.
    - Along with the usual setup of running bootstrap.py and starting volttron, make sure to run the vcfg in the command line to set up the configuration
    - In the configuration, enable the web interface for volttron

2. Pull down the grasshopper agent into the directory of choice.
    - The chosen IP Address will need to be set up on the os for the grasshopper agent to utilize
    - Assuming that the web interface is enabled, it should be accessible from the volttron config host

3. Install the agent
    - The agent can be installed using the VOLTTRON™️ Control Panel, or by running the following command from the VOLTTRON™️ root directory:

```python scripts/install-agent.py -s YoloOcc -i yoloocc -t yoloocc -f```

    - Then adding the configuration file to the VOLTTRON™️ configuration store:

```volttron-ctl config store yoloocc config <path to config file>```

    - Once the agent is running, it should automatically check the network once a day (default setting).


## Configuration
A sample config is provided in the repository. The config file is a JSON file with the following fields:
*scan_interval_secs": Interval at which the agent will scan the network
*"low_limit": Lower limit of a bacnet who_is scan
*"high_limit": Upper limit of a bacnet who_is scan
*"batch_broadcast_size": Batch size of bacnet who_is scan
*"graph_store_limit": Limit to store graph files
*"bacpypes_settings": Dictionary settings for simulated bacnet app
    *"name": Name of bacnet app
    *"instance": bacnet app instance
    *"network": bacnet app network
    *"address": bacnet app ip address
    *"vendoridentifier": bacnet app vendor id
    *"foreign": BBMD address to app as a foreign device
    *"ttl": foreign device subscription time-to-live
    *"bbmd": BDT address fr app as a BBMD

Example below:
```
{
    "scan_interval_secs": 86400,
    "low_limit": 0,
    "high_limit": 4194303,
    "batch_broadcast_size": 10000,
    "graph_store_limit": 30,
    "bacpypes_settings": {
        "name": "Excelsior",
        "instance": 999,
        "network": 0,
        "address": "192.168.1.12/24:47808",
        "vendoridentifier": 999,
        "foreign": null,
        "ttl": 30,
        "bbmd": null
    }
}
```

