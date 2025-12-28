#!/usr/bin/env python3

"""
FirefoxController - Main package initialization

This package provides a Python interface to control Firefox using its remote debugging protocol.
"""

# Patch Firefox's libxul.so on import to make WebDriver undetectable
from .webdriver_patch import WebDriverPatchError, check_and_raise_if_needed
# check_and_raise_if_needed()

from .interface import FirefoxRemoteDebugInterface
from .execution_manager import FirefoxExecutionManager
from .exceptions import (
    FirefoxControllerException,
    FirefoxStartupException,
    FirefoxConnectFailure,
    FirefoxCommunicationsError,
    FirefoxTabNotFoundError,
    FirefoxError,
    FirefoxDiedError,
    FirefoxNavigateTimedOut,
    FirefoxResponseNotReceived
)

# Main exports
__all__ = [
    'FirefoxRemoteDebugInterface',
    'FirefoxExecutionManager',
    'FirefoxControllerException',
    'FirefoxStartupException',
    'FirefoxConnectFailure',
    'FirefoxCommunicationsError',
    'FirefoxTabNotFoundError',
    'FirefoxError',
    'FirefoxDiedError',
    'FirefoxNavigateTimedOut',
    'FirefoxResponseNotReceived',
    'WebDriverPatchError',
    'setup_logging',
    'main'
]

# Import utility functions from the original firefox_controller.py
from .utils import setup_logging, main