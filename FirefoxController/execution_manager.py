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
import tempfile
import os
import os.path
import shutil
import base64
import queue
import threading
import urllib.request
import signal
import sys
import re
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse

IS_WINDOWS = sys.platform == 'win32'
IS_LINUX = sys.platform.startswith('linux')

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
                 port: Optional[int] = None,
                 websocket_timeout: int = 10,
                 headless: bool = False,
                 additional_options: List[str] = None,
                 profile_dir: str = None):
        """
        Initialize Firefox execution manager.

        Args:
            binary: Path to Firefox binary
            host: Host to connect to
            port: Debug port to use (None for automatic selection, or specify e.g. 9222)
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

        # Track global console event subscription (shared across all tabs)
        self.console_events_subscribed = False
        self.console_logging_refs = 0  # Count of tabs with console logging enabled
        self.console_subscription_lock = threading.Lock()

        # Track which contexts have console logging enabled
        self.console_enabled_contexts = set()
        self.console_contexts_lock = threading.Lock()

        # Track interface instances with console logging enabled
        self._console_interfaces = []  # List of interface instances
        self._console_interfaces_lock = threading.Lock()

        # Per-tab console event queues for log.entryAdded events
        self.console_queues = {}  # context_id -> queue.Queue()
        self.console_queues_lock = threading.Lock()
        
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

    def _create_user_js(self, profile_path: str):
        """
        Create user.js file with cookie persistence preferences.

        user.js takes precedence over prefs.js and Firefox doesn't modify it,
        making it perfect for enforcing cookie persistence settings.

        Args:
            profile_path: Path to the Firefox profile directory
        """
        user_js_file = os.path.join(profile_path, "user.js")

        # Create user.js with cookie persistence preferences
        # These override any prefs.js settings and aren't modified by Firefox
        user_js_content = """// Cookie persistence settings (enforced by FirefoxController)
// These settings prevent Firefox from clearing cookies on shutdown

// CRITICAL: Disable the master sanitization toggle
user_pref("privacy.sanitize.sanitizeOnShutdown", false);
user_pref("privacy.sanitize.sanitizeOnShutdown.v2", false);

// Disable clearing individual data types on shutdown (old preferences)
user_pref("privacy.clearOnShutdown.cookies", false);
user_pref("privacy.clearOnShutdown.cache", false);
user_pref("privacy.clearOnShutdown.offlineApps", false);
user_pref("privacy.clearOnShutdown.sessions", false);
user_pref("privacy.clearOnShutdown.formdata", false);
user_pref("privacy.clearOnShutdown.history", false);
user_pref("privacy.clearOnShutdown.siteSettings", false);
user_pref("privacy.clearOnShutdown.downloads", false);
user_pref("privacy.clearOnShutdown.openWindows", false);

// Disable clearing individual data types on shutdown (v2 preferences for newer Firefox)
// These are the primary preferences used by modern Firefox versions
user_pref("privacy.sanitize.sanitizeOnShutdown.v2", false);
user_pref("privacy.clearOnShutdown_v2.cookiesAndStorage", false);
user_pref("privacy.clearOnShutdown_v2.cache", false);
user_pref("privacy.clearOnShutdown_v2.formdata", false);
user_pref("privacy.clearOnShutdown_v2.historyFormDataAndDownloads", false);
user_pref("privacy.clearOnShutdown_v2.siteSettings", false);
user_pref("privacy.clearOnShutdown_v2.downloads", false);
user_pref("privacy.clearOnShutdown_v2.sessions", false);

// Disable sanitization completely
user_pref("privacy.sanitize.pending", "[]");
user_pref("privacy.sanitize.timeSpan", 0);

// Prevent Firefox from deleting cookies on shutdown (WebDriver-specific fix)
user_pref("network.cookie.lifetimePolicy", 0);  // 0 = keep cookies until they expire
user_pref("places.history.enabled", true);  // Enable history to prevent cookie clearing

// Disable remote debugging recommended preferences that might clear cookies
user_pref("remote.prefs.recommended.applied", false);

// Ensure cookies are saved to disk immediately
user_pref("network.cookie.cookieBehavior", 0);  // Accept all cookies
user_pref("browser.privatebrowsing.autostart", false);  // Disable private browsing
user_pref("browser.cache.disk.enable", true);  // Enable disk cache
user_pref("browser.cache.memory.enable", true);  // Enable memory cache
"""

        with open(user_js_file, 'w') as f:
            f.write(user_js_content)

        self.log.info("Created user.js with cookie persistence settings")

    def _ensure_cookie_persistence(self, profile_path: str):
        """
        Ensure privacy preferences don't clear cookies on shutdown.

        This method checks the Firefox profile's prefs.js file for problematic
        privacy preferences that would clear cookies on browser shutdown, and
        corrects them if needed.

        Args:
            profile_path: Path to the Firefox profile directory
        """
        prefs_file = os.path.join(profile_path, "prefs.js")

        # Preferences that should be set to preserve cookies
        # Include both old and new (v2) preference names for compatibility
        required_prefs = {
            "privacy.sanitize.sanitizeOnShutdown": "false",
            "privacy.clearOnShutdown.cookies": "false",
            "privacy.clearOnShutdown.cache": "false",
            "privacy.clearOnShutdown.offlineApps": "false",
            "privacy.clearOnShutdown.sessions": "false",
            "privacy.clearOnShutdown.formdata": "false",
            "privacy.clearOnShutdown.history": "false",
            # Version 2 preferences (newer Firefox versions - these are the primary ones)
            "privacy.sanitize.sanitizeOnShutdown.v2": "false",
            "privacy.clearOnShutdown_v2.cookiesAndStorage": "false",
            "privacy.clearOnShutdown_v2.cache": "false",
            "privacy.clearOnShutdown_v2.formdata": "false",
            "privacy.clearOnShutdown_v2.historyFormDataAndDownloads": "false",
            "privacy.clearOnShutdown_v2.siteSettings": "false",
            "privacy.clearOnShutdown_v2.downloads": "false",
            "privacy.clearOnShutdown_v2.sessions": "false",
        }

        # Read existing prefs if file exists
        if os.path.exists(prefs_file):
            with open(prefs_file, 'r') as f:
                content = f.read()

            # Check which prefs need to be added/fixed
            prefs_to_add = []
            for pref_name, pref_value in required_prefs.items():
                # Use regex to check if preference exists and what its value is
                pattern = r'user_pref\("{0}",\s*(true|false)\);'.format(re.escape(pref_name))
                match = re.search(pattern, content)

                if not match or match.group(1) != pref_value:
                    prefs_to_add.append('user_pref("{0}", {1});'.format(pref_name, pref_value))

            # Append missing/incorrect preferences
            if prefs_to_add:
                with open(prefs_file, 'a') as f:
                    f.write('\n// Cookie persistence settings (added by FirefoxController)\n')
                    for pref_line in prefs_to_add:
                        f.write(pref_line + '\n')
                self.log.info("Updated {} privacy preferences to preserve cookies".format(len(prefs_to_add)))

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

// Prevent clearing cookies and other data on shutdown
user_pref("privacy.sanitize.sanitizeOnShutdown", false);
user_pref("privacy.clearOnShutdown.cookies", false);
user_pref("privacy.clearOnShutdown.cache", false);
user_pref("privacy.clearOnShutdown.offlineApps", false);
user_pref("privacy.clearOnShutdown.sessions", false);
user_pref("privacy.clearOnShutdown.formdata", false);
user_pref("privacy.clearOnShutdown.history", false);
// Version 2 preferences for newer Firefox versions
user_pref("privacy.clearOnShutdown_v2.cookiesAndStorage", false);
user_pref("privacy.clearOnShutdown_v2.cache", false);
user_pref("privacy.clearOnShutdown_v2.formdata", false);
user_pref("privacy.clearOnShutdown_v2.historyFormDataAndDownloads", false);
""".format(self.port)
            with open(prefs_file, "w") as f:
                f.write(prefs_content)
            self.log.info("Created new prefs.js in profile")
        else:
            self.log.debug("Using existing prefs.js (user customizations preserved)")

        # Create user.js for cookie persistence (overrides prefs.js and isn't modified by Firefox)
        self._create_user_js(profile_path)

        # Also ensure cookie persistence preferences are set correctly in prefs.js
        self._ensure_cookie_persistence(profile_path)

        return profile_path
    
    def _find_firefox_binary(self) -> str:
        """
        Find the Firefox binary, checking platform-specific locations.

        Returns:
            Path to the Firefox binary

        Raises:
            FirefoxStartupException: If Firefox binary is not found
        """
        # First check if the configured binary is directly usable
        found = shutil.which(self.binary)
        if found:
            return found

        # Platform-specific fallback search
        if IS_WINDOWS:
            windows_paths = [
                os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Mozilla Firefox", "firefox.exe"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Mozilla Firefox", "firefox.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Mozilla Firefox", "firefox.exe"),
            ]
            for path in windows_paths:
                if os.path.isfile(path):
                    return path
        elif IS_LINUX:
            # On Linux, shutil.which should have found it if it's in PATH
            pass
        else:
            raise FirefoxStartupException("Unsupported platform: {}".format(sys.platform))

        raise FirefoxStartupException("Firefox binary not found: {}".format(self.binary))

    # Minimum Firefox version (network.addDataCollector added in 143)
    MINIMUM_FIREFOX_VERSION = 143

    def _get_firefox_version(self, firefox_path: str) -> Optional[int]:
        """
        Get the major version number of the Firefox binary.

        Args:
            firefox_path: Path to the Firefox binary

        Returns:
            Major version as int, or None if version could not be determined
        """
        try:
            result = subprocess.run(
                [firefox_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            # Output format: "Mozilla Firefox 148.0" or "Mozilla Firefox 140.7.1esr"
            match = re.search(r'Mozilla Firefox (\d+)\.', result.stdout)
            if match:
                return int(match.group(1))
        except Exception as e:
            self.log.debug("Could not determine Firefox version: {}".format(e))
        return None

    def start_firefox(self):
        """Start Firefox with remote debugging enabled"""
        firefox_path = self._find_firefox_binary()

        # Check Firefox version
        version = self._get_firefox_version(firefox_path)
        if version is not None:
            self.log.info("Detected Firefox version: {}".format(version))
            if version < self.MINIMUM_FIREFOX_VERSION:
                raise FirefoxStartupException(
                    "Firefox {} is too old. Minimum supported version is {}. "
                    "Please update Firefox.".format(version, self.MINIMUM_FIREFOX_VERSION))
        else:
            self.log.warning("Could not determine Firefox version. Proceeding anyway.")

        # Create profile if needed
        profile_path = self._create_profile()

        # Build command line
        cmd = [firefox_path]

        if self.headless:
            cmd.extend(["--headless"])

        # Use the profile
        cmd.extend(["--profile", profile_path])

        # Enable WebDriver BiDi (the modern standard)
        cmd.extend([
            "--remote-allow-system-access",
            "--remote-debugging-port", str(self.port),  # Start the Firefox Remote Agent
            "--remote-allow-hosts", "localhost,127.0.0.1",  # Allow local connections
            "--remote-allow-origins", "http://localhost,http://127.0.0.1",  # Allow local origins
        ])

        # Add additional options
        cmd.extend(self.additional_options)

        self.log.info("Starting Firefox with command: {}".format(' '.join(cmd)))
        self.log.info("Using profile: {}".format(profile_path))

        try:
            popen_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
            }

            if IS_WINDOWS:
                # On Windows, use CREATE_NEW_PROCESS_GROUP so we can terminate cleanly
                popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
            elif IS_LINUX:
                # On Linux, use preexec_fn to kill child when parent dies
                popen_kwargs['preexec_fn'] = self._set_pdeathsig
            else:
                raise FirefoxStartupException("Unsupported platform: {}".format(sys.platform))

            self.process = subprocess.Popen(cmd, **popen_kwargs)

            if IS_WINDOWS:
                self._assign_to_job_object()

            # Give Firefox more time to start
            time.sleep(4)

            # Check if process is still running
            if self.process.poll() is not None:
                stderr = self.process.stderr.read().decode('utf-8') if self.process.stderr else ""
                raise FirefoxStartupException("Firefox failed to start: {}".format(stderr))

        except FirefoxStartupException:
            raise
        except Exception as e:
            raise FirefoxStartupException("Failed to start Firefox: {}".format(e))
    
    def _set_pdeathsig(self):
        """Set parent death signal to ensure Firefox dies when parent dies (Linux only).

        This is only called as a preexec_fn on Linux, never on Windows.
        """
        try:
            import ctypes
            PR_SET_PDEATHSIG = 1
            libc = ctypes.CDLL("libc.so.6")
            libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
        except Exception:
            pass  # Not critical if this fails

    def _assign_to_job_object(self):
        """Assign Firefox to a Job Object so it dies when the parent process exits (Windows only).

        This is the Windows equivalent of Linux's prctl(PR_SET_PDEATHSIG).
        When the parent process exits (even via crash/kill), all handles are closed,
        which causes the job object to terminate all child processes.
        """
        if not self.process or not isinstance(self.process.pid, int):
            return

        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            # Job object constants
            JobObjectExtendedLimitInformation = 9
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
            PROCESS_SET_QUOTA = 0x0100
            PROCESS_TERMINATE = 0x0001

            class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ('PerProcessUserTimeLimit', ctypes.c_int64),
                    ('PerJobUserTimeLimit', ctypes.c_int64),
                    ('LimitFlags', wintypes.DWORD),
                    ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t),
                    ('ActiveProcessLimit', wintypes.DWORD),
                    ('Affinity', ctypes.POINTER(ctypes.c_ulong)),
                    ('PriorityClass', wintypes.DWORD),
                    ('SchedulingClass', wintypes.DWORD),
                ]

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('ReadOperationCount', ctypes.c_uint64),
                    ('WriteOperationCount', ctypes.c_uint64),
                    ('OtherOperationCount', ctypes.c_uint64),
                    ('ReadTransferCount', ctypes.c_uint64),
                    ('WriteTransferCount', ctypes.c_uint64),
                    ('OtherTransferCount', ctypes.c_uint64),
                ]

            class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ('IoInfo', IO_COUNTERS),
                    ('ProcessMemoryLimit', ctypes.c_size_t),
                    ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryUsed', ctypes.c_size_t),
                    ('PeakJobMemoryUsed', ctypes.c_size_t),
                ]

            # Create an anonymous job object
            job = kernel32.CreateJobObjectW(None, None)
            if not job:
                self.log.debug("Failed to create job object: error {}".format(
                    ctypes.get_last_error()))
                return

            # Configure job to kill children when job handle is closed
            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

            if not kernel32.SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info)
            ):
                self.log.debug("Failed to set job object info: error {}".format(
                    ctypes.get_last_error()))
                kernel32.CloseHandle(job)
                return

            # Assign Firefox process to the job
            process_handle = kernel32.OpenProcess(
                PROCESS_SET_QUOTA | PROCESS_TERMINATE,
                False,
                self.process.pid
            )
            if not process_handle:
                self.log.debug("Failed to open Firefox process: error {}".format(
                    ctypes.get_last_error()))
                kernel32.CloseHandle(job)
                return

            if not kernel32.AssignProcessToJobObject(job, process_handle):
                self.log.debug("Failed to assign process to job: error {}".format(
                    ctypes.get_last_error()))
                kernel32.CloseHandle(process_handle)
                kernel32.CloseHandle(job)
                return

            kernel32.CloseHandle(process_handle)

            # Store the job handle so it stays alive as long as this manager lives.
            # When this object is garbage-collected or the process exits, the handle
            # is closed and Windows kills all processes in the job.
            self._job_handle = job
            self.log.debug("Assigned Firefox to job object (kill-on-close enabled)")

        except Exception as e:
            self.log.debug("Failed to set up job object: {}".format(e))
    
    def connect(self):
        """Connect to Firefox remote debugging interface using WebDriver BiDi"""
        if not self.process or self.process.poll() is not None:
            raise FirefoxConnectFailure("Firefox process is not running")

        if not WEBSOCKETS_AVAILABLE:
            raise FirefoxConnectFailure("websockets library not available. Please install with: pip install websockets")

        # WebDriver BiDi uses a session-based WebSocket URL
        ws_url = "ws://127.0.0.1:{}/session".format(self.port)

        # Retry connection - Firefox may take varying time to start across platforms
        max_retries = 10
        retry_delay = 1.0
        last_error = None

        for attempt in range(max_retries):
            # Check that Firefox is still alive before each attempt
            if self.process.poll() is not None:
                stderr = self.process.stderr.read().decode('utf-8') if self.process.stderr else ""
                raise FirefoxConnectFailure("Firefox process died during connection. stderr: {}".format(stderr))

            try:
                self.log.info("Connecting to WebDriver BiDi WebSocket (attempt {}/{}): {}".format(
                    attempt + 1, max_retries, ws_url))

                self.ws_connection = connect(ws_url, max_size=64 * 1024 * 1024)

                # Initialize the WebDriver BiDi connection
                self._initialize_bidi_connection()
                return  # Success

            except Exception as e:
                last_error = e

                # If a stale session is blocking us, try to end it
                if "Maximum number of active sessions" in str(e) and self.ws_connection:
                    self.log.warning("Stale BiDi session detected, sending session.end...")
                    try:
                        self._send_message({'method': 'session.end', 'params': {}})
                        self.log.info("Stale session ended successfully")
                    except Exception as end_err:
                        self.log.debug("session.end failed (expected): {}".format(end_err))
                    try:
                        self.ws_connection.close()
                    except Exception:
                        pass
                    self.ws_connection = None

                if attempt < max_retries - 1:
                    self.log.debug("Connection attempt {} failed: {}. Retrying in {}s...".format(
                        attempt + 1, e, retry_delay))
                    time.sleep(retry_delay)
                else:
                    self.log.error("All {} connection attempts failed".format(max_retries))

        raise FirefoxConnectFailure("Connection failed after {} attempts. Last error: {}".format(
            max_retries, last_error))
    
    def _initialize_bidi_connection(self):
        """Initialize WebDriver BiDi connection (based on working implementation)"""
        try:
            # Initiate the session
            session_response = self._send_message({
                'method': 'session.new',
                'params': {
                    'capabilities': {}
                }
            })
            session_id = session_response['result']['sessionId']

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

            # Use default user context instead of creating a new one
            # This allows cookies to persist across browser restarts
            self.user_context = 'default'

            # Create browsing context and handle the event response
            create_response = self._send_message({
                'method': 'browsingContext.create',
                'params': {
                    'type': 'tab'
                }
            })

            self.log.debug("browsingContext.create response: {}".format(create_response))

            # Extract context ID from response - try multiple response formats
            context_id = None

            # Format 1: success response with result.context
            if create_response.get('type') == 'success' and 'result' in create_response:
                context_id = create_response['result'].get('context')

            # Format 2: domContentLoaded event (sometimes arrives instead of direct response)
            if not context_id and create_response.get('type') == 'event':
                if create_response.get('method') == 'browsingContext.domContentLoaded':
                    context_id = create_response.get('params', {}).get('context')

            # Format 3: wait for domContentLoaded event if we haven't got context yet
            if not context_id:
                self.log.debug("Context not found in create response, waiting for domContentLoaded event...")
                event = self._receive_event('browsingContext.domContentLoaded', {}, timeout=10)
                if event:
                    context_id = event.get('params', {}).get('context')

            # Format 4: fall back to getTree to discover existing contexts
            if not context_id:
                self.log.debug("Still no context, querying browsingContext.getTree...")
                tree_response = self._send_message({
                    'method': 'browsingContext.getTree',
                    'params': {'maxDepth': 0}
                })
                contexts = tree_response.get('result', {}).get('contexts', [])
                if contexts:
                    context_id = contexts[0].get('context')
                    self.log.debug("Found context from getTree: {}".format(context_id))

            if not context_id:
                raise FirefoxCommunicationsError(
                    "Failed to create browsing context. "
                    "create response: {}".format(create_response))

            self.browsing_context = context_id
            self.log.info("Created browsing context: {}".format(self.browsing_context))

            # Get the list of browsing contexts (tabs/windows)
            self._list_browsing_contexts()

        except FirefoxCommunicationsError:
            raise
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
                        method = response.get("method", "")
                        params = response.get("params", {})
                        context_id = None

                        # For log.entryAdded events, context is nested in source.context
                        if method == "log.entryAdded":
                            source = params.get("source", {})
                            if isinstance(source, dict):
                                context_id = source.get("context")

                            # Route to console queue
                            if context_id:
                                console_queue = self.get_console_queue_for_context(context_id)
                                console_queue.put(response)
                            else:
                                # Log event without context - route to all contexts with console logging enabled
                                with self.console_contexts_lock:
                                    for ctx in self.console_enabled_contexts:
                                        console_queue = self.get_console_queue_for_context(ctx)
                                        console_queue.put(response)
                        else:
                            # For other events, context is directly in params
                            if "context" in params:
                                context_id = params["context"]

                            if context_id:
                                event_queue = self.get_event_queue_for_context(context_id)
                                event_queue.put(response)
                        # Continue waiting for our response
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

    def get_console_queue_for_context(self, context_id: str) -> queue.Queue:
        """Get or create the console event queue for a specific browsing context."""
        with self.console_queues_lock:
            if context_id not in self.console_queues:
                self.console_queues[context_id] = queue.Queue()
            return self.console_queues[context_id]

    def poll_for_events(self, timeout: float = 0.1) -> int:
        """
        Poll WebSocket for events without sending a message (thread-safe).

        This reads from the WebSocket and distributes events to per-tab queues.
        Useful for capturing async events like network.responseCompleted and log.entryAdded.

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
                            method = response.get("method", "")

                            # Extract the context from the event if available
                            context_id = None
                            params = response.get("params", {})

                            # For log.entryAdded events, context is nested in source.context
                            if method == "log.entryAdded":
                                source = params.get("source", {})
                                if isinstance(source, dict):
                                    context_id = source.get("context")

                                # Route to console queue
                                if context_id:
                                    console_queue = self.get_console_queue_for_context(context_id)
                                    console_queue.put(response)
                                    events_received += 1
                                    self.log.debug("Routed log.entryAdded to console queue for context: {}".format(context_id))
                                else:
                                    # Log event without context - route to all contexts with console logging enabled
                                    with self.console_contexts_lock:
                                        for ctx in self.console_enabled_contexts:
                                            console_queue = self.get_console_queue_for_context(ctx)
                                            console_queue.put(response)
                                            events_received += 1
                                    self.log.debug("Routed log.entryAdded to all console-enabled contexts")
                            else:
                                # For other events, context is directly in params
                                if "context" in params:
                                    context_id = params["context"]

                                # If we have a context, queue it for that specific tab
                                if context_id:
                                    event_queue = self.get_event_queue_for_context(context_id)
                                    event_queue.put(response)
                                    events_received += 1
                                else:
                                    # No context - this is a global event, queue for all tabs
                                    # or just log and ignore
                                    self.log.debug("Received event without context: {}".format(method))
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
                    'type': 'tab'
                    # Use default user context for cookie persistence
                }
            })

            # Extract the new context ID
            if create_response.get('type') == 'event' and create_response.get('method') == 'browsingContext.domContentLoaded':
                new_context = create_response['params']['context']
            elif create_response.get('type') == 'success' and 'result' in create_response and 'context' in create_response['result']:
                new_context = create_response['result']['context']
            else:
                # Listen for the domContentLoaded event
                event = self._receive_event('browsingContext.domContentLoaded', {}, timeout=5)
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
        
        # Create a new interface instance sharing this manager (no new Firefox)
        interface = FirefoxRemoteDebugInterface(manager=self)
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
    
    def close(self, graceful_timeout=20, kill_timeout=30):
        """
        Close connection and stop Firefox with graceful shutdown escalation.

        Args:
            graceful_timeout: Seconds to wait after graceful termination before escalating (default: 20)
            kill_timeout: Seconds to wait after forceful kill before giving up (default: 30)
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
                except Exception:
                    pass
                self.ws_connection.close()
        except Exception:
            pass

        # Step 2: Gracefully shutdown Firefox process
        if self.process and self.process.poll() is None:
            pid = self.process.pid
            self.log.info("Shutting down Firefox process (PID: {})".format(pid))

            if IS_WINDOWS:
                # On Windows, use process.terminate() (calls TerminateProcess)
                # There is no graceful SIGINT equivalent that works reliably
                try:
                    self.log.info("Terminating Firefox process...")
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=graceful_timeout)
                        self.log.info("Firefox terminated gracefully")
                    except subprocess.TimeoutExpired:
                        self.log.warning("Firefox did not respond to terminate after {} seconds, killing...".format(graceful_timeout))
                        try:
                            self.process.kill()
                            self.process.wait(timeout=kill_timeout)
                            self.log.info("Firefox killed forcefully")
                        except subprocess.TimeoutExpired:
                            self.log.error("Firefox did not terminate even after kill (waited {} seconds)".format(kill_timeout))
                        except Exception as e:
                            self.log.error("Error killing Firefox: {}".format(e))
                except Exception as e:
                    self.log.error("Error during Firefox shutdown: {}".format(e))
            elif IS_LINUX:
                # On Linux, try SIGINT first for graceful shutdown
                try:
                    self.log.info("Sending SIGINT to Firefox process...")
                    os.kill(pid, signal.SIGINT)

                    # Wait for process to terminate gracefully
                    try:
                        self.process.wait(timeout=graceful_timeout)
                        self.log.info("Firefox terminated gracefully after SIGINT")
                    except subprocess.TimeoutExpired:
                        # Process didn't terminate, escalate to SIGKILL
                        self.log.warning("Firefox did not respond to SIGINT after {} seconds, escalating to SIGKILL...".format(graceful_timeout))

                        try:
                            os.kill(pid, signal.SIGKILL)
                            self.log.info("Sent SIGKILL to Firefox process")

                            # Wait for process to die after SIGKILL
                            try:
                                self.process.wait(timeout=kill_timeout)
                                self.log.info("Firefox killed with SIGKILL")
                            except subprocess.TimeoutExpired:
                                self.log.error("Firefox did not terminate even after SIGKILL (waited {} seconds)".format(kill_timeout))

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
                    except Exception:
                        try:
                            self.process.kill()
                        except Exception:
                            pass
            else:
                self.log.error("Unsupported platform: {}".format(sys.platform))
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except Exception:
                    try:
                        self.process.kill()
                    except Exception:
                        pass

        # Clean up temporary profile
        try:
            if self.temp_profile and os.path.exists(self.temp_profile):
                shutil.rmtree(self.temp_profile)
                self.log.debug("Cleaned up temporary profile: {}".format(self.temp_profile))
        except Exception:
            pass

        # Close job object handle (Windows)
        if hasattr(self, '_job_handle') and self._job_handle:
            try:
                import ctypes
                ctypes.WinDLL('kernel32').CloseHandle(self._job_handle)
            except Exception:
                pass
            self._job_handle = None

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
        try:
            self.connect()
        except Exception:
            # If connect fails, Firefox is running but we'll never enter
            # the with-block, so __exit__ won't be called. Clean up now.
            self.close()
            raise
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()