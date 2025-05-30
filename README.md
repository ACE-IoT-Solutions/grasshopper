# Grasshopper

![Grasshopper Logo](https://github.com/ACE-IoT-Solutions/grasshopper/blob/main/grasshopper.svg?raw=true)

[![Python Tests](https://github.com/ACE-IoT-Solutions/grasshopper/actions/workflows/test.yml/badge.svg)](https://github.com/ACE-IoT-Solutions/grasshopper/actions/workflows/test.yml)
[![Python Linting](https://github.com/ACE-IoT-Solutions/grasshopper/actions/workflows/lint.yml/badge.svg)](https://github.com/ACE-IoT-Solutions/grasshopper/actions/workflows/lint.yml)

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
   - Navigate to the Grasshopper frontend folder (`grasshopper-frontend`).  
   - In the frontend folder, ensure that NPM (>=11.1.0) and Node (>=23.9.0) are installed at the latest versions.
   - To install Node at the latest version, run `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash`, then `source ~/.bashrc`, then `nvm install 23`, and finally `nvm use 23`
   - Run `npm i` to install all dependencies.
   - Run `npm run build` to generate the `dist` folder.
   - The newly created `dist` folder should appear in the Grasshopper Agent’s main folder (e.g., `agent/grasshopper`). 
   - In the event it does not appear, move (or copy) the newly created `dist` folder into the Grasshopper Agent’s main folder from the frontend (`grasshopper-frontend/dist`) so the agent can serve its frontend assets.

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
   - Another option is to run the same installation from the volttron env. Once activated, run the following to install the same agent. If --force option is added, the agent will be overwritten. However, ttl files and compare files will remain persistent and will not be removed during this process. Example:
     ```bash
     vctl install <path to grasshopper/Grasshopper files> --vip-identity grasshopper --tag gh --force
     ```

---

## Installation / Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/grasshopper.git
    cd grasshopper
    ```

2.  **Create and activate a virtual environment:**
    You can use `uv` or Python's built-in `venv`.

    *   Using `uv`:
        ```bash
        # Create a virtual environment named .venv
        uv venv
        # Activate it (example for bash/zsh)
        source .venv/bin/activate
        # On Windows cmd: .venv\Scripts\activate.bat
        # On Windows PowerShell: .venv\Scripts\Activate.ps1
        ```
    *   Using `venv`:
        ```bash
        python -m venv .venv
        # Activate it (example for bash/zsh)
        source .venv/bin/activate
        # On Windows cmd: .venv\Scripts\activate.bat
        # On Windows PowerShell: .venv\Scripts\Activate.ps1
        ```

3.  **Install dependencies using uv:**
    This command installs both main and development dependencies based on `pyproject.toml`.
    ```bash
    uv pip sync pyproject.toml --extras dev
    ```

---

## Configuration

A sample configuration file is provided in the repository. The config file is a JSON file with the following fields:

- **`scan_interval_secs`**: Interval (in seconds) at which the agent will scan the network.
- **`low_limit`**: Lower limit for a BACnet `who_is` scan.
- **`high_limit`**: Upper limit for a BACnet `who_is` scan.
- **`batch_broadcast_size`**: Batch size for a BACnet `who_is` scan.
- **`bacpypes_settings`**: Dictionary settings for the simulated BACnet app, which includes:
  - **`name`**: Name of the BACnet app.
  - **`instance`**: BACnet app instance ID.
  - **`network`**: BACnet app network number.
  - **`address`**: BACnet app IP address (with subnet and port).
  - **`vendoridentifier`**: BACnet app vendor ID.
  - **`foreign`**: BBMD address if registering the app as a foreign device.
  - **`ttl`**: Foreign device subscription time-to-live.
  - **`bbmd`**: BBMD address if registering the app as a BBMD.
- **`webapp_settings`**: Dictionary settings for the webapp, which includes:
  - **`host`**: IP host for the web app.
  - **`port`**: Port for web app.
  - **`certfile`**: Cert file route.
  - **`keyfile`**: Key file route.

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
    },
    "webapp_settings": {
      "host": "0.0.0.0",
      "port": 5000,
      "certfile": null,
      "keyfile": null
    }
}
```
## Changelog

### 0.1.1

  - Fixed github workflow errors by cleaning up code

### 0.1.0

  - Latest stable version for release