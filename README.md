# Grasshopper

## Description

Grasshopper is an open-source project designed to tackle the complex world of smart building networks. It provides a comprehensive view of building automation systems (BAS) network to help facility managers and integrators understand, manage, and optimize their networks.

**Grasshopper addresses this challenge by:**

- **Autonomous Network Mapping**  
  Grasshopper intelligently scans and maps building automation networks, creating comprehensive network graphs that visualize device relationships and communication pathways.

- **Change Tracking**  
  The tool monitors the network in real-time, logging and highlighting any changes to the configuration – new devices, altered connections, protocol modifications.

- **Insightful Visualization**  
  Collected data is presented in a user-friendly, interactive dashboard. This helps facility managers easily see the health of their BAS.

**Grasshopper Solves:**

- **Opaque Networks**  
  Building automation networks frequently become black boxes, their inner workings poorly documented and difficult to decipher.

- **Reactive Troubleshooting**  
  Without network visibility, issues are often addressed only after they cause problems, leading to downtime and inefficient operations.

- **Vendor Lock-In**  
  The complexity of many BAS environments makes it difficult to integrate new devices or solutions, increasing vendor dependence.

**Benefits:**

- **Proactive Management**  
  Network visibility empowers proactive maintenance, reducing unexpected downtime.

- **Troubleshooting Efficiency**  
  Pinpoint issues rapidly by tracing communication paths and identifying configuration errors.

- **Data-Driven Optimization**  
  Track changes over time to analyze network performance and guide upgrade decisions.

- **Greater Adaptability**  
  Reduce reliance on specific vendors by understanding your network as a whole.

---

## Documentation: Setting Up the Grasshopper Open-Source Agent

1. **Download and Install the VOLTTRON Platform**  
   - Clone or download the [VOLTTRON™️ repository](https://github.com/VOLTTRON/volttron) onto the host server.  
   - Follow the developer’s instructions to install and bootstrap VOLTTRON (e.g., run `bootstrap.py`, then start VOLTTRON).  
   - Run `vcfg` in the command line to configure VOLTTRON.  
   - **Optional**: Disable the web interface unless you plan to utilize VOLTTRON Central.

2. **Pull Down the Grasshopper Agent**  
   - Clone or download the Grasshopper Agent repository into your directory of choice.  
   - Ensure that the IP address or hostname you want to use is properly configured on the operating system for the Grasshopper Agent.  
   - If you have VOLTTRON’s web interface enabled, the Grasshopper Agent’s interface should be accessible from the configured VOLTTRON host.

3. **Build the Grasshopper Frontend**  
   - Navigate to the Grasshopper frontend folder (commonly named something like `frontend` or `grasshopper-frontend`).  
   - Run the appropriate build command (e.g., `npm run build` or `yarn build`) to generate the `dist` folder.  
   - Move (or copy) the newly created `dist` folder into the Grasshopper Agent’s main folder (e.g., `agent/grasshopper`) so the agent can serve its frontend assets.

4. **Install the Grasshopper Agent**  
   - From the VOLTTRON root directory, run the following command to install the agent:
     ```bash
     python scripts/install-agent.py -s Grasshopper -i grasshopper -t grasshopper -f
     ```
   - Add your Grasshopper Agent configuration file to the VOLTTRON configuration store:
     ```bash
     volttron-ctl config store grasshopper config <path to config file>
     ```
   - Once the agent is installed and running, it should automatically check the network once a day (by default).

---

## Configuration

A sample configuration file is provided in the repository. The config file is a JSON file with the following fields:

- **`scan_interval_secs`**: Interval (in seconds) at which the agent will scan the network.
- **`low_limit`**: Lower limit for a BACnet `who_is` scan.
- **`high_limit`**: Upper limit for a BACnet `who_is` scan.
- **`batch_broadcast_size`**: Batch size for a BACnet `who_is` scan.
- **`graph_store_limit`**: Limit on how many network graph files to store.
- **`bacpypes_settings`**: Dictionary settings for the simulated BACnet app, which includes:
  - **`name`**: Name of the BACnet app.
  - **`instance`**: BACnet app instance ID.
  - **`network`**: BACnet app network number.
  - **`address`**: BACnet app IP address (with subnet and port).
  - **`vendoridentifier`**: BACnet app vendor ID.
  - **`foreign`**: BBMD address if registering the app as a foreign device.
  - **`ttl`**: Foreign device subscription time-to-live.
  - **`bbmd`**: BBMD address if registering the app as a BBMD.

### Example Configuration

```json
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
