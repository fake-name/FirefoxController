#!/usr/bin/env python3

"""
Simple import test for FirefoxController

This script tests that all modules can be imported correctly.
"""

import pytest

def test_main_package_import():
    """Test that the main FirefoxController package can be imported"""
    import FirefoxController
    assert FirefoxController is not None

def test_firefox_remote_debug_interface_import():
    """Test that FirefoxRemoteDebugInterface can be imported"""
    from FirefoxController import FirefoxRemoteDebugInterface
    assert FirefoxRemoteDebugInterface is not None

def test_firefox_execution_manager_import():
    """Test that FirefoxExecutionManager can be imported"""
    from FirefoxController import FirefoxExecutionManager
    assert FirefoxExecutionManager is not None

def test_exceptions_import():
    """Test that all exceptions can be imported"""
    from FirefoxController import (
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
    assert FirefoxControllerException is not None
    assert FirefoxStartupException is not None
    assert FirefoxConnectFailure is not None
    assert FirefoxCommunicationsError is not None
    assert FirefoxTabNotFoundError is not None
    assert FirefoxError is not None
    assert FirefoxDiedError is not None
    assert FirefoxNavigateTimedOut is not None
    assert FirefoxResponseNotReceived is not None

def test_utility_functions_import():
    """Test that utility functions can be imported"""
    from FirefoxController import setup_logging, main
    assert setup_logging is not None
    assert main is not None

def test_interface_methods():
    """Test that the interface has all expected methods"""
    from FirefoxController import FirefoxRemoteDebugInterface

    interface = FirefoxRemoteDebugInterface
    expected_methods = [
        'blocking_navigate_and_get_source',
        'get_page_source',
        'get_current_url',
        'get_page_url_title',
        'take_screenshot',
        'execute_javascript_statement',
        'execute_javascript_function',
        'navigate_to',
        'blocking_navigate',
        'get_cookies',
        'set_cookie',
        'clear_cookies',
        'find_element',
        'click_element',
        'click_link_containing_url',
        'scroll_page',
        'get_rendered_page_source',
        'wait_for_dom_idle',
        'new_tab',
        # XHR fetch (ChromeController parity)
        'xhr_fetch',
        # XPath element selection (ChromeController parity)
        'get_element_by_xpath',
        'get_elements_by_xpath',
        'select_input_by_xpath',
        'click_element_by_xpath',
        'get_input_value_by_xpath',
        'set_input_value_by_xpath',
        # Keyboard event methods (ChromeController parity)
        'dispatch_key_event',
        'type_text',
        'type_text_in_input',
        'send_key_combination',
        'press_enter',
        'press_tab',
        'press_escape',
        # Mouse event methods (ChromeController parity)
        'get_element_coordinates_by_xpath',
        'get_element_coordinates',
        'move_mouse_to',
        'move_mouse_to_element_by_xpath',
        'move_mouse_to_element',
        'mouse_click',
        'mouse_click_element_by_xpath',
        'mouse_click_element',
        'mouse_double_click',
        'mouse_double_click_element_by_xpath',
        'mouse_right_click_element_by_xpath',
        'mouse_drag',
        'mouse_drag_element_by_xpath',
        'hover_element_by_xpath',
    ]

    for method in expected_methods:
        assert hasattr(interface, method), "Method {} missing from FirefoxRemoteDebugInterface".format(method)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])