#!/usr/bin/env python3

"""
Basic test script for FirefoxController
"""

import FirefoxController
import logging

def test_basic_functionality():
    """Test basic FirefoxController functionality"""
    
    # Setup logging
    FirefoxController.setup_logging(verbose=True)
    logger = logging.getLogger("FirefoxController")
    
    try:
        logger.info("Starting basic functionality test...")
        
        # Test with a simple context manager
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=True,
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

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("✓ Basic functionality test passed")
    else:
        print("✗ Basic functionality test failed")