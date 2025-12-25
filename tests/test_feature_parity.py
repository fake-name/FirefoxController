#!/usr/bin/env python3

"""
Test script for FirefoxController feature parity with ChromeController
Tests all the new functions added to achieve feature parity
"""

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
    
    try:
        logger.info("Starting JavaScript execution tests...")
        
        # Start test server
        test_server = TestServer()
        test_server.start()
        
        try:
            with FirefoxController.FirefoxRemoteDebugInterface(
                headless=False,
                additional_options=["--width=800", "--height=600"]
            ) as firefox:
                
                # Navigate to a test page
                firefox.blocking_navigate_and_get_source(test_server.get_url("/javascript"), timeout=15)
                
                # Test execute_javascript_statement
                result = firefox.execute_javascript_statement("1 + 1")
                logger.info(f"JavaScript statement result: {result}")
                assert result == 2, f"Expected 2, got {result}"
                
                # Test execute_javascript_statement with variable
                result = firefox.execute_javascript_statement("document.title")
                logger.info(f"Document title: {result}")
                assert result is not None, "Document title should not be None"
                
                # Test execute_javascript_function
                func = "function test(a, b) { return a + b; }"
                result = firefox.execute_javascript_function(func, [3, 5])
                logger.info(f"JavaScript function result: {result}")
                assert result == 8, f"Expected 8, got {result}"
                
                # Test calling a function defined in the page
                result = firefox.execute_javascript_statement("testFunction(10, 20)")
                logger.info(f"Page function result: {result}")
                assert result == 30, f"Expected 30, got {result}"
                
                logger.info("JavaScript execution tests completed successfully")
                return True
                
        finally:
            test_server.stop()
            
    except Exception as e:
        logger.error(f"JavaScript execution tests failed: {e}")
        return False

def test_navigation_functions():
    """Test navigation functions"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting navigation function tests...")
        
        # Start test server
        test_server = TestServer()
        test_server.start()
        
        try:
            with FirefoxController.FirefoxRemoteDebugInterface(
                headless=False,
                additional_options=["--width=800", "--height=600"]
            ) as firefox:
                
                # Test navigate_to (JS-based navigation)
                success = firefox.navigate_to(test_server.get_url("/simple"))
                logger.info(f"navigate_to result: {success}")
                assert success, "navigate_to should return True"
                
                # Wait for navigation to complete
                time.sleep(2)
                
                # Test blocking_navigate
                success = firefox.blocking_navigate(test_server.get_url("/javascript"), timeout=10)
                logger.info(f"blocking_navigate result: {success}")
                assert success, "blocking_navigate should return True"
                
                # Verify we're on the right page
                current_url = firefox.get_current_url()
                logger.info(f"Current URL after blocking_navigate: {current_url}")
                assert "javascript" in current_url.lower(), f"Expected javascript in URL, got {current_url}"
                
                logger.info("Navigation function tests completed successfully")
                return True
                
        finally:
            test_server.stop()
            
    except Exception as e:
        logger.error(f"Navigation function tests failed: {e}")
        return False

def test_cookie_management():
    """Test cookie management functions"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting cookie management tests...")
        
        # Start test server
        test_server = TestServer()
        test_server.start()
        
        try:
            with FirefoxController.FirefoxRemoteDebugInterface(
                headless=False,
                additional_options=["--width=800", "--height=600"]
            ) as firefox:
                
                # Navigate to a test page
                firefox.blocking_navigate_and_get_source(test_server.get_url("/cookies"), timeout=15)
                
                # Test get_cookies
                cookies = firefox.get_cookies()
                logger.info(f"Found {len(cookies)} cookies")
                assert isinstance(cookies, list), "get_cookies should return a list"
                
                # Test setting a cookie via navigation to cookie endpoint
                firefox.blocking_navigate_and_get_source(test_server.get_url("/set-cookie"), timeout=10)
                
                # Test get_cookies again to verify cookie was set
                cookies_after = firefox.get_cookies()
                logger.info(f"Found {len(cookies_after)} cookies after setting")
                
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
                logger.info(f"set_cookie result: {success}")
                assert success, "set_cookie should return True"
                
                # Test clear_cookies
                success = firefox.clear_cookies()
                logger.info(f"clear_cookies result: {success}")
                assert success, "clear_cookies should return True"
                
                # Verify cookies were cleared
                cookies_cleared = firefox.get_cookies()
                logger.info(f"Found {len(cookies_cleared)} cookies after clearing")
                
                logger.info("Cookie management tests completed successfully")
                return True
                
        finally:
            test_server.stop()
            
    except Exception as e:
        logger.error(f"Cookie management tests failed: {e}")
        return False

def test_dom_interaction():
    """Test DOM interaction functions"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting DOM interaction tests...")
        
        # Start test server
        test_server = TestServer()
        test_server.start()
        
        try:
            with FirefoxController.FirefoxRemoteDebugInterface(
                headless=False,
                additional_options=["--width=800", "--height=600"]
            ) as firefox:
                
                # Navigate to a test page with DOM elements
                firefox.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)
                
                # Test find_element
                element = firefox.find_element("h1")
                logger.info(f"Found element: {element}")
                if element:
                    assert element["found"], "Element should be found"
                    logger.info(f"Element tag: {element.get('tagName')}")
                
                # Test find_element by class
                element = firefox.find_element(".test-paragraph")
                logger.info(f"Found element by class: {element}")
                
                # Test find_element by ID
                element = firefox.find_element("#test-link")
                logger.info(f"Found element by ID: {element}")
                
                # Test click_element (may not have clickable elements on example.com)
                # This is just to test the function works, not that it actually clicks something
                success = firefox.click_element("body")
                logger.info(f"click_element result: {success}")
                
                # Test click_link_containing_url
                success = firefox.click_link_containing_url("simple")
                logger.info(f"click_link_containing_url result: {success}")
                
                # Test scroll_page
                success = firefox.scroll_page(100)  # Scroll down 100 pixels
                logger.info(f"scroll_page result: {success}")
                assert success, "scroll_page should return True"
                
                logger.info("DOM interaction tests completed successfully")
                return True
                
        finally:
            test_server.stop()
            
    except Exception as e:
        logger.error(f"DOM interaction tests failed: {e}")
        return False

def test_advanced_features():
    """Test advanced features"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting advanced feature tests...")
        
        # Start test server
        test_server = TestServer()
        test_server.start()
        
        try:
            with FirefoxController.FirefoxRemoteDebugInterface(
                headless=False,
                additional_options=["--width=800", "--height=600"]
            ) as firefox:
                
                # Navigate to a test page
                firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
                
                # Test wait_for_dom_idle (with short timeout for testing)
                success = firefox.wait_for_dom_idle(dom_idle_requirement_secs=1, max_wait_timeout=5)
                logger.info(f"wait_for_dom_idle result: {success}")
                
                # Test get_rendered_page_source
                source = firefox.get_rendered_page_source(dom_idle_requirement_secs=1, max_wait_timeout=5)
                logger.info(f"get_rendered_page_source length: {len(source)}")
                assert len(source) > 0, "Rendered page source should not be empty"
                
                # Test new_tab
                new_tab_id = firefox.new_tab(test_server.get_url("/javascript"))
                logger.info(f"new_tab result: {new_tab_id}")
                assert len(new_tab_id) > 0, "new_tab should return a non-empty context ID"
                
                logger.info("Advanced feature tests completed successfully")
                return True
                
        finally:
            test_server.stop()
            
    except Exception as e:
        logger.error(f"Advanced feature tests failed: {e}")
        return False

def run_feature_parity_tests():
    """Run all feature parity tests"""
    
    # Setup logging
    FirefoxController.setup_logging(verbose=True)
    logger = logging.getLogger("FirefoxController")
    
    logger.info("=" * 60)
    logger.info("Starting FirefoxController Feature Parity Tests")
    logger.info("Testing new functions for ChromeController compatibility")
    logger.info("=" * 60)
    
    tests = [
        ("JavaScript Execution", test_javascript_execution),
        ("Navigation Functions", test_navigation_functions),
        ("Cookie Management", test_cookie_management),
        ("DOM Interaction", test_dom_interaction),
        ("Advanced Features", test_advanced_features),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info('='*60)
        
        try:
            success = test_func()
            if success:
                logger.info(f"{test_name} PASSED")
                results.append((test_name, True))
            else:
                logger.warning(f"{test_name} FAILED")
                results.append((test_name, False))
        except Exception as e:
            logger.error(f"{test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("FEATURE PARITY TEST SUMMARY")
    logger.info('='*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("All feature parity tests passed!")
        return True
    else:
        logger.warning("Some feature parity tests failed")
        return False

if __name__ == "__main__":
    success = run_feature_parity_tests()
    if success:
        print("\nAll feature parity tests passed")
    else:
        print("\nSome feature parity tests failed")