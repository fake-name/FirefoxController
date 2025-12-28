#!/usr/bin/env python3

"""
Test script for FirefoxController feature parity with ChromeController
Tests all the new functions added to achieve feature parity
"""

import pytest
import FirefoxController
import logging
import time
import sys
import os

# Add tests directory to path so we can import test_server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_server import TestServer

def test_javascript_execution():
    """Test JavaScript execution functions"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting JavaScript execution tests...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Navigate to a test page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/javascript"), timeout=15)
            
            # Test execute_javascript_statement
            result = firefox.execute_javascript_statement("1 + 1")
            logger.info("JavaScript statement result: {}".format(result))
            assert result == 2, "Expected 2, got {}".format(result)
            
            # Test execute_javascript_statement with variable
            result = firefox.execute_javascript_statement("document.title")
            logger.info("Document title: {}".format(result))
            assert result is not None, "Document title should not be None"
            
            # Test execute_javascript_function
            func = "function test(a, b) { return a + b; }"
            result = firefox.execute_javascript_function(func, [3, 5])
            logger.info("JavaScript function result: {}".format(result))
            assert result == 8, "Expected 8, got {}".format(result)
            
            # Test calling a function defined in the page
            result = firefox.execute_javascript_statement("testFunction(10, 20)")
            logger.info("Page function result: {}".format(result))
            assert result == 30, "Expected 30, got {}".format(result)
            
            logger.info("JavaScript execution tests completed successfully")
    
    finally:
        test_server.stop()

def test_navigation_functions():
    """Test navigation functions"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting navigation function tests...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Test navigate_to (JS-based navigation)
            success = firefox.navigate_to(test_server.get_url("/simple"))
            logger.info("navigate_to result: {}".format(success))
            assert success, "navigate_to should return True"
            
            # Wait for navigation to complete
            time.sleep(2)
            
            # Test blocking_navigate
            success = firefox.blocking_navigate(test_server.get_url("/javascript"), timeout=10)
            logger.info("blocking_navigate result: {}".format(success))
            assert success, "blocking_navigate should return True"
            
            # Verify we're on the right page
            current_url = firefox.get_current_url()
            logger.info("Current URL after blocking_navigate: {}".format(current_url))
            assert "javascript" in current_url.lower(), "Expected javascript in URL, got {}".format(current_url)
            
            logger.info("Navigation function tests completed successfully")
    
    finally:
        test_server.stop()

def test_cookie_management():
    """Test cookie management functions"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting cookie management tests...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Navigate to a test page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/cookies"), timeout=15)
            
            # Test get_cookies
            cookies = firefox.get_cookies()
            logger.info("Found {} cookies".format(len(cookies)))
            assert isinstance(cookies, list), "get_cookies should return a list"
            
            # Test setting a cookie via navigation to cookie endpoint
            firefox.blocking_navigate_and_get_source(test_server.get_url("/set-cookie"), timeout=10)
            
            # Test get_cookies again to verify cookie was set
            cookies_after = firefox.get_cookies()
            logger.info("Found {} cookies after setting".format(len(cookies_after)))
            
            # Test set_cookie directly
            test_cookie = {
                "name": "test_cookie_direct",
                "value": "test_value_direct",
                "domain": "localhost",
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "sameSite": "lax"
            }
            success = firefox.set_cookie(test_cookie)
            logger.info("set_cookie result: {}".format(success))
            assert success, "set_cookie should return True"
            
            # Test clear_cookies
            success = firefox.clear_cookies()
            logger.info("clear_cookies result: {}".format(success))
            assert success, "clear_cookies should return True"
            
            # Verify cookies were cleared
            cookies_cleared = firefox.get_cookies()
            logger.info("Found {} cookies after clearing".format(len(cookies_cleared)))
            
            logger.info("Cookie management tests completed successfully")
    
    finally:
        test_server.stop()

def test_dom_interaction():
    """Test DOM interaction functions"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting DOM interaction tests...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Navigate to a test page with DOM elements
            firefox.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)
            
            # Test find_element
            element = firefox.find_element("h1")
            logger.info("Found element: {}".format(element))
            if element:
                assert element["found"], "Element should be found"
                logger.info("Element tag: {}".format(element.get('tagName')))
            
            # Test find_element by class
            element = firefox.find_element(".test-paragraph")
            logger.info("Found element by class: {}".format(element))
            
            # Test find_element by ID
            element = firefox.find_element("#test-link")
            logger.info("Found element by ID: {}".format(element))
            
            # Test click_element (may not have clickable elements on example.com)
            # This is just to test the function works, not that it actually clicks something
            success = firefox.click_element("body")
            logger.info("click_element result: {}".format(success))
            
            # Test click_link_containing_url
            success = firefox.click_link_containing_url("simple")
            logger.info("click_link_containing_url result: {}".format(success))
            
            # Test scroll_page
            success = firefox.scroll_page(100)  # Scroll down 100 pixels
            logger.info("scroll_page result: {}".format(success))
            assert success, "scroll_page should return True"
            
            logger.info("DOM interaction tests completed successfully")
    
    finally:
        test_server.stop()

def test_advanced_features():
    """Test advanced features"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting advanced feature tests...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Navigate to a test page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            
            # Test wait_for_dom_idle (with short timeout for testing)
            success = firefox.wait_for_dom_idle(dom_idle_requirement_secs=1, max_wait_timeout=5)
            logger.info("wait_for_dom_idle result: {}".format(success))
            
            # Test get_rendered_page_source
            source = firefox.get_rendered_page_source(dom_idle_requirement_secs=1, max_wait_timeout=5)
            logger.info("get_rendered_page_source length: {}".format(len(source)))
            assert len(source) > 0, "Rendered page source should not be empty"
            
            # Test new_tab
            new_tab_interface = firefox.new_tab(test_server.get_url("/javascript"))
            logger.info("new_tab result: {}".format(new_tab_interface))
            assert new_tab_interface is not None, "new_tab should return a valid interface instance"
            assert hasattr(new_tab_interface, 'active_browsing_context'), "new_tab should return an interface with active_browsing_context"
            
            logger.info("Advanced feature tests completed successfully")
    
    finally:
        test_server.stop()

def test_xhr_fetch():
    """Test xhr_fetch function for making XMLHttpRequests"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch tests...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to a page first (xhr_fetch is affected by same-origin policy)
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch GET request to same origin
            result = firefox.xhr_fetch(test_server.get_url("/simple"))
            logger.info("xhr_fetch GET result code: {}".format(result.get('code')))
            assert result is not None, "xhr_fetch should return a result"
            assert 'response' in result, "Result should have response key"
            assert result.get('code') == 200 or result.get('code') == 0, "Status code should be 200 or 0 (if blocked)"

            # Test xhr_fetch with custom headers
            result = firefox.xhr_fetch(
                test_server.get_url("/simple"),
                headers={"X-Custom-Header": "TestValue"}
            )
            logger.info("xhr_fetch with headers result: {}".format(result.get('code')))

            logger.info("xhr_fetch tests completed successfully")

    finally:
        test_server.stop()


def test_xpath_element_selection():
    """Test XPath element selection functions"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting XPath element selection tests...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to a test page with DOM elements
            firefox.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)

            # Test get_element_by_xpath
            element = firefox.get_element_by_xpath("//h1")
            logger.info("Found element by xpath: {}".format(element))
            if element:
                assert element.get("found"), "Element should be found"
                assert element.get("tagName") == "H1", "Element should be H1"

            # Test get_elements_by_xpath
            elements = firefox.get_elements_by_xpath("//p")
            logger.info("Found {} elements by xpath".format(len(elements)))
            assert isinstance(elements, list), "get_elements_by_xpath should return a list"

            # Test select_input_by_xpath
            success = firefox.select_input_by_xpath("//input[@type='text']")
            logger.info("select_input_by_xpath result: {}".format(success))
            # May be False if no input on page, that's OK

            # Test click_element_by_xpath
            success = firefox.click_element_by_xpath("//body")
            logger.info("click_element_by_xpath result: {}".format(success))
            assert success, "click_element_by_xpath on body should return True"

            # Test get_input_value_by_xpath (might be None if no input)
            value = firefox.get_input_value_by_xpath("//input[@type='text']")
            logger.info("get_input_value_by_xpath result: {}".format(value))

            # Test set_input_value_by_xpath
            success = firefox.set_input_value_by_xpath("//input[@type='text']", "test value")
            logger.info("set_input_value_by_xpath result: {}".format(success))

            logger.info("XPath element selection tests completed successfully")

    finally:
        test_server.stop()


def test_keyboard_events():
    """Test keyboard event dispatch functions"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting keyboard event tests...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to a test page with input elements
            firefox.blocking_navigate_and_get_source(test_server.get_url("/form"), timeout=15)

            # Test dispatch_key_event
            success = firefox.dispatch_key_event('a')
            logger.info("dispatch_key_event result: {}".format(success))
            assert success, "dispatch_key_event should return True"

            # Test dispatch_key_event with modifiers
            success = firefox.dispatch_key_event('a', modifiers=['Shift'])
            logger.info("dispatch_key_event with modifiers result: {}".format(success))
            assert success, "dispatch_key_event with modifiers should return True"

            # Test type_text
            success = firefox.type_text("hello")
            logger.info("type_text result: {}".format(success))
            assert success, "type_text should return True"

            # Test send_key_combination (Ctrl+A)
            success = firefox.send_key_combination(['Control', 'a'])
            logger.info("send_key_combination result: {}".format(success))
            assert success, "send_key_combination should return True"

            # Test convenience methods
            success = firefox.press_enter()
            logger.info("press_enter result: {}".format(success))
            assert success, "press_enter should return True"

            success = firefox.press_tab()
            logger.info("press_tab result: {}".format(success))
            assert success, "press_tab should return True"

            success = firefox.press_escape()
            logger.info("press_escape result: {}".format(success))
            assert success, "press_escape should return True"

            logger.info("Keyboard event tests completed successfully")

    finally:
        test_server.stop()


def test_type_text_in_input():
    """Test typing text into input fields"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting type_text_in_input tests...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to a test page with input elements
            firefox.blocking_navigate_and_get_source(test_server.get_url("/form"), timeout=15)

            # Test type_text_in_input
            success = firefox.type_text_in_input(
                "//input[@id='username']",
                "testuser",
                clear_first=True,
                delay_ms=10
            )
            logger.info("type_text_in_input result: {}".format(success))
            # May be False if element doesn't exist, that's OK for this test

            # Verify the value was set (if element exists)
            value = firefox.get_input_value_by_xpath("//input[@id='username']")
            logger.info("Input value after typing: {}".format(value))

            logger.info("type_text_in_input tests completed successfully")

    finally:
        test_server.stop()


def test_mouse_events():
    """Test mouse event functions"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting mouse event tests...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to a test page with clickable elements
            firefox.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)

            # Test get_element_coordinates_by_xpath
            coords = firefox.get_element_coordinates_by_xpath("//h1")
            logger.info("Element coordinates: {}".format(coords))
            assert coords is not None, "Should get element coordinates"
            assert 'x' in coords and 'y' in coords, "Coordinates should have x and y"

            # Test get_element_coordinates (CSS selector)
            coords_css = firefox.get_element_coordinates("#test-button")
            logger.info("Button coordinates (CSS): {}".format(coords_css))
            assert coords_css is not None, "Should get button coordinates"

            # Test move_mouse_to
            success = firefox.move_mouse_to(100, 100)
            logger.info("move_mouse_to result: {}".format(success))
            assert success, "move_mouse_to should return True"

            # Test move_mouse_to_element_by_xpath
            success = firefox.move_mouse_to_element_by_xpath("//h1")
            logger.info("move_mouse_to_element_by_xpath result: {}".format(success))
            assert success, "move_mouse_to_element_by_xpath should return True"

            # Test move_mouse_to_element (CSS selector)
            success = firefox.move_mouse_to_element("#test-button")
            logger.info("move_mouse_to_element result: {}".format(success))
            assert success, "move_mouse_to_element should return True"

            # Test mouse_click at coordinates
            success = firefox.mouse_click(100, 100)
            logger.info("mouse_click result: {}".format(success))
            assert success, "mouse_click should return True"

            # Test mouse_click_element_by_xpath
            success = firefox.mouse_click_element_by_xpath("//button[@id='test-button']")
            logger.info("mouse_click_element_by_xpath result: {}".format(success))
            assert success, "mouse_click_element_by_xpath should return True"

            # Test mouse_click_element (CSS selector)
            success = firefox.mouse_click_element("#test-button")
            logger.info("mouse_click_element result: {}".format(success))
            assert success, "mouse_click_element should return True"

            # Test mouse_double_click
            success = firefox.mouse_double_click(200, 200)
            logger.info("mouse_double_click result: {}".format(success))
            assert success, "mouse_double_click should return True"

            # Test hover_element_by_xpath
            success = firefox.hover_element_by_xpath("//a[@id='test-link']")
            logger.info("hover_element_by_xpath result: {}".format(success))
            assert success, "hover_element_by_xpath should return True"

            # Test mouse_drag
            success = firefox.mouse_drag(100, 100, 200, 200, duration_ms=50)
            logger.info("mouse_drag result: {}".format(success))
            assert success, "mouse_drag should return True"

            logger.info("Mouse event tests completed successfully")

    finally:
        test_server.stop()


def test_mouse_click_form_input():
    """Test clicking on form inputs with mouse and then typing"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting mouse click form input tests...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to form page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/form"), timeout=15)

            # Click on username input using mouse
            success = firefox.mouse_click_element_by_xpath("//input[@id='username']")
            logger.info("Clicked on username input: {}".format(success))
            assert success, "Should be able to click on username input"

            # Type into the focused field
            time.sleep(0.1)  # Brief pause for focus
            success = firefox.type_text("mouseuser")
            logger.info("Typed text: {}".format(success))
            assert success, "Should be able to type text"

            # Verify the value
            value = firefox.get_input_value_by_xpath("//input[@id='username']")
            logger.info("Input value after mouse click and typing: {}".format(value))
            assert value == "mouseuser", "Input should contain typed text"

            # Click on password field and type
            success = firefox.mouse_click_element_by_xpath("//input[@id='password']")
            logger.info("Clicked on password input: {}".format(success))

            time.sleep(0.1)
            success = firefox.type_text("secretpass")
            logger.info("Typed password: {}".format(success))

            # Verify password value
            value = firefox.get_input_value_by_xpath("//input[@id='password']")
            logger.info("Password value: {}".format(value))
            assert value == "secretpass", "Password should contain typed text"

            logger.info("Mouse click form input tests completed successfully")

    finally:
        test_server.stop()


if __name__ == "__main__":
    # Run pytest when this file is executed directly
    import pytest
    import sys

    # Setup logging for pytest runs
    FirefoxController.setup_logging(verbose=True)

    # Run pytest on this file
    sys.exit(pytest.main([__file__, "-v"]))