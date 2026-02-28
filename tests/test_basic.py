#!/usr/bin/env python3

"""
Comprehensive test script for FirefoxController
Tests all features without using headless mode
"""

import pytest
import FirefoxController
import logging
import tempfile
import os
import time
import sys
import threading

# Add tests directory to path so we can import test_server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_server import TestServer

def test_basic_functionality():
    """Test basic FirefoxController functionality"""
    
    # Setup logging
    FirefoxController.setup_logging(verbose=True)
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting basic functionality test...")
        
        # Test with a simple context manager (non-headless)
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,  # Run in visible mode
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            logger.info("Firefox started successfully")
            
            # Test listing tabs
            tabs = firefox.manager.list_tabs()
            logger.info("Found {} tabs".format(len(tabs)))
            
            if tabs:
                tab_id = tabs[0]["actor"]
                logger.info("Using tab: {}".format(tab_id))
                
                # Test navigation to local test server
                source = firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=10)
                logger.info("Successfully navigated and got {} characters of source".format(len(source)))
                
                # Verify we got the expected content
                assert "Simple Test Page" in source, "Expected content not found in page source"
                
                # Test getting URL and title
                title, url = firefox.get_page_url_title()
                logger.info("Title: {}, URL: {}".format(title, url))
                
                logger.info("Basic functionality test completed successfully")
    
    finally:
        test_server.stop()

def test_navigation_features():
    """Test navigation and page source retrieval"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting navigation features test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=1024", "--height=768"]
        ) as firefox:
            
            # Test navigation to different URLs on local server
            test_urls = [
                test_server.get_url("/simple"),
                test_server.get_url("/javascript"),
                test_server.get_url("/dom"),
                "about:blank"
            ]
            
            for url in test_urls:
                logger.info("Navigating to {}...".format(url))
                source = firefox.blocking_navigate_and_get_source(url, timeout=15)
                
                # Verify we got some source
                assert len(source) > 0, "Got empty source from {}".format(url)
                logger.info(" Successfully got {} characters from {}".format(len(source), url))
                
                # Test get_page_source separately
                source2 = firefox.get_page_source()
                assert len(source2) > 0, "get_page_source() returned empty source"
                logger.info(" get_page_source() returned {} characters".format(len(source2)))
                
                # Test get_current_url
                current_url = firefox.get_current_url()
                logger.info(" Current URL: {}".format(current_url))
                
                # Test get_page_url_title
                title, page_url = firefox.get_page_url_title()
                logger.info(" Title: '{}', URL: {}".format(title, page_url))
            
            logger.info("Navigation features test completed successfully")
    
    finally:
        test_server.stop()

def test_screenshot_features():
    """Test screenshot functionality"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting screenshot features test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            
            # Test taking screenshot
            screenshot = firefox.take_screenshot(format="png")
            
            assert len(screenshot) > 0, "Screenshot was empty"
            logger.info(" Successfully took screenshot ({} bytes)".format(len(screenshot)))
            
            # Save screenshot to file for verification
            screenshot_path = "test_screenshot.png"
            with open(screenshot_path, "wb") as f:
                f.write(screenshot)
            logger.info(" Saved screenshot to {}".format(screenshot_path))
            
            # Clean up
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
                logger.info(" Cleaned up screenshot file")
            
            logger.info("Screenshot features test completed successfully")
    
    finally:
        test_server.stop()

def test_tab_management():
    """Test tab management features"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting tab management test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Test listing tabs
            tabs = firefox.manager.list_tabs()
            logger.info(" Found {} tabs initially".format(len(tabs)))
            
            # Test getting specific tab info
            if tabs:
                tab_id = tabs[0]["actor"]
                tab_info = firefox.manager.get_tab(tab_id)
                logger.info(" Got tab info: {}".format(tab_info))
            
            # Test navigation creates new tab context
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            
            # Check tabs again
            tabs_after = firefox.manager.list_tabs()
            logger.info(" Found {} tabs after navigation".format(len(tabs_after)))
            
            logger.info("Tab management test completed successfully")
    
    finally:
        test_server.stop()

def test_custom_profile():
    """Test using custom profile directory"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    temp_profile_dir = tempfile.mkdtemp()
    try:
        logger.info("Starting custom profile test...")
        logger.info("Using temporary profile: {}".format(temp_profile_dir))

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            profile_dir=temp_profile_dir,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Test basic functionality with custom profile
            tabs = firefox.manager.list_tabs()
            logger.info(" Found {} tabs with custom profile".format(len(tabs)))

            # Test navigation
            source = firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            logger.info(" Successfully navigated with custom profile ({} chars)".format(len(source)))

            logger.info("Custom profile test completed successfully")

    finally:
        test_server.stop()
        # On Windows, Firefox may still hold file locks briefly after termination.
        # Give it a moment, then try cleanup (tolerate failure).
        time.sleep(1)
        try:
            import shutil
            shutil.rmtree(temp_profile_dir, ignore_errors=True)
        except Exception:
            pass

def test_error_handling():
    """Test error handling and edge cases"""
    
    logger = logging.getLogger("FirefoxController")
    
    logger.info("Starting error handling test...")
    
    with FirefoxController.FirefoxRemoteDebugInterface(
        headless=False,
        additional_options=["--width=800", "--height=600"]
    ) as firefox:
        
        # Test getting tab that doesn't exist
        try:
            firefox.manager.get_tab("non-existent-tab-id")
            logger.warning(" Expected getting non-existent tab to fail")
        except FirefoxController.FirefoxTabNotFoundError:
            logger.info(" Correctly handled non-existent tab")
        
        logger.info("Error handling test completed successfully")

def test_context_manager():
    """Test context manager functionality"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting context manager test...")
        
        # Test that Firefox starts and stops properly
        firefox = FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        )
        
        # Use context manager
        with firefox:
            tabs = firefox.manager.list_tabs()
            logger.info(" Context manager working - found {} tabs".format(len(tabs)))
            
            # Do some operations
            source = firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            logger.info(" Context manager navigation successful ({} chars)".format(len(source)))
        
        # After context manager exits, Firefox should be closed
        logger.info(" Context manager exited cleanly")
        
        logger.info("Context manager test completed successfully")
    
    finally:
        test_server.stop()


def test_multi_tab_functionality():
    """Test multi-tab functionality with different URLs"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting multi-tab functionality test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=1024", "--height=768"]
        ) as firefox:
            
            # Test 1: Open multiple tabs with different URLs
            logger.info(" Opening multiple tabs...")
            
            # Get initial tab count
            initial_tabs = firefox.manager.list_tabs()
            initial_count = len(initial_tabs)
            logger.info(" Initial tab count: {}".format(initial_count))
            
            # Open new tabs with different test pages
            test_pages = [
                ("/simple", "Simple Test Page"),
                ("/javascript", "JavaScript Test Page"),
                ("/dom", "DOM Test Page")
            ]
            
            tab_interfaces = []  # Store interface instances instead of just IDs
            
            for page, expected_title in test_pages:
                # Open new tab - this now returns a FirefoxRemoteDebugInterface instance
                new_tab_interface = firefox.new_tab(test_server.get_url(page))
                if new_tab_interface:
                    tab_interfaces.append((new_tab_interface, test_server.get_url(page), expected_title))
                    logger.info(" Opened tab for {}".format(page))
                else:
                    logger.warning(" Failed to open tab for {}".format(page))
            
            # Test 2: Verify we have the expected number of tabs
            final_tabs = firefox.manager.list_tabs()
            final_count = len(final_tabs)
            logger.info(" Final tab count: {}".format(final_count))
            
            expected_tab_count = initial_count + len(tab_interfaces)
            assert final_count >= expected_tab_count, "Tab count verification failed ({} < {})".format(final_count, expected_tab_count)
            logger.info(" Tab count verification passed ({} >= {})".format(final_count, expected_tab_count))
            
            # Test 3: Test each tab interface individually
            logger.info(" Testing individual tab interfaces...")
            
            for i, (tab_interface, expected_url, expected_title) in enumerate(tab_interfaces):
                # Get page source from this specific tab
                source = tab_interface.get_page_source()
                
                # Get title from this specific tab
                title, url = tab_interface.get_page_url_title()
                
                logger.info(" Tab {}: URL={}, Title='{}'".format(i+1, url, title))
                
                # Verify content
                assert expected_title in source and expected_title in title, "Tab {}: Content verification failed".format(i+1)
                logger.info(" Tab {}: Content verification passed".format(i+1))
                    
            
            # Test 4: Verify tab creation and interface tracking
            logger.info(" Verifying tab creation and interface tracking...")
            
            # Get all tab interfaces from the manager
            all_tab_interfaces = firefox.manager.get_all_tab_interfaces()
            final_interface_count = len(all_tab_interfaces)
            
            assert final_interface_count > initial_count, "Tab interface tracking failed ({} <= {})".format(final_interface_count, initial_count)
            logger.info(" Tab interface tracking passed ({} > {})".format(final_interface_count, initial_count))
            
            logger.info("Multi-tab functionality test completed successfully")
    
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