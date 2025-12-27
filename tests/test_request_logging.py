#!/usr/bin/env python3

"""
Test script for request logging feature
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


def test_request_logging_basic():
    """Test basic request logging functionality"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting request logging test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable request logging
            firefox.enable_request_logging()

            # Navigate to a test page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Wait a bit for events to be processed
            firefox.poll_events()

            # Get list of fetched URLs
            fetched_urls = firefox.get_fetched_urls()
            logger.info("Fetched URLs: {}".format(fetched_urls))

            # Should have at least the main page
            assert len(fetched_urls) > 0, "Should have captured at least one request"

            # Get content for the main page URL
            main_page_url = test_server.get_url("/simple")
            content = firefox.get_content_for_url(main_page_url)

            if content:
                logger.info("Content for {}: mimetype={}, size={} bytes".format(
                    content['url'],
                    content['mimetype'],
                    len(content['content'])
                ))

                # Verify content structure
                assert 'url' in content
                assert 'mimetype' in content
                assert 'content' in content
                assert isinstance(content['content'], bytes)

                # Content should contain HTML
                html_content = content['content'].decode('utf-8', errors='ignore')
                assert '<html' in html_content.lower()

            # Test clear cache
            firefox.clear_request_log_cache()
            fetched_urls_after_clear = firefox.get_fetched_urls()
            assert len(fetched_urls_after_clear) == 0, "Cache should be empty after clearing"

            # Navigate to another page to test that logging still works
            firefox.blocking_navigate_and_get_source(test_server.get_url("/javascript"), timeout=15)
            firefox.poll_events()

            fetched_urls_after_nav = firefox.get_fetched_urls()
            assert len(fetched_urls_after_nav) > 0, "Should have captured requests after clearing cache"

            # Disable request logging
            firefox.disable_request_logging()

            # After disabling, cache should be cleared
            fetched_urls_after_disable = firefox.get_fetched_urls()
            assert len(fetched_urls_after_disable) == 0, "Cache should be empty after disabling"

            logger.info("Request logging test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_multiple_resources():
    """Test request logging captures multiple resources"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting multiple resources test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable request logging
            firefox.enable_request_logging()

            # Navigate to a page (which may load multiple resources)
            firefox.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)

            # Wait for all resources to load
            firefox.poll_events()

            # Get list of fetched URLs
            fetched_urls = firefox.get_fetched_urls()
            logger.info("Fetched {} URLs".format(len(fetched_urls)))

            for url in fetched_urls:
                content = firefox.get_content_for_url(url)
                logger.info("  - {}: {} bytes, mimetype={}".format(
                    url,
                    len(content['content']),
                    content['mimetype']
                ))

            # Should have captured at least the main page
            assert len(fetched_urls) >= 1

            logger.info("Multiple resources test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_disable_clears_cache():
    """Test that disabling request logging clears the cache"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting disable clears cache test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable request logging
            firefox.enable_request_logging()

            # Navigate to a test page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            firefox.poll_events()

            # Should have captured some URLs
            fetched_urls = firefox.get_fetched_urls()
            assert len(fetched_urls) > 0

            # Disable request logging
            firefox.disable_request_logging()

            # Cache should be empty
            fetched_urls_after = firefox.get_fetched_urls()
            assert len(fetched_urls_after) == 0, "Cache should be empty after disabling"

            # Re-enable and verify it still works
            firefox.enable_request_logging()
            firefox.blocking_navigate_and_get_source(test_server.get_url("/javascript"), timeout=15)
            firefox.poll_events()

            fetched_urls_after_reenable = firefox.get_fetched_urls()
            assert len(fetched_urls_after_reenable) > 0, "Should capture requests after re-enabling"

            logger.info("Disable clears cache test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_multiple_tabs_independent():
    """Test that request logging is independent per tab"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting multiple tabs independent test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Navigate main tab to a page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Create a second tab
            tab2 = firefox.new_tab(test_server.get_url("/javascript"))
            firefox.poll_events()

            # Enable logging on main tab only
            firefox.enable_request_logging()

            # Navigate main tab - should be logged
            firefox.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)
            firefox.poll_events()

            # Navigate tab2 - should NOT be logged (logging not enabled on tab2)
            tab2.blocking_navigate_and_get_source(test_server.get_url("/cookies"), timeout=15)
            tab2.poll_events()

            # Check main tab has captured URLs
            main_tab_urls = firefox.get_fetched_urls()
            logger.info("Main tab captured {} URLs".format(len(main_tab_urls)))
            assert len(main_tab_urls) > 0, "Main tab should have captured requests"

            # Check tab2 has no captured URLs (logging not enabled)
            tab2_urls = tab2.get_fetched_urls()
            logger.info("Tab2 captured {} URLs".format(len(tab2_urls)))
            assert len(tab2_urls) == 0, "Tab2 should have no captured requests (logging not enabled)"

            # Now enable logging on tab2
            tab2.enable_request_logging()

            # Navigate tab2 again - should now be logged
            tab2.blocking_navigate_and_get_source(test_server.get_url("/form"), timeout=15)
            tab2.poll_events()

            # Check tab2 now has captured URLs
            tab2_urls_after = tab2.get_fetched_urls()
            logger.info("Tab2 captured {} URLs after enabling".format(len(tab2_urls_after)))
            assert len(tab2_urls_after) > 0, "Tab2 should have captured requests after enabling"

            # Verify caches are independent
            main_tab_urls_final = firefox.get_fetched_urls()

            # URLs should be different between tabs
            main_has_dom = any("/dom" in url for url in main_tab_urls_final)
            tab2_has_form = any("/form" in url for url in tab2_urls_after)

            assert main_has_dom, "Main tab should have /dom URL"
            assert tab2_has_form, "Tab2 should have /form URL"

            # Main tab should not have tab2's URLs
            main_has_form = any("/form" in url for url in main_tab_urls_final)
            assert not main_has_form, "Main tab should not have tab2's /form URL"

            logger.info("Multiple tabs independent test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_multiple_tabs_all_enabled():
    """Test request logging with all tabs enabled"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting multiple tabs all enabled test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Create three tabs
            tab2 = firefox.new_tab(test_server.get_url("/javascript"))
            tab3 = firefox.new_tab(test_server.get_url("/cookies"))

            # Enable logging on all tabs
            firefox.enable_request_logging()
            tab2.enable_request_logging()
            tab3.enable_request_logging()

            # Navigate all tabs to different pages
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            tab2.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)
            tab3.blocking_navigate_and_get_source(test_server.get_url("/form"), timeout=15)

            # Wait for all to complete
            tab3.poll_events()

            # Get URLs from all tabs
            tab1_urls = firefox.get_fetched_urls()
            tab2_urls = tab2.get_fetched_urls()
            tab3_urls = tab3.get_fetched_urls()

            logger.info("Tab1 captured {} URLs".format(len(tab1_urls)))
            logger.info("Tab2 captured {} URLs".format(len(tab2_urls)))
            logger.info("Tab3 captured {} URLs".format(len(tab3_urls)))

            # All tabs should have captured content
            assert len(tab1_urls) > 0, "Tab1 should have captured requests"
            assert len(tab2_urls) > 0, "Tab2 should have captured requests"
            assert len(tab3_urls) > 0, "Tab3 should have captured requests"

            # Verify each tab has its own content
            tab1_has_simple = any("/simple" in url for url in tab1_urls)
            tab2_has_dom = any("/dom" in url for url in tab2_urls)
            tab3_has_form = any("/form" in url for url in tab3_urls)

            assert tab1_has_simple, "Tab1 should have /simple URL"
            assert tab2_has_dom, "Tab2 should have /dom URL"
            assert tab3_has_form, "Tab3 should have /form URL"

            # Verify content is isolated (tab1 shouldn't have tab2's URLs)
            tab1_has_dom = any("/dom" in url for url in tab1_urls)
            tab2_has_simple = any("/simple" in url for url in tab2_urls)

            assert not tab1_has_dom, "Tab1 should not have tab2's /dom URL"
            assert not tab2_has_simple, "Tab2 should not have tab1's /simple URL"

            logger.info("Multiple tabs all enabled test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_disable_one_tab_others_continue():
    """Test that disabling logging on one tab doesn't affect others"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting disable one tab test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Create two tabs
            tab2 = firefox.new_tab(test_server.get_url("/javascript"))

            # Enable logging on both tabs
            firefox.enable_request_logging()
            tab2.enable_request_logging()

            # Navigate both tabs
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            tab2.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)
            firefox.poll_events()

            # Both should have content
            tab1_urls = firefox.get_fetched_urls()
            tab2_urls = tab2.get_fetched_urls()

            assert len(tab1_urls) > 0, "Tab1 should have captured requests"
            assert len(tab2_urls) > 0, "Tab2 should have captured requests"

            logger.info("Before disable - Tab1: {} URLs, Tab2: {} URLs".format(
                len(tab1_urls), len(tab2_urls)))

            # Disable logging on tab1 only
            firefox.disable_request_logging()

            # Navigate both tabs again
            firefox.blocking_navigate_and_get_source(test_server.get_url("/cookies"), timeout=15)
            tab2.blocking_navigate_and_get_source(test_server.get_url("/form"), timeout=15)
            firefox.poll_events()

            # Tab1 should have no URLs (logging disabled and cache cleared)
            tab1_urls_after = firefox.get_fetched_urls()
            assert len(tab1_urls_after) == 0, "Tab1 should have no URLs after disabling"

            # Tab2 should still be logging and have new URLs
            tab2_urls_after = tab2.get_fetched_urls()
            logger.info("After disable - Tab1: {} URLs, Tab2: {} URLs".format(
                len(tab1_urls_after), len(tab2_urls_after)))

            assert len(tab2_urls_after) > 0, "Tab2 should still have captured requests"

            # Tab2 should have both old and new content
            tab2_has_form = any("/form" in url for url in tab2_urls_after)
            assert tab2_has_form, "Tab2 should have new /form URL"

            logger.info("Disable one tab test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_clear_cache_one_tab_others_unaffected():
    """Test that clearing cache on one tab doesn't affect other tabs"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting clear cache one tab test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Create two tabs
            tab2 = firefox.new_tab(test_server.get_url("/javascript"))

            # Enable logging on both tabs
            firefox.enable_request_logging()
            tab2.enable_request_logging()

            # Navigate both tabs
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            tab2.blocking_navigate_and_get_source(test_server.get_url("/dom"), timeout=15)
            firefox.poll_events()

            # Both should have content
            tab1_urls_before = firefox.get_fetched_urls()
            tab2_urls_before = tab2.get_fetched_urls()

            assert len(tab1_urls_before) > 0, "Tab1 should have captured requests"
            assert len(tab2_urls_before) > 0, "Tab2 should have captured requests"

            logger.info("Before clear - Tab1: {} URLs, Tab2: {} URLs".format(
                len(tab1_urls_before), len(tab2_urls_before)))

            # Clear cache on tab1 only
            firefox.clear_request_log_cache()

            # Check tab1 cache is empty but tab2 is not
            tab1_urls_after_clear = firefox.get_fetched_urls()
            tab2_urls_after_clear = tab2.get_fetched_urls()

            logger.info("After clear - Tab1: {} URLs, Tab2: {} URLs".format(
                len(tab1_urls_after_clear), len(tab2_urls_after_clear)))

            assert len(tab1_urls_after_clear) == 0, "Tab1 should have no URLs after clearing"
            assert len(tab2_urls_after_clear) > 0, "Tab2 should still have URLs"

            # Verify tab2 still has the same URLs
            assert len(tab2_urls_after_clear) == len(tab2_urls_before), "Tab2 URLs should be unchanged"

            # Tab1 should still be logging (just cache was cleared)
            firefox.blocking_navigate_and_get_source(test_server.get_url("/cookies"), timeout=15)
            firefox.poll_events()

            tab1_urls_new = firefox.get_fetched_urls()
            assert len(tab1_urls_new) > 0, "Tab1 should capture new requests after cache clear"

            logger.info("Clear cache one tab test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_multiple_tabs_content_verification():
    """Test that cached content is actually correct for each tab"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting multiple tabs content verification test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Create a second tab
            tab2 = firefox.new_tab(test_server.get_url("/javascript"))

            # Enable logging on both tabs
            firefox.enable_request_logging()
            tab2.enable_request_logging()

            # Navigate to different pages with distinct content
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)
            tab2.blocking_navigate_and_get_source(test_server.get_url("/javascript"), timeout=15)
            firefox.poll_events()

            # Get content from both tabs
            tab1_urls = firefox.get_fetched_urls()
            tab2_urls = tab2.get_fetched_urls()

            logger.info("Tab1 URLs: {}".format(tab1_urls))
            logger.info("Tab2 URLs: {}".format(tab2_urls))

            # Find the main page URLs
            simple_url = test_server.get_url("/simple")
            javascript_url = test_server.get_url("/javascript")

            # Get content for tab1
            tab1_content = firefox.get_content_for_url(simple_url)
            if tab1_content:
                html_content = tab1_content['content'].decode('utf-8', errors='ignore')
                logger.info("Tab1 content preview: {}".format(html_content[:100]))

                # Verify it's the simple page
                assert 'Simple Test Page' in html_content, "Tab1 should have Simple Test Page content"
                assert 'text/html' in tab1_content['mimetype'].lower(), "Tab1 should have HTML mimetype"

            # Get content for tab2
            tab2_content = tab2.get_content_for_url(javascript_url)
            if tab2_content:
                html_content = tab2_content['content'].decode('utf-8', errors='ignore')
                logger.info("Tab2 content preview: {}".format(html_content[:100]))

                # Verify it's the javascript page
                assert 'JavaScript Test Page' in html_content, "Tab2 should have JavaScript Test Page content"
                assert 'testFunction' in html_content, "Tab2 should have testFunction in content"
                assert 'text/html' in tab2_content['mimetype'].lower(), "Tab2 should have HTML mimetype"

            # Verify tab1 doesn't have tab2's content
            tab1_javascript_content = firefox.get_content_for_url(javascript_url)
            assert tab1_javascript_content is None, "Tab1 should not have tab2's JavaScript page"

            # Verify tab2 doesn't have tab1's content
            tab2_simple_content = tab2.get_content_for_url(simple_url)
            assert tab2_simple_content is None, "Tab2 should not have tab1's Simple page"

            logger.info("Multiple tabs content verification test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_async_fetch():
    """Test that async fetch requests are captured after page load"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting async fetch test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable request logging
            firefox.enable_request_logging()

            # Navigate to page that performs async fetch
            firefox.blocking_navigate_and_get_source(test_server.get_url("/async-fetch"), timeout=15)

            # Wait for async fetch to complete (page waits 500ms then fetches)
            time.sleep(1)
            firefox.poll_events()

            # Get fetched URLs
            fetched_urls = firefox.get_fetched_urls()
            logger.info("Fetched URLs: {}".format(fetched_urls))

            # Should have captured both the page and the async API call
            assert len(fetched_urls) >= 2, "Should have captured at least page and API call"

            # Check for the API endpoint
            api_url = test_server.get_url("/api/data")
            api_captured = any(api_url in url for url in fetched_urls)
            assert api_captured, "Should have captured async /api/data request"

            # Get the API response content
            api_content = firefox.get_content_for_url(api_url)
            if api_content:
                logger.info("API content mimetype: {}".format(api_content['mimetype']))
                assert 'application/json' in api_content['mimetype'], "API should return JSON"

                # Parse JSON response
                import json as json_module
                response_data = json_module.loads(api_content['content'].decode('utf-8'))
                logger.info("API response: {}".format(response_data))

                assert response_data['status'] == 'success', "API response should be successful"
                assert 'data' in response_data, "API response should have data field"
                assert 'This is async fetched data' in response_data['data'], "API response should have expected data"

            logger.info("Async fetch test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_async_xhr():
    """Test that async XMLHttpRequest calls are captured"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting async XHR test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable request logging
            firefox.enable_request_logging()

            # Navigate to page that performs async XHR
            firefox.blocking_navigate_and_get_source(test_server.get_url("/async-xhr"), timeout=15)

            # Wait for async XHR to complete
            time.sleep(1)
            firefox.poll_events()

            # Get fetched URLs
            fetched_urls = firefox.get_fetched_urls()
            logger.info("Fetched URLs: {}".format(fetched_urls))

            # Check for the API endpoint
            api_url = test_server.get_url("/api/text")
            api_captured = any(api_url in url for url in fetched_urls)
            assert api_captured, "Should have captured async /api/text XHR request"

            # Get the API response content
            api_content = firefox.get_content_for_url(api_url)
            if api_content:
                logger.info("API content mimetype: {}".format(api_content['mimetype']))
                assert 'text/plain' in api_content['mimetype'], "API should return plain text"

                # Check text response
                response_text = api_content['content'].decode('utf-8')
                logger.info("API response: {}".format(response_text))
                assert 'Plain text async response' in response_text, "API response should have expected text"

            logger.info("Async XHR test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_multiple_async_requests():
    """Test that multiple async requests at different times are all captured"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting multiple async requests test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable request logging
            firefox.enable_request_logging()

            # Navigate to page that performs multiple async fetches
            firefox.blocking_navigate_and_get_source(test_server.get_url("/async-multiple"), timeout=15)

            # Wait for all async fetches to complete
            # Fetch 1: immediate, Fetch 2: after 500ms, Fetch 3: after 1000ms + 1s API delay
            for _ in range(5):
                firefox.poll_events()
                time.sleep(0.5)

            # Poll one more time to capture any events that arrived during the last sleep
            firefox.poll_events()

            # Get fetched URLs
            fetched_urls = firefox.get_fetched_urls()
            logger.info("Fetched {} URLs".format(len(fetched_urls)))
            for url in fetched_urls:
                logger.info("  - {}".format(url))

            # Should have captured page + 3 API calls
            assert len(fetched_urls) >= 4, "Should have captured at least page and 3 API calls, got {}".format(len(fetched_urls))

            # Check for all three API endpoints
            api_data_url = test_server.get_url("/api/data")
            api_text_url = test_server.get_url("/api/text")
            api_delayed_url = test_server.get_url("/api/delayed")

            has_api_data = any(api_data_url in url for url in fetched_urls)
            has_api_text = any(api_text_url in url for url in fetched_urls)
            has_api_delayed = any(api_delayed_url in url for url in fetched_urls)

            assert has_api_data, "Should have captured /api/data request"
            assert has_api_text, "Should have captured /api/text request"
            assert has_api_delayed, "Should have captured /api/delayed request"

            # Verify content of all three API calls
            # API 1: JSON data
            api_data_content = firefox.get_content_for_url(api_data_url)
            if api_data_content:
                import json as json_module
                data = json_module.loads(api_data_content['content'].decode('utf-8'))
                assert data['status'] == 'success', "API data should be successful"

            # API 2: Plain text
            api_text_content = firefox.get_content_for_url(api_text_url)
            if api_text_content:
                text = api_text_content['content'].decode('utf-8')
                assert 'Plain text async response' in text, "API text should match"

            # API 3: Delayed JSON
            api_delayed_content = firefox.get_content_for_url(api_delayed_url)
            if api_delayed_content:
                import json as json_module
                data = json_module.loads(api_delayed_content['content'].decode('utf-8'))
                assert data['status'] == 'success', "API delayed should be successful"
                assert 'delay' in data, "API delayed should have delay field"

            logger.info("Multiple async requests test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_async_with_navigation():
    """Test that async requests are captured correctly across page navigations"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting async with navigation test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable request logging
            firefox.enable_request_logging()

            # Navigate to first async page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/async-fetch"), timeout=15)
            time.sleep(1)
            firefox.poll_events()

            # Get URLs from first page
            first_page_urls = firefox.get_fetched_urls()
            logger.info("First page captured {} URLs".format(len(first_page_urls)))

            api_data_captured = any("/api/data" in url for url in first_page_urls)
            assert api_data_captured, "Should have captured /api/data from first page"

            # Navigate to second async page (XHR)
            firefox.blocking_navigate_and_get_source(test_server.get_url("/async-xhr"), timeout=15)
            time.sleep(1)
            firefox.poll_events()

            # Get URLs after second navigation
            second_page_urls = firefox.get_fetched_urls()
            logger.info("After second page captured {} URLs".format(len(second_page_urls)))

            # Should have both first and second page API calls
            has_api_data = any("/api/data" in url for url in second_page_urls)
            has_api_text = any("/api/text" in url for url in second_page_urls)

            assert has_api_data, "Should still have /api/data from first page"
            assert has_api_text, "Should have /api/text from second page"

            # Clear cache
            firefox.clear_request_log_cache()

            # Navigate to third async page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/async-multiple"), timeout=15)
            for _ in range(5):
                firefox.poll_events()
                time.sleep(0.5)

            # Poll one more time to capture any events that arrived during the last sleep
            firefox.poll_events()

            # After clear, should only have URLs from third page
            third_page_urls = firefox.get_fetched_urls()
            logger.info("After clear captured {} URLs".format(len(third_page_urls)))

            # Should not have old URLs
            has_old_api_data = any("/api/data" in url for url in third_page_urls)
            has_old_api_text = any("/api/text" in url for url in third_page_urls)

            # But should have new async calls from multiple page
            assert len(third_page_urls) >= 4, "Should have captured multiple async calls from third page"

            logger.info("Async with navigation test completed successfully")

    finally:
        test_server.stop()


def test_request_logging_async_multiple_tabs_independent():
    """Test that async requests in different tabs are captured independently"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting async multiple tabs test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Create second tab
            tab2 = firefox.new_tab(test_server.get_url("/simple"))

            # Enable logging on both tabs
            firefox.enable_request_logging()
            tab2.enable_request_logging()

            # Navigate to different async pages
            firefox.blocking_navigate_and_get_source(test_server.get_url("/async-fetch"), timeout=15)
            tab2.blocking_navigate_and_get_source(test_server.get_url("/async-xhr"), timeout=15)

            # Wait for async requests
            time.sleep(1)
            firefox.poll_events()
            tab2.poll_events()

            # Get URLs from both tabs
            tab1_urls = firefox.get_fetched_urls()
            tab2_urls = tab2.get_fetched_urls()

            logger.info("Tab 1 captured {} URLs".format(len(tab1_urls)))
            logger.info("Tab 2 captured {} URLs".format(len(tab2_urls)))

            # Tab 1 should have /api/data (from fetch page)
            tab1_has_data = any("/api/data" in url for url in tab1_urls)
            assert tab1_has_data, "Tab 1 should have captured /api/data"

            # Tab 2 should have /api/text (from XHR page)
            tab2_has_text = any("/api/text" in url for url in tab2_urls)
            assert tab2_has_text, "Tab 2 should have captured /api/text"

            # Tab 1 should NOT have tab 2's async requests
            tab1_has_text = any("/api/text" in url for url in tab1_urls)
            assert not tab1_has_text, "Tab 1 should not have tab 2's /api/text"

            # Tab 2 should NOT have tab 1's async requests
            tab2_has_data = any("/api/data" in url for url in tab2_urls)
            assert not tab2_has_data, "Tab 2 should not have tab 1's /api/data"

            logger.info("Async multiple tabs test completed successfully")

    finally:
        test_server.stop()


if __name__ == "__main__":
    # Setup logging for pytest runs
    FirefoxController.setup_logging(verbose=True)

    # Run pytest on this file
    sys.exit(pytest.main([__file__, "-v"]))
