#!/usr/bin/env python3

"""
Comprehensive test script for FirefoxController
Tests all features without using headless mode
"""

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
    
    try:
        logger.info("Starting basic functionality test...")
        
        # Start test server
        test_server = TestServer()
        test_server.start()
        
        try:
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
                    try:
                        source = firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=10)
                        logger.info(f"Successfully navigated and got {len(source)} characters of source")
                        
                        # Verify we got the expected content
                        if "Simple Test Page" in source:
                            logger.info("Found expected content in page source")
                        else:
                            logger.warning("Expected content not found in page source")
                        
                        # Test getting URL and title
                        title, url = firefox.get_page_url_title()
                        logger.info(f"Title: {title}, URL: {url}")
                        
                    except Exception as e:
                        logger.error(f"Navigation test failed: {e}")
                        return False
                
                logger.info("Basic functionality test completed successfully")
                
        finally:
            test_server.stop()
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    
    return True

def test_navigation_and_screenshot():
    """Test navigation and screenshot functionality"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting navigation and screenshot test...")
        
        # Start test server
        test_server = TestServer()
        test_server.start()
        
        try:
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
                if len(screenshot) > 0:
                    logger.info(f"Successfully took screenshot ({len(screenshot)} bytes)")
                else:
                    logger.warning("Screenshot was empty")
                
                logger.info("Navigation and screenshot test completed successfully")
                
        finally:
            test_server.stop()
            
    except Exception as e:
        logger.error(f"Navigation and screenshot test failed: {e}")
        return False
    
    return True

def test_custom_profile():
    """Test using custom profile directory"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting custom profile test...")
        
        # Start test server
        test_server = TestServer()
        test_server.start()
        
        try:
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
            
            # Profile should be cleaned up automatically
            logger.info("Custom profile test completed")
            
        finally:
            test_server.stop()
            
    except Exception as e:
        logger.error(f"Custom profile test failed: {e}")
        return False
    
    return True

def run_comprehensive_tests():
    """Run comprehensive tests"""
    
    # Setup logging
    FirefoxController.setup_logging(verbose=True)
    logger = logging.getLogger("FirefoxController")
    
    logger.info("=" * 60)
    logger.info("Starting comprehensive FirefoxController tests")
    logger.info("Running in NON-HEADLESS mode (Firefox will be visible)")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Navigation and Screenshot", test_navigation_and_screenshot),
        ("Custom Profile", test_custom_profile),
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
    logger.info("TEST SUMMARY")
    logger.info('='*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("All tests passed!")
        return True
    else:
        logger.warning("Some tests failed")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    if success:
        print("\nAll comprehensive tests passed")
    else:
        print("\nSome tests failed")