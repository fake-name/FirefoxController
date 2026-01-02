#!/usr/bin/env python3

"""
Timeout handling tests for FirefoxController

Tests various timeout scenarios:
- Pages that never finish loading
- Slow loading pages
- Partial content delivery
- Stuck resources
- Timeout escalation in process cleanup
"""

import pytest
import FirefoxController
from FirefoxController import (
    FirefoxNavigateTimedOut,
    BrowserTimeoutError,
    BrowserNavigationError,
    BrowserOperationError
)
import logging
import time
import sys
import os

# Add tests directory to path so we can import test_server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_server import TestServer


@pytest.fixture(scope="function")
def test_server():
    """Start test server for each test function"""
    server = TestServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="function")
def firefox_instance():
    """Create a Firefox instance for each test"""
    FirefoxController.setup_logging(verbose=True)

    firefox = FirefoxController.FirefoxRemoteDebugInterface(
        headless=False,
        additional_options=["--width=1024", "--height=768"]
    )

    # Start Firefox using context manager entry
    firefox.__enter__()

    yield firefox

    # Cleanup using context manager exit
    firefox.__exit__(None, None, None)


def test_infinite_loading_page_timeout(test_server, firefox_instance):
    """Test that a page that never finishes loading raises timeout exception"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing infinite loading page with timeout...")

    # Navigate to page that never finishes loading
    # Should timeout after 5 seconds
    url = test_server.get_url("/timeout/infinite")

    start_time = time.time()

    with pytest.raises((FirefoxNavigateTimedOut, BrowserTimeoutError, BrowserNavigationError)):
        firefox_instance.blocking_navigate(url, timeout=5)

    elapsed = time.time() - start_time

    # Verify timeout occurred within reasonable bounds (5s +/- 2s tolerance)
    assert 3 <= elapsed <= 7, "Timeout took {}s, expected ~5s".format(elapsed)

    logger.info("PASS: Infinite loading page correctly timed out after {:.1f}s".format(elapsed))


def test_slow_page_within_timeout(test_server, firefox_instance):
    """Test that a slow page completes successfully within timeout"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing slow page that completes within timeout...")

    # Navigate to page that delays 3 seconds before completing
    # Timeout is 10 seconds, so should succeed
    url = test_server.get_url("/timeout/slow?delay=3")

    start_time = time.time()

    # Should succeed without exception
    success = firefox_instance.blocking_navigate(url, timeout=10)

    elapsed = time.time() - start_time

    assert success, "Navigation should have succeeded"
    assert 2 <= elapsed <= 5, "Navigation took {}s, expected ~3s".format(elapsed)

    # Verify we can get page source
    source = firefox_instance.get_page_source()
    assert "Slow Loading Page" in source, "Expected content not found"
    assert "3 seconds" in source, "Expected delay message not found"

    logger.info("PASS: Slow page loaded successfully in {:.1f}s".format(elapsed))


def test_slow_page_exceeds_timeout(test_server, firefox_instance):
    """Test that a slow page that exceeds timeout raises exception"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing slow page that exceeds timeout...")

    # Navigate to page that delays 10 seconds
    # Timeout is 3 seconds, so should fail
    url = test_server.get_url("/timeout/slow?delay=10")

    start_time = time.time()

    with pytest.raises((FirefoxNavigateTimedOut, BrowserTimeoutError, BrowserNavigationError)):
        firefox_instance.blocking_navigate(url, timeout=3)

    elapsed = time.time() - start_time

    # Verify timeout occurred within reasonable bounds (3s +/- 2s tolerance)
    assert 1 <= elapsed <= 5, "Timeout took {}s, expected ~3s".format(elapsed)

    logger.info("PASS: Slow page correctly timed out after {:.1f}s".format(elapsed))


def test_partial_content_timeout(test_server, firefox_instance):
    """Test page that sends partial content then stalls"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing partial content delivery that stalls...")

    # Navigate to page that sends 3 chunks then blocks forever
    url = test_server.get_url("/timeout/partial")

    start_time = time.time()

    with pytest.raises((FirefoxNavigateTimedOut, BrowserTimeoutError, BrowserNavigationError)):
        firefox_instance.blocking_navigate(url, timeout=5)

    elapsed = time.time() - start_time

    # Should timeout around 5 seconds (chunks take ~3s total, then stalls)
    assert 3 <= elapsed <= 7, "Timeout took {}s, expected ~5s".format(elapsed)

    logger.info("PASS: Partial content correctly timed out after {:.1f}s".format(elapsed))


def test_stuck_resource_timeout(test_server, firefox_instance):
    """Test page with resources that never load"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing page with stuck resources...")

    # Navigate to page that loads HTML but has resources that never complete
    url = test_server.get_url("/timeout/stuck-resource")

    start_time = time.time()

    # This might timeout depending on whether Firefox waits for all resources
    # With wait="complete", it should timeout
    with pytest.raises((FirefoxNavigateTimedOut, BrowserTimeoutError, BrowserNavigationError)):
        firefox_instance.blocking_navigate(url, timeout=5)

    elapsed = time.time() - start_time

    # Should timeout around 5 seconds
    assert 3 <= elapsed <= 7, "Timeout took {}s, expected ~5s".format(elapsed)

    logger.info("PASS: Stuck resource page correctly timed out after {:.1f}s".format(elapsed))


def test_normal_page_no_regression(test_server, firefox_instance):
    """Test that normal pages still work correctly (regression test)"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing normal page navigation (regression test)...")

    # Navigate to simple test page
    url = test_server.get_url("/simple")

    start_time = time.time()

    # Should succeed without exception
    success = firefox_instance.blocking_navigate(url, timeout=10)

    elapsed = time.time() - start_time

    assert success, "Navigation should have succeeded"
    assert elapsed < 5, "Normal page took too long: {}s".format(elapsed)

    # Verify we can get page source
    source = firefox_instance.get_page_source()
    assert "Simple Test Page" in source, "Expected content not found"

    # Verify page title
    title, page_url = firefox_instance.get_page_url_title()
    assert "Simple Test Page" in title, "Expected title not found"

    logger.info("PASS: Normal page loaded successfully in {:.1f}s".format(elapsed))


def test_multiple_timeout_scenarios_sequential(test_server, firefox_instance):
    """Test multiple timeout scenarios in sequence"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing multiple timeout scenarios sequentially...")

    # Test 1: Normal page
    logger.info("  1. Normal page...")
    url = test_server.get_url("/simple")
    success = firefox_instance.blocking_navigate(url, timeout=10)
    assert success, "Normal page failed"
    source = firefox_instance.get_page_source()
    assert "Simple Test Page" in source
    logger.info("  PASS: Normal page succeeded")

    # Test 2: Slow page within timeout
    logger.info("  2. Slow page within timeout...")
    url = test_server.get_url("/timeout/slow?delay=2")
    success = firefox_instance.blocking_navigate(url, timeout=10)
    assert success, "Slow page within timeout failed"
    logger.info("  PASS: Slow page within timeout succeeded")

    # Test 3: Timeout scenario
    logger.info("  3. Page that times out...")
    url = test_server.get_url("/timeout/infinite")
    with pytest.raises((FirefoxNavigateTimedOut, BrowserTimeoutError, BrowserNavigationError)):
        firefox_instance.blocking_navigate(url, timeout=3)
    logger.info("  PASS: Timeout correctly raised")

    # Test 4: Normal page after timeout (verify browser still works)
    logger.info("  4. Normal page after timeout...")
    url = test_server.get_url("/simple")
    success = firefox_instance.blocking_navigate(url, timeout=10)
    assert success, "Normal page after timeout failed"
    source = firefox_instance.get_page_source()
    assert "Simple Test Page" in source
    logger.info("  PASS: Normal page after timeout succeeded")

    logger.info("PASS: All sequential scenarios completed successfully")


def test_timeout_with_different_wait_modes():
    """Test timeout behavior with different wait modes (if supported)"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing timeout with different wait modes...")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        FirefoxController.setup_logging(verbose=True)

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=1024", "--height=768"]
        ) as firefox:

            # Test with stuck resource page
            # With wait="none", might succeed immediately
            # With wait="complete", should timeout
            url = test_server.get_url("/timeout/stuck-resource")

            logger.info("  Testing with implicit wait mode...")

            start_time = time.time()

            # Should timeout when waiting for complete page load
            with pytest.raises((FirefoxNavigateTimedOut, BrowserTimeoutError, BrowserNavigationError)):
                firefox.blocking_navigate(url, timeout=5)

            elapsed = time.time() - start_time
            assert 3 <= elapsed <= 7, "Timeout took {}s, expected ~5s".format(elapsed)

            logger.info("  PASS: Timeout correctly occurred after {:.1f}s".format(elapsed))

    finally:
        test_server.stop()


def test_browser_cleanup_with_timeout():
    """Test that browser cleanup works properly even after timeouts"""
    logger = logging.getLogger("FirefoxController")

    logger.info("Testing browser cleanup after timeout scenarios...")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        FirefoxController.setup_logging(verbose=True)

        # Create Firefox instance
        firefox = FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=1024", "--height=768"]
        )

        # Cause a timeout
        url = test_server.get_url("/timeout/infinite")

        try:
            firefox.blocking_navigate(url, timeout=3)
        except (FirefoxNavigateTimedOut, BrowserTimeoutError, BrowserNavigationError):
            logger.info("  PASS: Timeout occurred as expected")

        # Now close Firefox - this should use the SIGINT/SIGKILL escalation
        logger.info("  Closing Firefox with cleanup escalation...")

        start_time = time.time()
        firefox.__exit__(None, None, None)
        elapsed = time.time() - start_time

        # Should complete within reasonable time (not hang forever)
        # With SIGINT timeout=20s and SIGKILL timeout=30s, should be < 60s total
        assert elapsed < 60, "Firefox cleanup took too long: {}s".format(elapsed)

        logger.info("  PASS: Firefox cleanup completed in {:.1f}s".format(elapsed))

    finally:
        test_server.stop()


if __name__ == "__main__":
    # Run pytest when this file is executed directly
    import sys

    # Setup logging for pytest runs
    FirefoxController.setup_logging(verbose=True)

    # Run pytest on this file with verbose output
    sys.exit(pytest.main([__file__, "-v", "-s"]))
