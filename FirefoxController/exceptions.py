#!/usr/bin/env python3

"""
FirefoxController Exceptions

This module contains all custom exceptions for FirefoxController.
"""


class FirefoxControllerException(Exception):
    """Base exception for FirefoxController errors"""
    pass


class FirefoxStartupException(FirefoxControllerException):
    """Exception raised when Firefox fails to start"""
    pass


class FirefoxConnectFailure(FirefoxControllerException):
    """Exception raised when connection to Firefox fails"""
    pass


class FirefoxCommunicationsError(FirefoxControllerException):
    """Exception raised when communication with Firefox fails"""
    pass


class FirefoxTabNotFoundError(FirefoxControllerException):
    """Exception raised when a tab is not found"""
    pass


class FirefoxError(FirefoxControllerException):
    """General Firefox error"""
    pass


class FirefoxDiedError(FirefoxControllerException):
    """Exception raised when Firefox process dies"""
    pass


class FirefoxNavigateTimedOut(FirefoxControllerException):
    """Exception raised when navigation times out"""
    pass


class FirefoxResponseNotReceived(FirefoxControllerException):
    """Exception raised when expected response is not received"""
    pass


# Browser operation exceptions for higher-level operations
class BrowserOperationError(FirefoxControllerException):
    """Base exception for all browser operation failures"""
    pass


class BrowserTimeoutError(BrowserOperationError):
    """Raised when a browser operation times out"""
    pass


class BrowserNavigationError(BrowserOperationError):
    """Raised when browser navigation fails"""
    pass


class BrowserContentError(BrowserOperationError):
    """Raised when browser content retrieval fails"""
    pass


class BrowserDownloadError(BrowserOperationError):
    """Raised when browser file download fails"""
    pass