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