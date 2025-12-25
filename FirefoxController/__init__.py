"""
FirefoxController - Python interface for Firefox Remote Debugging Protocol

This package provides a Python wrapper for controlling Firefox using its remote
debugging interface, similar to ChromeController for Chrome/Chromium.
"""

from .firefox_controller import (
    FirefoxControllerException,
    FirefoxStartupException, 
    FirefoxConnectFailure,
    FirefoxCommunicationsError,
    FirefoxTabNotFoundError,
    FirefoxError,
    FirefoxDiedError,
    FirefoxNavigateTimedOut,
    FirefoxResponseNotReceived,
    FirefoxExecutionManager,
    FirefoxRemoteDebugInterface,
    setup_logging
)

__version__ = "0.1.0"
__author__ = "FirefoxController"
__license__ = "BSD"