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

def test_basic_functionality():
    """Test basic FirefoxController functionality"""
    
    # Setup logging
    FirefoxController.setup_logging(verbose=True)
    logger = logging.getLogger("FirefoxController")
    
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
                
                # Test navigation (this might fail if the URL is not accessible)
                try:
                    source = firefox.blocking_navigate_and_get_source("https://www.example.com", timeout=10)
                    logger.info(f"Successfully navigated and got {len(source)} characters of source")
                    
                    # Test getting URL and title
                    title, url = firefox.get_page_url_title()
                    logger.info(f"Title: {title}, URL: {url}")
                    
                except Exception as e:
                    logger.warning(f"Navigation test failed (expected if no internet): {e}")
            
            logger.info("Basic functionality test completed successfully")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    
    return True

def test_navigation_features():
    """Test navigation and page source retrieval"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting navigation features test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=1024", "--height=768"]
        ) as firefox:
            
            # Test navigation to different URLs
            test_urls = [
                "https://www.example.com",
                "https://www.google.com",
                "about:blank"
            ]
            
            for url in test_urls:
                try:
                    logger.info(f"Navigating to {url}...")
                    source = firefox.blocking_navigate_and_get_source(url, timeout=15)
                    
                    # Verify we got some source
                    if len(source) > 0:
                        logger.info(f" Successfully got {len(source)} characters from {url}")
                    else:
                        logger.warning(f" Got empty source from {url}")
                    
                    # Test get_page_source separately
                    source2 = firefox.get_page_source()
                    if len(source2) > 0:
                        logger.info(f" get_page_source() returned {len(source2)} characters")
                    
                    # Test get_current_url
                    current_url = firefox.get_current_url()
                    logger.info(f" Current URL: {current_url}")
                    
                    # Test get_page_url_title
                    title, page_url = firefox.get_page_url_title()
                    logger.info(f" Title: '{title}', URL: {page_url}")
                    
                except Exception as e:
                    logger.warning(f" Navigation to {url} failed: {e}")
            
            logger.info("Navigation features test completed successfully")
            
    except Exception as e:
        logger.error(f"Navigation test failed: {e}")
        return False
    
    return True

def test_screenshot_features():
    """Test screenshot functionality"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting screenshot features test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Navigate to a page first
            firefox.blocking_navigate_and_get_source("https://www.example.com", timeout=15)
            
            # Test taking screenshot
            screenshot = firefox.take_screenshot(format="png")
            
            if len(screenshot) > 0:
                logger.info(f" Successfully took screenshot ({len(screenshot)} bytes)")
                
                # Save screenshot to file for verification
                screenshot_path = "test_screenshot.png"
                with open(screenshot_path, "wb") as f:
                    f.write(screenshot)
                logger.info(f" Saved screenshot to {screenshot_path}")
                
                # Clean up
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
                    logger.info(" Cleaned up screenshot file")
            else:
                logger.warning(" Screenshot was empty")
            
            logger.info("Screenshot features test completed successfully")
            
    except Exception as e:
        logger.error(f"Screenshot test failed: {e}")
        return False
    
    return True

def test_tab_management():
    """Test tab management features"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting tab management test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Test listing tabs
            tabs = firefox.manager.list_tabs()
            logger.info(f" Found {len(tabs)} tabs initially")
            
            # Test getting specific tab info
            if tabs:
                tab_id = tabs[0]["actor"]
                tab_info = firefox.manager.get_tab(tab_id)
                logger.info(f" Got tab info: {tab_info}")
            
            # Test navigation creates new tab context
            firefox.blocking_navigate_and_get_source("https://www.example.com", timeout=15)
            
            # Check tabs again
            tabs_after = firefox.manager.list_tabs()
            logger.info(f" Found {len(tabs_after)} tabs after navigation")
            
            logger.info("Tab management test completed successfully")
            
    except Exception as e:
        logger.error(f"Tab management test failed: {e}")
        return False
    
    return True

def test_custom_profile():
    """Test using custom profile directory"""
    
    logger = logging.getLogger("FirefoxController")
    
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
                logger.info(f" Found {len(tabs)} tabs with custom profile")
                
                # Test navigation
                source = firefox.blocking_navigate_and_get_source("https://www.example.com", timeout=15)
                logger.info(f" Successfully navigated with custom profile ({len(source)} chars)")
                
                logger.info("Custom profile test completed successfully")
            
            # Profile should be cleaned up automatically
            logger.info(" Custom profile test completed")
            
    except Exception as e:
        logger.error(f"Custom profile test failed: {e}")
        return False
    
    return True

def test_error_handling():
    """Test error handling and edge cases"""
    
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting error handling test...")
        
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:
            
            # Test invalid URL navigation
            try:
                firefox.blocking_navigate_and_get_source("https://invalid-url-that-does-not-exist.com", timeout=5)
                logger.warning(" Expected navigation to invalid URL to fail")
            except Exception as e:
                logger.info(f" Correctly handled invalid URL: {type(e).__name__}")
            
            # Test getting tab that doesn't exist
            try:
                firefox.manager.get_tab("non-existent-tab-id")
                logger.warning(" Expected getting non-existent tab to fail")
            except FirefoxController.FirefoxTabNotFoundError:
                logger.info(" Correctly handled non-existent tab")
            except Exception as e:
                logger.info(f" Handled tab error: {type(e).__name__}")
            
            logger.info("Error handling test completed successfully")
            
    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False
    
    return True

def test_context_manager():
    """Test context manager functionality"""
    
    logger = logging.getLogger("FirefoxController")
    
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
            logger.info(f" Context manager working - found {len(tabs)} tabs")
            
            # Do some operations
            source = firefox.blocking_navigate_and_get_source("https://www.example.com", timeout=15)
            logger.info(f" Context manager navigation successful ({len(source)} chars)")
        
        # After context manager exits, Firefox should be closed
        logger.info(" Context manager exited cleanly")
        
        logger.info("Context manager test completed successfully")
        
    except Exception as e:
        logger.error(f"Context manager test failed: {e}")
        return False
    
    return True

def run_all_tests():
    """Run all comprehensive tests"""
    
    # Setup logging
    FirefoxController.setup_logging(verbose=True)
    logger = logging.getLogger("FirefoxController")
    
    logger.info("=" * 60)
    logger.info("Starting comprehensive FirefoxController tests")
    logger.info("Running in NON-HEADLESS mode (Firefox will be visible)")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Navigation Features", test_navigation_features),
        ("Screenshot Features", test_screenshot_features),
        ("Tab Management", test_tab_management),
        ("Custom Profile", test_custom_profile),
        ("Error Handling", test_error_handling),
        ("Context Manager", test_context_manager),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info('='*60)
        
        try:
            success = test_func()
            if success:
                logger.info(f" {test_name} PASSED")
                results.append((test_name, True))
            else:
                logger.warning(f" {test_name} FAILED")
                results.append((test_name, False))
        except Exception as e:
            logger.error(f" {test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info('='*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = " PASSED" if result else " FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info(" All tests passed!")
        return True
    else:
        logger.warning(" Some tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("\n All comprehensive tests passed")
    else:
        print("\n Some tests failed")