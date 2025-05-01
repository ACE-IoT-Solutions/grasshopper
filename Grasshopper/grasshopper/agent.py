"""
Copyright 2023 ACE IoT Solutions
Licensed under the MIT License (MIT)
Created by Justice Lee

This agent is used to analyze the BacNet Network using bacpypes3 and return an
overall view of the network.
The agent is configured using the config file, with the bacnet settings stored in the
config file.
The agent will periodically scan the network and publish the responsive devices
detected in a graphical view.
The agent also provides a web interface to view each scan of the network as found.
"""

__docformat__ = "reStructuredText"

import asyncio
import logging
import os
import re
import signal
import sys
import traceback
import json
from multiprocessing import Process
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional, cast

import gevent
import uvicorn
from bacpypes3.local.networkport import NetworkPortObject
from bacpypes3.vendor import VendorInfo
from fastapi import FastAPI
from rdflib import Graph

# from volttron.platform.web import Response
from volttron.platform.agent import utils
from volttron.platform.messaging.health import STATUS_BAD
from volttron.platform.vip.agent import Agent, Core

from .api import (
    executor,
    DEVICE_STATE_CONFIG,
)
from .bacpypes3_scanner import bacpypes3_scanner
from .version import __version__
from .web_app import create_app

_log = logging.getLogger(__name__)
utils.setup_logging()

seconds_in_day: int = 86400


def grasshopper(config_path: str, **kwargs: Any) -> "Grasshopper":
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Grasshopper
    :rtype: Grasshopper
    """
    try:
        config: Dict[str, Any] = utils.load_config(config_path)
    except Exception:  # pylint: disable=broad-except
        # We need to catch any exception from load_config and provide defaults
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    scan_interval_secs: int = config.get("scan_interval_secs", seconds_in_day)
    low_limit: int = config.get("low_limit", 0)
    high_limit: int = config.get("high_limit", 4194303)
    device_broadcast_full_step_size: int = config.get(
        "device_broadcast_full_step_size", 100
    )
    device_broadcast_empty_step_size: int = config.get(
        "device_broadcast_empty_step_size", 1000
    )
    bacpypes_settings: Dict[str, Any] = config.get(
        "bacpypes_settings",
        {
            "name": "Excelsior",
            "instance": 999,
            "network": 0,
            "address": "192.168.1.12/24:47808",
            "vendoridentifier": 999,
            "foreign": None,
            "ttl": 30,
            "bbmd": None,
        },
    )
    webapp_settings: Dict[str, Any] = config.get(
        "webapp_settings",
        {"host": "0.0.0.0", "port": 5000, "certfile": None, "keyfile": None},
    )
    graph_store_limit: Optional[int] = config.get("graph_store_limit", None)
    return Grasshopper(
        scan_interval_secs,
        low_limit,
        high_limit,
        device_broadcast_full_step_size,
        device_broadcast_empty_step_size,
        bacpypes_settings,
        graph_store_limit,
        webapp_settings,
        **kwargs,
    )


class Grasshopper(Agent):
    """
    Document agent constructor here.
    """

    def __init__(
        self,
        scan_interval_secs: int = seconds_in_day,
        low_limit: int = 0,
        high_limit: int = 4194303,
        device_broadcast_full_step_size: int = 100,
        device_broadcast_empty_step_size: int = 1000,
        bacpypes_settings: Optional[Dict[str, Any]] = None,
        graph_store_limit: Optional[int] = None,
        webapp_settings: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(enable_web=True, **kwargs)
        _log.debug("vip_identity: %s", self.core.identity)

        self.bacnet_analysis: Optional[Any] = None
        self.scan_interval_secs: int = scan_interval_secs
        self.low_limit: int = low_limit
        self.high_limit: int = high_limit
        self.device_broadcast_full_step_size: int = device_broadcast_full_step_size
        self.device_broadcast_empty_step_size: int = device_broadcast_empty_step_size
        if bacpypes_settings is None:
            bacpypes_settings = {
                "name": "Excelsior",
                "instance": 999,
                "network": 0,
                "address": "192.168.1.12/24:47808",
                "vendoridentifier": 999,
                "foreign": None,
                "ttl": 30,
                "bbmd": None,
            }
        self.bacpypes_settings: Dict[str, Any] = bacpypes_settings
        if webapp_settings is None:
            webapp_settings = {
                "host": "0.0.0.0",
                "port": 5000,
                "certfile": None,
                "keyfile": None,
            }
        self.webapp_settings: Dict[str, Any] = webapp_settings
        self.graph_store_limit: Optional[int] = graph_store_limit
        self.default_config: Dict[str, Any] = {
            "scan_interval_secs": scan_interval_secs,
            "low_limit": low_limit,
            "high_limit": high_limit,
            "device_broadcast_full_step_size": device_broadcast_full_step_size,
            "device_broadcast_empty_step_size": device_broadcast_empty_step_size,
            "graph_store_limit": graph_store_limit,
            "bacpypes_settings": bacpypes_settings,
            "webapp_settings": webapp_settings,
        }
        self.http_server_process: Optional[Process] = None
        self.agent_data_path: Optional[str] = None
        self.app: Optional[FastAPI] = None
        self.vendor_info: Optional[VendorInfo] = None

        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.vip.config.set_default("config", self.default_config)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(
            self.configure, actions=["NEW", "UPDATE"], pattern="config"
        )
        _log.debug("Init completed")

    def configure(
        self, config_name: str, action: str, contents: Dict[str, Any]
    ) -> None:  # pylint: disable=unused-argument
        # config_name and action are required by the VOLTTRON platform but not used directly
        """
        Called after the Agent has connected to the message bus. If a configuration exists
        at startup
        this will be called before onstart.

        Is called every time the configuration in the store changes.
        """
        _log.debug("Configuring Agent")
        config: Dict[str, Any] = self.default_config.copy()
        config.update(contents)

        if config_name == "config":
            try:
                self.scan_interval_secs = contents.get("scan_interval_secs", 86400)
                self.low_limit = contents.get("low_limit", 0)
                self.high_limit = contents.get("high_limit", 4194303)
                self.device_broadcast_full_step_size = contents.get(
                    "device_broadcast_full_step_size", 100
                )
                self.device_broadcast_empty_step_size = contents.get(
                    "device_broadcast_empty_step_size", 1000
                )
                self.bacpypes_settings = contents.get(
                    "bacpypes_settings",
                    {
                        "name": "Excelsior",
                        "instance": 999,
                        "network": 0,
                        "address": "192.168.1.12/24:47808",
                        "vendoridentifier": 999,
                        "foreign": None,
                        "ttl": 30,
                        "bbmd": None,
                    },
                )
                self.webapp_settings = contents.get(
                    "webapp_settings",
                    {"host": "0.0.0.0", "port": 5000, "certfile": None, "keyfile": None},
                )

                self.configure_server_and_start()

                vendorid: int = self.bacpypes_settings.get("vendoridentifier", 999)
                if vendorid != 999:
                    self.vendor_info = VendorInfo(vendorid)
                    self.vendor_info.register_object_class(56, NetworkPortObject)

            except ValueError as e:
                _log.error("ERROR PROCESSING CONFIGURATION: %s", e)
                return

            if self.bacnet_analysis is not None:
                self.bacnet_analysis.kill()  # pylint: disable=no-member
            self.bacnet_analysis = self.core.periodic(
                self.scan_interval_secs, self.who_is_broadcast
            )

        _log.debug("Config completed")

    def _grequests_exception_handler(self, request: Any, exception: Exception) -> None:
        """
        Log exceptions from grequests
        """
        _log.error("grequests error: %s with %s", exception, request)

    def _device_config_read_key(self, key) -> Optional[Dict[str, Any]]:
        """
        Read a key from the device config
        """
        _log.debug("device_config_read_key")
        try:
            config_path = os.path.join(
                self.agent_data_path, DEVICE_STATE_CONFIG
            )
            if not os.path.exists(config_path):
                _log.error("Config file not found: %s", config_path)
                return None
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if key in config:
                    return config[key]
                else:
                    _log.error("Key %s not found in config", key)
                    return None
        except FileNotFoundError:
            _log.error("Config file not found: %s", config_path)
            return None
        except json.JSONDecodeError:
            _log.error("Error decoding JSON from config file: %s", config_path)
            return None

    def config_retrieve_bbmd_devices(self) -> List[Dict[str, Any]]:
        """
        Retrieve config foreign devices
        """
        _log.debug("config_retrieve_bbmd_devices")
        try:
            bbmd_devices: Dict[str, Any] = self._device_config_read_key("bbmd_devices")
            _log.debug("config_retrieve_bbmd_devices config: %s", bbmd_devices)
            return bbmd_devices
        except KeyError as ke:
            _log.error("Error config_retrieve_subnets: %s", ke)
            return []
            

    def config_retrieve_subnets(self) -> List[Dict[str, Any]]:
        """
        Retrieve config subnets
        """
        _log.debug("config_retrieve_subnets")
        try:
            bbmd_devices: Dict[str, Any] = self._device_config_read_key("subnets")
            _log.debug("config_retrieve_bbmd_devices config: %s", bbmd_devices)
            return bbmd_devices
        except KeyError as ke:
            _log.error("Error config_retrieve_subnets: %s", ke)
            return []

    def run_async_function(
        self, func: Callable[[Graph], Coroutine[Any, Any, Any]], graph: Graph
    ) -> None:
        """
        Run a function asynchronously
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(func(graph))
        finally:
            loop.close()

    def who_is_broadcast(self) -> None:
        """
        Broadcasts a Who-Is message to the BACnet network
        """
        _log.debug("who_is_broadcast")

        def extract_datetime(filename: str) -> datetime:
            datetime_str = filename.replace(".ttl", "")
            return datetime.fromisoformat(datetime_str)

        def is_valid_filename(filename: str) -> bool:
            pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.ttl$"
            return bool(re.match(pattern, filename))

        def find_latest_file(directory: str) -> Optional[str]:
            files = [
                f
                for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
            ]
            valid_files = [f for f in files if is_valid_filename(f)]

            if not valid_files:
                return None

            latest_file = max(valid_files, key=extract_datetime)
            return latest_file

        try:
            if self.agent_data_path is None:
                _log.error("Agent data path is not set")
                return

            base_rdf_path = os.path.join(self.agent_data_path, "ttl/base.ttl")
            recent_ttl_file = find_latest_file(
                os.path.join(self.agent_data_path, "ttl")
            )

            prev_graph: Graph = Graph()
            graph: Graph = Graph()

            if os.path.exists(base_rdf_path):
                graph.parse(base_rdf_path, format="ttl")

            if recent_ttl_file:
                prev_graph.parse(
                    os.path.join(self.agent_data_path, f"ttl/{recent_ttl_file}"),
                    format="ttl",
                )

            now = datetime.now()

            bbmds = self.config_retrieve_bbmd_devices()
            subnets = self.config_retrieve_subnets()
            scanner = bacpypes3_scanner(
                self.bacpypes_settings,
                prev_graph,
                bbmds,
                subnets,
                self.device_broadcast_empty_step_size,
                self.device_broadcast_full_step_size,
                self.low_limit,
                self.high_limit,
            )
            # This is a wrapper that returns None, but gevent.spawn expects a callable
            # Using type ignore as this is a valid pattern even though the types don't
            # align perfectly
            # Spawn a task to run the async function
            gevent.spawn(
                self.run_async_function, scanner.get_device_and_router, graph
            )  # type: ignore

            rdf_path = os.path.join(
                self.agent_data_path,
                f"ttl/{now.replace(microsecond=0).isoformat()}.ttl",
            )
            os.makedirs(os.path.dirname(rdf_path), exist_ok=True)
            graph.serialize(destination=rdf_path, format="turtle")
        except Exception as e:  # pylint: disable=broad-except
            # We need to catch any exception during broadcast to prevent crash
            _log.error("Error in who_is_broadcast: %s", e)
            _log.error(traceback.format_exc())


    def configure_server_and_start(self) -> None:
        """
        Runs to setup web server and processes when configuration changes
        """
        _log.debug("configure_server_setup")

        def ensure_folders_exist(agent_data_path: str, folder_names: List[str]) -> None:
            for folder in folder_names:
                folder_path = os.path.join(agent_data_path, folder)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    print(f"Folder '{folder}' created.")
                else:
                    print(f"Folder '{folder}' already exists.")

        def get_agent_data_path(original_path: str) -> str:
            agent_name = os.path.basename(original_path)
            agent_data = f"{agent_name}.agent-data"
            modified_path = os.path.join(original_path, agent_data)
            return modified_path

        current_dir = os.getcwd()
        agent_data_path = get_agent_data_path(current_dir)
        self.agent_data_path = agent_data_path

        # Create cert/key files
        certfile = self.webapp_settings.get("certfile")
        keyfile = self.webapp_settings.get("keyfile")

        # If using SSL/TLS
        ssl_context: Optional[Dict[str, str]] = None
        if certfile and keyfile:
            try:
                ssl_context = {"certfile": certfile, "keyfile": keyfile}
            except Exception as e:
                print(f"Failed to setup ssl_context: {e}")
                raise

        # Start FastAPI with uvicorn
        host = self.webapp_settings.get("host")
        port = self.webapp_settings.get("port")


        try:
            self.http_server_process = Process(target=self._start_server,args=(host, port, ssl_context), daemon=True)
            self.http_server_process.start()
            
            _log.info(f"[Agent] Starting Uvicorn PID {self.http_server_process.pid}")
        except Exception as e:  # pylint: disable=broad-except
            # We need to catch any server errors to properly set status
            _log.error("Error starting server: %s", e)
            self.vip.health.set_status(STATUS_BAD)
            return -1
        
        if not self.http_server_process.is_alive():
            code = self.http_server_process.exitcode
            _log.error(f"Uvicorn process died immediately with exit code {code}")
        else:
            _log.info(f"Server is alive, running on {host}:{port}")


    def _start_server(
        self, host: str, port: int, ssl_context: Optional[Dict[str, str]] = None
    ) -> int:
        """Start the uvicorn server in a separate thread"""
        _log.debug("Running _start_server")

        # Create FastAPI app
        app = create_app()
        app.extra["agent_data_path"] = self.agent_data_path
        self.app = app

        if self.app is None:
            _log.error("FastAPI app is not initialized")
            return -1

        config = uvicorn.Config(
            app=self.app,  # type: ignore # FastAPI is a valid ASGI app but mypy doesn't know
            host=host,
            port=port,
            ssl_certfile=ssl_context.get("certfile") if ssl_context else None,
            ssl_keyfile=ssl_context.get("keyfile") if ssl_context else None,
            log_level="info",
        )
        server = uvicorn.Server(config)

        server.run()

        _log.debug("Running _start_server complete")
        return 0
    
    def _stop_server(self) -> None:
        """Stop the uvicorn server"""
        _log.debug("Running _stop_server")
        if self.http_server_process and self.http_server_process.is_alive():
            print(f"[Agent] Terminating Uvicorn PID {self.http_server_process.pid}")
            # Send SIGINT for a clean shutdown, or SIGTERM if you prefer
            os.kill(self.http_server_process.pid, signal.SIGINT)
            # Give it a moment to exit gracefully...
            self.http_server_process.join(timeout=5)
            if self.http_server_process.is_alive():
                print("[Agent] Uvicorn did not exit; killing")
                self.http_server_process.terminate()
                self.http_server_process.join(timeout=2)
        _log.debug("Running _stop_server complete")

    @Core.receiver("onstart")
    def onstart(
        self, sender: Any, **kwargs: Any
    ) -> None:  # pylint: disable=unused-argument
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        # Example publish to pubsub
        # self.vip.pubsub.publish('pubsub', "devices/camera/topic", message="HI!")
        _log.debug("in onstart")

        # Set up device config
        _log.info("Setting up Device Config")
        device_config_path = os.path.join(
            self.agent_data_path, DEVICE_STATE_CONFIG
        )
        if not os.path.exists(device_config_path):
            _log.info("Creating device config file: %s", device_config_path)
            with open(device_config_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"bbmd_devices": [], "subnets": []},
                    f,
                    indent=4,
                    ensure_ascii=False,
                )
        else:
            _log.info("Device config file already exists: %s", device_config_path)

        # Sets WEB_ROOT to be the path to the webroot directory
        # in the agent-data directory of the installed agent.
        # WEB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'webroot/'))

    @Core.receiver("onstop")
    def onstop(
        self, sender: Any, **kwargs: Any
    ) -> None:  # pylint: disable=unused-argument
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        _log.debug("in onstop")

        # Kill executor and currently running tasks
        # We need to access protected member here to clean up processes
        for process in executor._processes.values():  # pylint: disable=protected-access
            if process.pid is not None:
                os.kill(process.pid, signal.SIGKILL)
        executor.shutdown(wait=False)

        # Stop the web server
        self._stop_server()


def main() -> None:
    """Main method called to start the agent."""
    # vip_main returns a value, but we're ignoring it as it's not used
    # and the function is declared to return None
    utils.vip_main(grasshopper, version=__version__)  # type: ignore


if __name__ == "__main__":
    # Entry point for script
    try:
        main()  # main() returns None, but we want to exit with code 0
        sys.exit(0)
    except KeyboardInterrupt:
        pass
