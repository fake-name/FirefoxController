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
            logger.info(f"Found {len(tabs)} tabs")
            
            if tabs:
                tab_id = tabs[0]["actor"]
                logger.info(f"Using tab: {tab_id}")
                
                # Test navigation to local test server
                source = firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=10)
                logger.info(f"Successfully navigated and got {len(source)} characters of source")
                
                # Verify we got the expected content
                assert "Simple Test Page" in source, "Expected content not found in page source"
                
                # Test getting URL and title
                title, url = firefox.get_page_url_title()
                logger.info(f"Title: {title}, URL: {url}")
            
            logger.info("Basic functionality test completed successfully")
    
    finally:
        test_server.stop()

def test_navigation_and_screenshot():
    """Test navigation and screenshot functionality"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting navigation and screenshot test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=1024", "--height=768"]
        ) as firefox:
            
            # Test navigation
            source = firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            logger.info(f"Successfully navigated ({len(source)} characters)")
            
            # Test get_page_source
            source2 = firefox.get_page_source()
            logger.info(f"get_page_source() returned {len(source2)} characters")
            
            # Test get_current_url
            current_url = firefox.get_current_url()
            logger.info(f"Current URL: {current_url}")
            
            # Test get_page_url_title
            title, page_url = firefox.get_page_url_title()
            logger.info(f"Title: '{title}', URL: {page_url}")
            
            # Test screenshot
            screenshot = firefox.take_screenshot(format="png")
            assert len(screenshot) > 0, "Screenshot was empty"
            logger.info(f"Successfully took screenshot ({len(screenshot)} bytes)")
            
            logger.info("Navigation and screenshot test completed successfully")
    
    finally:
        test_server.stop()

def test_custom_profile():
    """Test using custom profile directory"""
    
    logger = logging.getLogger("FirefoxController")
    
    # Start test server
    test_server = TestServer()
    test_server.start()
    
    try:
        logger.info("Starting custom profile test...")
        
        # Create a temporary profile directory
        with tempfile.TemporaryDirectory() as temp_profile_dir:
            logger.info(f"Using temporary profile: {temp_profile_dir}")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            profile_dir=temp_profile_dir,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Test basic functionality with custom profile
            tabs = firefox.manager.list_tabs()
            logger.info(f"Found {len(tabs)} tabs with custom profile")
            
            # Test navigation
            source = firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            logger.info(f"Successfully navigated with custom profile ({len(source)} chars)")
            
            logger.info("Custom profile test completed successfully")
    
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