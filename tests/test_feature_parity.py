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

if __name__ == "__main__":
    # Run pytest when this file is executed directly
    import pytest
    import sys
    
    # Setup logging for pytest runs
    FirefoxController.setup_logging(verbose=True)
    
    # Run pytest on this file
    sys.exit(pytest.main([__file__, "-v"]))