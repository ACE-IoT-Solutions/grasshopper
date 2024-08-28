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
    - Once the agent is running, it should automatically check the network once a day (default setting).