#!/usr/bin/env python3

"""
FirefoxController Execution Manager

This module handles Firefox process management and WebDriver BiDi connections.
"""

import json
import logging
import subprocess
import time
import uuid
import websocket
import distutils.spawn
import tempfile
import os
import os.path
import shutil
import base64
import queue
import threading
import urllib.request
import signal
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse

try:
    from websockets.sync.client import connect
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    connect = None

from .exceptions import (
    FirefoxStartupException,
    FirefoxConnectFailure,
    FirefoxCommunicationsError,
    FirefoxError,
    FirefoxTabNotFoundError,
    FirefoxDiedError,
    FirefoxNavigateTimedOut,
    FirefoxResponseNotReceived
)


class FirefoxExecutionManager:
    """
    Class for managing Firefox execution and remote debugging connection.
    
    This is similar to ChromeExecutionManager in ChromeController but adapted
    for Firefox's remote debugging protocol using Marionette.
    """
    
    def __init__(self,
                 binary: str = "firefox",
                 host: str = "localhost",
                 port: Optional[int] = 9222,
                 websocket_timeout: int = 10,
                 headless: bool = False,
                 additional_options: List[str] = None,
                 profile_dir: str = None):
        """
        Initialize Firefox execution manager.

        Args:
            binary: Path to Firefox binary
            host: Host to connect to
            port: Debug port to use (9222 default, None for automatic selection)
            websocket_timeout: WebSocket timeout in seconds
            headless: Run Firefox in headless mode
            additional_options: Additional command line options for Firefox
            profile_dir: Custom profile directory (None for temporary profile)
        """
        self.binary = binary
        self.host = host
        self.log = logging.getLogger("FirefoxController.ExecutionManager")

        # Handle automatic port selection
        if port is None:
            from .utils import find_available_port
            self.port = find_available_port()
            self.log.info("Auto-selected port: {}".format(self.port))
        else:
            self.port = port
        self.websocket_timeout = websocket_timeout
        self.headless = headless
        self.additional_options = additional_options or []
        self.profile_dir = profile_dir
        self.process = None
        self.ws = None
        self.ws_connection = None
        self.root_actor = None
        self.log = logging.getLogger("FirefoxController.ExecutionManager")

        if self.profile_dir is None:
            self.profile_dir = os.path.expanduser("~/.firefox_controller_profile")
        
        # Message ID counter
        self.msg_id = 0
        
        # Track active tabs - each tab will have its own interface
        self.tabs = {}  # context_id -> FirefoxRemoteDebugInterface
        self.tab_id_map = {}  # context_id -> tab_info
        
        # Track browsing context for the default tab
        self.browsing_context = None
        self.user_context = None
        self.default_interface = None  # Default interface for backward compatibility
        
        # Temporary profile directory
        self.temp_profile = None

        # Per-tab event queues for handling asynchronous events
        self.event_queues = {}  # context_id -> queue.Queue()
        self.event_queues_lock = threading.Lock()

        # Thread safety for ExecutionManager (shared across tabs)
        self.ws_lock = threading.Lock()  # Protects WebSocket send/recv

        # Track global network event subscription (shared across all tabs)
        self.network_events_subscribed = False
        self.network_logging_refs = 0  # Count of tabs with logging enabled
        self.network_subscription_lock = threading.Lock()

        # Track which contexts have logging enabled
        self.logging_enabled_contexts = set()
        self.logging_contexts_lock = threading.Lock()

        # Track interface instances with logging enabled for automatic polling
        self._logging_interfaces = []  # List of interface instances
        self._logging_interfaces_lock = threading.Lock()
        
    def _install_ublock_origin(self, profile_path: str):
        """
        Download and install uBlock Origin extension into the profile.

        Args:
            profile_path: Path to the Firefox profile directory
        """
        # uBlock Origin extension ID and download URL
        extension_id = "uBlock0@raymondhill.net"
        # Mozilla Add-ons direct download URL for uBlock Origin
        ublock_url = "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi"

        # Create extensions directory
        extensions_dir = os.path.join(profile_path, "extensions")
        if not os.path.exists(extensions_dir):
            os.makedirs(extensions_dir)

        # Extension file path (Firefox expects {extension_id}.xpi)
        extension_path = os.path.join(extensions_dir, "{}.xpi".format(extension_id))

        # Check if already downloaded
        if os.path.exists(extension_path):
            self.log.debug("uBlock Origin already installed at {}".format(extension_path))
            return

        # Download the extension
        self.log.info("Downloading uBlock Origin extension...")
        try:
            # Create a request with a proper User-Agent to avoid 403 errors
            request = urllib.request.Request(
                ublock_url,
                headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0'}
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                xpi_data = response.read()

            # Write the XPI file
            with open(extension_path, 'wb') as f:
                f.write(xpi_data)

            self.log.info("uBlock Origin installed to {}".format(extension_path))

        except Exception as e:
            self.log.warning("Failed to download uBlock Origin: {}".format(e))
            # Don't raise - extension is optional, continue without it

    def _create_profile(self) -> str:
        """Create a temporary Firefox profile with required preferences"""
        # Use provided profile directory
        profile_path = self.profile_dir
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)
   
        # Install uBlock Origin extension
        self._install_ublock_origin(profile_path)

        # Create prefs.js only if it doesn't exist (allows user customization)
        prefs_file = os.path.join(profile_path, "prefs.js")
        if not os.path.exists(prefs_file):
            # These are the critical settings that Firefox requires for remote debugging
            prefs_content = """user_pref("devtools.debugger.remote-enabled", true);
user_pref("devtools.chrome.enabled", true);
user_pref("devtools.debugger.prompt-connection", false);
user_pref("devtools.debugger.forbid-certified-apps", false);
user_pref("devtools.remote.adb.extensionURL", "");
user_pref("devtools.remote.wifi.enabled", true);
user_pref("devtools.remote.usb.enabled", true);

user_pref("devtools.remote.force-local", true);
user_pref("devtools.debugger.force-local", true);
user_pref("devtools.debugger.chrome-enabled", true);
user_pref("devtools.debugger.remote-mode", true);
user_pref("devtools.debugger.remote-port", {});
user_pref("devtools.debugger.remote-host", "localhost");

// Auto-enable extensions without user interaction
user_pref("extensions.autoDisableScopes", 0);
user_pref("extensions.enabledScopes", 15);
// Don't show first-run pages for extensions
user_pref("extensions.getAddons.showPane", false);
user_pref("extensions.update.enabled", false);
""".format(self.port)
            with open(prefs_file, "w") as f:
                f.write(prefs_content)
            self.log.info("Created new prefs.js in profile")
        else:
            self.log.debug("Using existing prefs.js (user customizations preserved)")

        return profile_path
    
    def start_firefox(self):
        """Start Firefox with Marionette enabled"""
        if not distutils.spawn.find_executable(self.binary):
            raise FirefoxStartupException("Firefox binary not found: {}".format(self.binary))
        
        # Create profile if needed
        profile_path = self._create_profile()
        
        # Build command line
        cmd = [self.binary]
        
        if self.headless:
            cmd.extend(["--headless"])
            
        # Use the profile
        cmd.extend(["--profile", profile_path])
        
        # Enable WebDriver BiDi (the modern standard)
        cmd.extend([
            "--remote-debugging-port", str(self.port),  # Start the Firefox Remote Agent
            "--remote-allow-hosts", "localhost,127.0.0.1",  # Allow local connections
            "--remote-allow-origins", "http://localhost,http://127.0.0.1",  # Allow local origins
        ])
        
        # Add additional options
        cmd.extend(self.additional_options)
        
        self.log.info("Starting Firefox with command: {}".format(' '.join(cmd)))
        self.log.info("Using profile: {}".format(profile_path))
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=self._set_pdeathsig
            )
            
            # Give Firefox more time to start
            time.sleep(4)
            
            # Check if process is still running
            if self.process.poll() is not None:
                stderr = self.process.stderr.read().decode('utf-8') if self.process.stderr else ""
                raise FirefoxStartupException("Firefox failed to start: {}".format(stderr))
                
        except Exception as e:
            raise FirefoxStartupException("Failed to start Firefox: {}".format(e))
    
    def _set_pdeathsig(self):
        """Set parent death signal to ensure Firefox dies when parent dies"""
        import signal
        import os
        try:
            # Set the child process to be killed when parent dies
            if hasattr(signal, 'SIGTERM'):
                import ctypes
                libc = ctypes.CDLL("libc.so.6")
                libc.prctl(1, signal.SIGTERM)
        except:
            pass  # Not critical if this fails
    
    def connect(self):
        """Connect to Firefox remote debugging interface using WebDriver BiDi"""
        if not self.process or self.process.poll() is not None:
            raise FirefoxConnectFailure("Firefox process is not running")
        
        if not WEBSOCKETS_AVAILABLE:
            raise FirefoxConnectFailure("websockets library not available. Please install with: pip install websockets")
        
        try:
            # Give Firefox more time to start
            time.sleep(3)
            
            # WebDriver BiDi uses a session-based WebSocket URL (based on working implementation)
            ws_url = "ws://127.0.0.1:{}/session".format(self.port)
            
            self.log.info("Connecting to WebDriver BiDi WebSocket: {}".format(ws_url))
            
            # Connect using websockets.sync.client (more reliable)
            self.ws_connection = connect(ws_url)
            
            # Initialize the WebDriver BiDi connection
            self._initialize_bidi_connection()
            
        except Exception as e:
            raise FirefoxConnectFailure("Connection failed: {}".format(e))
    
    def _initialize_bidi_connection(self):
        """Initialize WebDriver BiDi connection (based on working implementation)"""
        try:
            # Initiate the session (based on working implementation)
            session_id = self._send_message({
                'method': 'session.new',
                'params': {
                    'capabilities': {}
                }
            })['result']['sessionId']
            
            self.session_id = session_id
            self.root_actor = "bidi"
            self.log.info("Connected to WebDriver BiDi session: {}".format(session_id))
            
            # Subscribe to browser events
            self._send_message({
                'method': 'session.subscribe',
                'params': {
                    'events': [
                        'browsingContext.domContentLoaded',
                    ]
                }
            })
            
            # Create the browsing context
            user_context = self._send_message({
                'method': 'browser.createUserContext',
                'params': {}
            })['result']['userContext']
            
            self.user_context = user_context
            
            # Create browsing context and handle the event response
            create_response = self._send_message({
                'method': 'browsingContext.create',
                'params': {
                    'type': 'tab',
                    'userContext': user_context
                }
            })
            
            # The response might be an event or a result
            if create_response.get('type') == 'event' and create_response.get('method') == 'browsingContext.domContentLoaded':
                self.browsing_context = create_response['params']['context']
            elif create_response.get('type') == 'success' and 'result' in create_response and 'context' in create_response['result']:
                self.browsing_context = create_response['result']['context']
            else:
                # If we get an event but not the right one, listen for the correct event
                event = self._receive_event('browsingContext.domContentLoaded', {
                    'userContext': user_context
                }, timeout=5)
                if event:
                    self.browsing_context = event['params']['context']
                else:
                    raise FirefoxCommunicationsError("Failed to create browsing context")
            
            self.log.info("Created browsing context: {}".format(self.browsing_context))
            
            # Get the list of browsing contexts (tabs/windows)
            self._list_browsing_contexts()
            
        except Exception as e:
            self.log.warning("WebDriver BiDi initialization failed: {}".format(e))
            raise FirefoxCommunicationsError("Failed to initialize WebDriver BiDi connection: {}".format(e))
    
    def _send_message(self, message: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
        """Send a message to Firefox and wait for response (thread-safe)

        Args:
            message: WebDriver BiDi message to send
            timeout: Timeout in seconds (defaults to websocket_timeout)

        Returns:
            Response message from Firefox

        Raises:
            FirefoxResponseNotReceived: If no response received within timeout
            FirefoxError: If Firefox returns an error response
        """
        if not self.ws_connection:
            raise FirefoxCommunicationsError("WebSocket not connected")

        with self.ws_lock:  # Thread-safe WebSocket access
            try:
                # Always assign a new message ID to avoid collisions
                self.msg_id += 1
                message["id"] = self.msg_id

                expected_id = message["id"]

                message_str = json.dumps(message)
                self.log.debug("Sending message: {}".format(message_str))

                self.ws_connection.send(message_str)

                # Wait for response with matching ID
                timeout = timeout if timeout is not None else self.websocket_timeout
                start_time = time.time()

                while time.time() - start_time < timeout:
                    # Calculate remaining timeout
                    remaining_timeout = timeout - (time.time() - start_time)
                    if remaining_timeout <= 0:
                        break

                    try:
                        # Pass timeout to recv() to prevent infinite blocking
                        response_str = self.ws_connection.recv(timeout=remaining_timeout)
                    except TimeoutError:
                        # WebSocket timeout - break out and raise FirefoxResponseNotReceived
                        break

                    self.log.debug("Received response: {}".format(response_str))

                    response = json.loads(response_str)

                    # Check if this is the response we're waiting for
                    if response.get("id") == expected_id:
                        # Check for errors
                        if "error" in response:
                            error_msg = response.get("message", "Unknown error")
                            if isinstance(error_msg, dict):
                                error_msg = str(error_msg)
                            raise FirefoxError("Firefox error: {}".format(error_msg))
                        elif response.get("type") == "error":
                            error_msg = response.get("message", "Unknown error")
                            raise FirefoxError("Firefox error: {}".format(error_msg))

                        return response

                    # If this is an event or a response for a different message, queue it
                    if response.get("type") == "event" or response.get("method"):
                        # This is an event - route it to the appropriate per-tab queue
                        context_id = None
                        if "params" in response and "context" in response["params"]:
                            context_id = response["params"]["context"]

                        if context_id:
                            event_queue = self.get_event_queue_for_context(context_id)
                            event_queue.put(response)
                        # If no context, discard it (shouldn't happen for network events)
                        continue

                    # If this is a response for a different message, we might want to handle it
                    # For now, just continue waiting for our response


                raise FirefoxResponseNotReceived("Timeout waiting for response with ID {} after {} seconds".format(expected_id, timeout))

            except FirefoxResponseNotReceived:
                # Re-raise timeout exceptions as-is
                raise
            except FirefoxError:
                # Re-raise Firefox errors as-is
                raise
            except Exception as e:
                raise FirefoxCommunicationsError("Failed to send message: {}".format(e))

    def get_event_queue_for_context(self, context_id: str) -> queue.Queue:
        """Get or create the event queue for a specific browsing context."""
        with self.event_queues_lock:
            if context_id not in self.event_queues:
                self.event_queues[context_id] = queue.Queue()
            return self.event_queues[context_id]

    def poll_for_events(self, timeout: float = 0.1) -> int:
        """
        Poll WebSocket for events without sending a message (thread-safe).

        This reads from the WebSocket and distributes events to per-tab queues.
        Useful for capturing async events like network.responseCompleted.

        Args:
            timeout: How long to wait for events (seconds)

        Returns:
            Number of events received
        """
        if not self.ws_connection:
            return 0

        events_received = 0

        with self.ws_lock:  # Thread-safe WebSocket access
            try:
                # Poll with timeout - websockets-sync uses timeout parameter on recv()
                try:
                    while True:
                        # Use timeout parameter on recv() instead of settimeout()
                        response_str = self.ws_connection.recv(timeout)
                        if not response_str:
                            break

                        response = json.loads(response_str)
                        self.log.debug("Polled event/response: {}".format(response_str[:200]))

                        # Distribute events to the correct per-tab queue
                        if response.get("type") == "event" or response.get("method"):
                            # Extract the context from the event if available
                            context_id = None
                            if "params" in response and "context" in response["params"]:
                                context_id = response["params"]["context"]

                            # If we have a context, queue it for that specific tab
                            if context_id:
                                event_queue = self.get_event_queue_for_context(context_id)
                                event_queue.put(response)
                                events_received += 1
                            else:
                                # No context - this is a global event, queue for all tabs
                                # or just log and ignore
                                self.log.debug("Received event without context: {}".format(response.get("method")))
                        elif "id" in response:
                            # This is a response to a command - these aren't context-specific
                            # Put in the first available queue or handle separately
                            # For now, just log
                            self.log.debug("Received command response during polling: {}".format(response.get("id")))

                except TimeoutError:
                    # Timeout is expected when polling - no more events available
                    pass
                except Exception as e:
                    # Other errors - log and continue
                    self.log.debug("Error polling for events: {}".format(e))

            except Exception as e:
                self.log.debug("Error in poll_for_events: {}".format(e))

        return events_received
    
    def _receive_event(self, event_type: str, params: dict, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Receive a specific event from the WebSocket"""
        try:
            # Use the websockets library's timeout parameter (not settimeout/gettimeout)
            try:
                response_str = self.ws_connection.recv(timeout=timeout)
                response = json.loads(response_str)

                # Check if this is the event we're looking for
                if (response.get("method") == event_type and
                    self._dictionaries_match(params, response.get("params", {}), False)):
                    return response

                # If it's an error, raise it
                if response.get("type") == "error":
                    error_msg = response.get("message", "Unknown error")
                    raise FirefoxError("Firefox error: {}".format(error_msg))

                # If it's a response to a previous message, ignore it
                if "id" in response:
                    # This is a response to a previous request, not an event
                    # Continue waiting for the actual event
                    return None

                # If we got a message but it's not what we want, continue waiting
                return None

            except TimeoutError:
                # Timeout occurred - websockets library raises TimeoutError
                return None
            except Exception as e:
                self.log.debug("Error receiving event: {}".format(e))
                return None

        except Exception as e:
            self.log.debug("Error receiving event: {}".format(e))
            return None
    
    def _dictionaries_match(self, pattern: dict, data: dict, required: bool) -> bool:
        """Check if two dictionaries match (helper for event matching)"""
        for key in pattern:
            if required and key not in data:
                return False
            
            if key in data:
                # Equal values, up to slashes
                if isinstance(pattern[key], dict):
                    if not self._dictionaries_match(pattern[key], data[key], required):
                        return False
                elif str(data[key]).replace('/', '') != str(pattern[key]).replace('/', ''):
                    return False
        return True
    
    def new_tab(self, url: str = "about:blank") -> 'FirefoxRemoteDebugInterface':
        """
        Create a new tab and return a FirefoxRemoteDebugInterface instance for it.
        
        Args:
            url: URL to navigate to in the new tab
            
        Returns:
            FirefoxRemoteDebugInterface instance for the new tab
        """
        try:
            # Create a new browsing context (tab)
            create_response = self._send_message({
                'method': 'browsingContext.create',
                'params': {
                    'type': 'tab',
                    'userContext': self.user_context
                }
            })
            
            # Extract the new context ID
            if create_response.get('type') == 'event' and create_response.get('method') == 'browsingContext.domContentLoaded':
                new_context = create_response['params']['context']
            elif create_response.get('type') == 'success' and 'result' in create_response and 'context' in create_response['result']:
                new_context = create_response['result']['context']
            else:
                # Listen for the domContentLoaded event
                event = self._receive_event('browsingContext.domContentLoaded', {
                    'userContext': self.user_context
                }, timeout=5)
                if event:
                    new_context = event['params']['context']
                else:
                    raise Exception("Failed to create new browsing context")
            
            # Create an interface instance for this new context
            interface = self._create_interface_for_context(new_context)
            
            # Navigate to the specified URL if provided
            if url and url != "about:blank":
                # Use the interface to navigate (this will use the correct context)
                interface.blocking_navigate_and_get_source(url, timeout=30)
            
            # Track this tab
            self.tabs[new_context] = interface
            self.tab_id_map[new_context] = {
                'context_id': new_context,
                'url': url,
                'created_at': time.time()
            }
            
            return interface
            
        except Exception as e:
            self.log.error("Failed to create new tab: {}".format(e))
            raise

    def _create_interface_for_context(self, context_id: str) -> 'FirefoxRemoteDebugInterface':
        """
        Create a new FirefoxRemoteDebugInterface instance for a specific browsing context.
        
        Args:
            context_id: The browsing context ID to associate with this interface
            
        Returns:
            FirefoxRemoteDebugInterface instance configured for the specified context
        """
        from .interface import FirefoxRemoteDebugInterface
        
        # Create a new interface instance
        interface = FirefoxRemoteDebugInterface(
            binary=self.binary,
            host=self.host,
            port=self.port,
            headless=self.headless,
            additional_options=self.additional_options,
            profile_dir=self.profile_dir
        )

        # Configure the interface for this specific context
        interface.manager = self  # Share the same execution manager
        interface.active_browsing_context = context_id

        # Note: Don't update self.browsing_context here - it belongs to the default tab
        # Each interface tracks its own context via active_browsing_context

        return interface

    def _list_browsing_contexts(self):
        """List available browsing contexts (tabs/windows) using WebDriver BiDi"""
        try:
            message = {
                "id": self.msg_id + 1,
                "method": "browsingContext.getTree",
                "params": {
                    "maxDepth": 0,
                    "root": None
                }
            }
            
            response = self._send_message(message)
            
            try:
                self.log.debug("Parsing response: {}".format(response))
                
                # Check if we have the expected structure
                if not isinstance(response, dict):
                    self.log.warning("Response is not a dict: {}".format(type(response)))
                    return []
                
                if response.get("type") != "success":
                    self.log.warning("Response type is not success: {}".format(response.get('type')))
                    return []
                
                if "result" not in response:
                    self.log.warning("Response has no 'result' field")
                    return []
                
                if "contexts" not in response["result"]:
                    self.log.warning("Response result has no 'contexts' field")
                    return []
                
                contexts = response["result"]["contexts"]
                if not isinstance(contexts, list):
                    self.log.warning("Contexts is not a list: {}".format(type(contexts)))
                    return []
                
                self.tabs = {}
                self.tab_id_map = {}
                
                for i, context in enumerate(contexts):
                    self.log.debug("Processing context {}: {}".format(i, context))
                    
                    # WebDriver BiDi doesn't have a "type" field, so we check for tab-like contexts
                    # Use .get() to safely access fields
                    if not isinstance(context, dict):
                        self.log.warning("Context {} is not a dict: {}".format(i, type(context)))
                        continue
                    
                    tab_info = {
                        "actor": context.get("context", ""),
                        "title": context.get("title", ""),
                        "url": context.get("url", ""),
                        "type": "tab"
                    }
                    
                    self.log.debug("Tab info: {}".format(tab_info))
                    
                    if tab_info["actor"]:  # Only add if we have a valid context
                        # Create an interface instance for this context
                        interface = self._create_interface_for_context(tab_info["actor"])
                        self.tabs[tab_info["actor"]] = interface
                        self.tab_id_map[tab_info["actor"]] = tab_info
                
                self.log.info("Found {} tabs".format(len(self.tabs)))
                return list(self.tabs.values())
                
            except Exception as e:
                self.log.warning("Error parsing browsing contexts: {}".format(e))
                self.log.warning("Response was: {}".format(response))
                import traceback
                self.log.warning("Traceback: {}".format(traceback.format_exc()))
                return []
                
        except Exception as e:
            self.log.warning("Failed to list browsing contexts: {}".format(e))
            return []
    
    def list_tabs(self) -> List[Dict[str, Any]]:
        """List available tabs using WebDriver BiDi"""
        if hasattr(self, 'tab_id_map') and self.tab_id_map:
            return list(self.tab_id_map.values())
        else:
            return self._list_browsing_contexts()
    
    def get_tab(self, tab_id: str) -> Dict[str, Any]:
        """Get information about a specific tab"""
        if tab_id not in self.tabs:
            # Try to find the tab
            tabs = self.list_tabs()
            for tab in tabs:
                if tab.get("actor") == tab_id:
                    self.tabs[tab_id] = tab
                    return tab
            
            raise FirefoxTabNotFoundError("Tab {} not found".format(tab_id))
        
        return self.tabs[tab_id]
    
    def navigate(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """Navigate the current browsing context to a URL using WebDriver BiDi"""
        try:
            if not self.browsing_context:
                raise FirefoxError("No browsing context available")
            
            # Navigate using WebDriver BiDi
            navigation = self._send_message({
                'method': 'browsingContext.navigate',
                'params': {
                    'url': url,
                    'context': self.browsing_context
                }
            })['result']['navigation']
            
            # Wait for the DOM to load
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Listen for domContentLoaded event
                    event = self._receive_event('browsingContext.domContentLoaded', {
                        'url': url,
                        'context': self.browsing_context,
                        'navigation': navigation,
                    })
                    
                    if event:
                        return {"status": "success", "url": url, "navigation": navigation}
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.log.debug("Event listening error: {}".format(e))
                    break
            
            return {"status": "success", "url": url, "navigation": navigation}
            
        except Exception as e:
            raise FirefoxNavigateTimedOut("Navigation to {} timed out: {}".format(url, e))

    def get_all_tab_interfaces(self) -> List['FirefoxRemoteDebugInterface']:
        """
        Get all active tab interfaces.
        
        Returns:
            List of FirefoxRemoteDebugInterface instances for all tabs
        """
        return list(self.tabs.values())

    def get_tab_interface(self, tab_id: str) -> Optional['FirefoxRemoteDebugInterface']:
        """
        Get the interface for a specific tab.
        
        Args:
            tab_id: Browsing context ID of the tab
            
        Returns:
            FirefoxRemoteDebugInterface instance or None if not found
        """
        return self.tabs.get(tab_id)

    def close_tab(self, tab_id: str) -> bool:
        """
        Close a specific tab.
        
        Args:
            tab_id: Browsing context ID of the tab to close
            
        Returns:
            True if tab was closed successfully, False otherwise
        """
        try:
            if tab_id in self.tabs:
                # Remove the tab from tracking
                del self.tabs[tab_id]
                if tab_id in self.tab_id_map:
                    del self.tab_id_map[tab_id]
                
                # If this was the active tab, switch to another tab or None
                if self.browsing_context == tab_id:
                    if self.tabs:
                        # Switch to the first remaining tab
                        first_tab = next(iter(self.tabs.keys()))
                        self.browsing_context = first_tab
                    else:
                        self.browsing_context = None
                
                # Send close command to Firefox
                self._send_message({
                    'method': 'browsingContext.close',
                    'params': {
                        'context': tab_id
                    }
                })
                
                return True
            return False
        except Exception as e:
            self.log.error("Failed to close tab {}: {}".format(tab_id, e))
            return False

    def close_all_tabs(self) -> bool:
        """
        Close all tabs.
        
        Returns:
            True if all tabs were closed successfully
        """
        try:
            # Close all tabs
            for tab_id in list(self.tabs.keys()):
                self.close_tab(tab_id)
            return True
        except Exception as e:
            self.log.error("Failed to close all tabs: {}".format(e))
            return False
    
    def close(self, sigint_timeout=20, sigkill_timeout=30):
        """
        Close connection and stop Firefox with graceful shutdown escalation.

        Args:
            sigint_timeout: Seconds to wait after SIGINT before escalating (default: 20)
            sigkill_timeout: Seconds to wait after SIGKILL before giving up (default: 30)
        """
        # Step 1: End WebSocket session properly
        try:
            if self.ws_connection:
                # End the WebDriver BiDi session properly
                try:
                    self._send_message({
                        'method': 'session.end',
                        'params': {},
                    })
                except:
                    pass
                self.ws_connection.close()
        except:
            pass

        # Step 2: Gracefully shutdown Firefox process
        if self.process and self.process.poll() is None:
            pid = self.process.pid
            self.log.info("Shutting down Firefox process (PID: {})".format(pid))

            # Try SIGINT (Ctrl+C) first for graceful shutdown
            try:
                self.log.info("Sending SIGINT to Firefox process...")
                os.kill(pid, signal.SIGINT)

                # Wait for process to terminate gracefully
                try:
                    self.process.wait(timeout=sigint_timeout)
                    self.log.info("Firefox terminated gracefully after SIGINT")
                except subprocess.TimeoutExpired:
                    # Process didn't terminate, escalate to SIGKILL
                    self.log.warning("Firefox did not respond to SIGINT after {} seconds, escalating to SIGKILL...".format(sigint_timeout))

                    try:
                        os.kill(pid, signal.SIGKILL)
                        self.log.info("Sent SIGKILL to Firefox process")

                        # Wait for process to die after SIGKILL
                        try:
                            self.process.wait(timeout=sigkill_timeout)
                            self.log.info("Firefox killed with SIGKILL")
                        except subprocess.TimeoutExpired:
                            self.log.error("Firefox did not terminate even after SIGKILL (waited {} seconds)".format(sigkill_timeout))

                    except ProcessLookupError:
                        self.log.info("Firefox process already terminated")
                    except Exception as e:
                        self.log.error("Error sending SIGKILL: {}".format(e))

            except ProcessLookupError:
                self.log.info("Firefox process already terminated")
            except Exception as e:
                self.log.error("Error during Firefox shutdown: {}".format(e))
                # Try the old method as fallback
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except:
                    try:
                        self.process.kill()
                    except:
                        pass

        # Clean up temporary profile
        try:
            if self.temp_profile and os.path.exists(self.temp_profile):
                shutil.rmtree(self.temp_profile)
                self.log.debug("Cleaned up temporary profile: {}".format(self.temp_profile))
        except:
            pass

        # Clear all state
        self.ws_connection = None
        self.process = None
        self.tabs = {}
        self.tab_id_map = {}
        self.browsing_context = None
        self.user_context = None
        self.temp_profile = None
    
    def __enter__(self):
        """Context manager entry"""
        self.start_firefox()
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()