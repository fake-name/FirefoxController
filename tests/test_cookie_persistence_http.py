#!/usr/bin/env python3

"""
Test cookie persistence using HTTP cookies (not WebDriver BiDi API)

This test verifies cookies persist by having the server set them via HTTP headers,
then checking if they're sent back by the browser after a restart.
"""

import pytest
import FirefoxController
import logging
import tempfile
import os
import sys
import shutil

# Add tests directory to path so we can import test_server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_server import TestServer


def test_http_cookies_persist_across_restarts():
    """
    Test that HTTP cookies persist across browser restarts.

    This test uses the server to set and check cookies via HTTP headers,
    completely bypassing the WebDriver BiDi cookie API.
    """

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    # Create a temporary profile directory for this test
    temp_profile_dir = tempfile.mkdtemp(prefix="firefox_http_cookie_test_")
    logger.info("Created temporary profile: {}".format(temp_profile_dir))

    try:
        logger.info("Starting HTTP cookie persistence test...")

        # PHASE 1: First browser session - server sets persistent cookie
        logger.info("PHASE 1: Navigate to page that sets persistent cookie...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            profile_dir=temp_profile_dir,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to page that sets persistent cookie via HTTP header
            source = firefox.blocking_navigate_and_get_source(
                test_server.get_url("/set-persistent-cookie"),
                timeout=15
            )

            # Verify page loaded
            assert "Persistent Cookie Set" in source
            logger.info("[PASS] Navigated to cookie-setting page")

            # Give Firefox time to save cookie
            import time
            time.sleep(2)

            logger.info("Phase 1 complete - Firefox will now close")

        # Firefox is now closed
        logger.info("Firefox closed. Profile persists at: {}".format(temp_profile_dir))

        # PHASE 2: Second browser session - check if cookie is sent back
        logger.info("PHASE 2: Restart browser and check if cookie persists...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            profile_dir=temp_profile_dir,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to page that checks cookies
            source = firefox.blocking_navigate_and_get_source(
                test_server.get_url("/check-cookie"),
                timeout=15
            )

            logger.info("Check-cookie page response: {}".format(source[:500]))

            # Check if our persistent cookie is in the response
            if "persistent_test_cookie=persistent_value" in source:
                logger.info("[PASS] ✓ Cookie PERSISTED across browser restart!")
                logger.info("Phase 2 complete - TEST PASSED")
            else:
                logger.error("[FAIL] ✗ Cookie was NOT found after restart")
                logger.error("Response: {}".format(source))
                raise AssertionError(
                    "Persistent cookie was NOT found after browser restart! "
                    "Expected 'persistent_test_cookie=persistent_value' in response"
                )

    finally:
        # Cleanup
        test_server.stop()

        # Remove temporary profile directory
        # On Windows, Firefox may still hold file locks briefly after termination.
        import time
        time.sleep(1)
        if os.path.exists(temp_profile_dir):
            shutil.rmtree(temp_profile_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run pytest when this file is executed directly
    import pytest
    import sys

    # Setup logging for pytest runs
    FirefoxController.setup_logging(verbose=True)

    # Run pytest on this file
    sys.exit(pytest.main([__file__, "-v"]))
