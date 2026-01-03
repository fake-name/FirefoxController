#!/usr/bin/env python3

"""
Test cookie persistence across browser restarts

This test verifies that cookies persist when Firefox is closed and reopened,
ensuring the privacy preferences fix is working correctly.
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


def test_cookies_persist_across_restarts():
    """
    Test that cookies persist across browser restarts.

    This is the main test for verifying the cookie persistence fix.
    It creates a temporary profile, sets cookies, closes Firefox,
    reopens it with the same profile, and verifies cookies still exist.
    """

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    # Create a temporary profile directory for this test
    temp_profile_dir = tempfile.mkdtemp(prefix="firefox_cookie_test_")
    logger.info("Created temporary profile: {}".format(temp_profile_dir))

    try:
        logger.info("Starting cookie persistence test...")

        # Test cookies we'll set
        # Note: Must include 'expiry' field to make cookies persistent
        # Without expiry, cookies are session cookies and cleared on browser close
        import time
        expiry_time = int(time.time()) + (24 * 60 * 60)  # 24 hours from now

        test_cookies = [
            {
                "name": "persistent_cookie_1",
                "value": "value_1",
                "domain": "127.0.0.1",  # Use 127.0.0.1 instead of localhost for proper persistence
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "sameSite": "lax",
                "expiry": expiry_time
            },
            {
                "name": "persistent_cookie_2",
                "value": "value_2_with_special_chars_!@#$%",
                "domain": "127.0.0.1",  # Use 127.0.0.1 instead of localhost for proper persistence
                "path": "/",
                "httpOnly": True,
                "secure": False,
                "sameSite": "strict",
                "expiry": expiry_time
            }
        ]

        # PHASE 1: First browser session - set cookies
        logger.info("PHASE 1: First browser session - setting cookies...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            profile_dir=temp_profile_dir,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to test page first (required for cookies to work)
            firefox.blocking_navigate_and_get_source(test_server.get_url("/cookies"), timeout=15)
            logger.info("Navigated to test page")

            # Set test cookies
            for cookie in test_cookies:
                success = firefox.set_cookie(cookie)
                assert success, "Failed to set cookie: {}".format(cookie["name"])
                logger.info("Set cookie: {} = {}".format(cookie["name"], cookie["value"]))

            # Verify cookies were set
            cookies_set = firefox.get_cookies()
            logger.info("Total cookies after setting: {}".format(len(cookies_set)))

            # Verify our test cookies exist
            cookie_names = [c.get("name") for c in cookies_set]
            for test_cookie in test_cookies:
                assert test_cookie["name"] in cookie_names, \
                    "Cookie {} was not found after setting".format(test_cookie["name"])
                logger.info("Verified cookie exists: {}".format(test_cookie["name"]))

            logger.info("Phase 1 complete - Firefox will now close")

        # Firefox is now closed (exited context manager)
        logger.info("Firefox closed. Profile persists at: {}".format(temp_profile_dir))

        # PHASE 2: Second browser session - verify cookies persist
        logger.info("PHASE 2: Second browser session - verifying cookies persist...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            profile_dir=temp_profile_dir,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            # Navigate to test page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/cookies"), timeout=15)
            logger.info("Navigated to test page in new session")

            # Get cookies from fresh browser session via API
            cookies_after_restart = firefox.get_cookies()
            logger.info("Total cookies after restart (via API): {}".format(len(cookies_after_restart)))

            # ALSO check cookies.sqlite database directly (more reliable)
            import sqlite3
            cookies_db = os.path.join(temp_profile_dir, "cookies.sqlite")
            db_cookie_count = 0
            db_cookie_names = []

            if os.path.exists(cookies_db):
                conn = sqlite3.connect(cookies_db)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM moz_cookies")
                db_cookie_names = [row[0] for row in cursor.fetchall()]
                db_cookie_count = len(db_cookie_names)
                conn.close()
                logger.info("Total cookies in database: {}".format(db_cookie_count))

            # Use database results if API returns 0 but database has cookies
            if db_cookie_count > 0:
                cookie_names_after = db_cookie_names
                logger.info("Using database cookies for verification")
            else:
                cookie_names_after = [c.get("name") for c in cookies_after_restart]

            for test_cookie in test_cookies:
                assert test_cookie["name"] in cookie_names_after, \
                    "Cookie {} was NOT FOUND after browser restart! Cookies were cleared!".format(
                        test_cookie["name"]
                    )
                logger.info("[PASS] Cookie persisted after restart: {}".format(test_cookie["name"]))

                # Find the cookie and verify its value
                persisted_cookie = next(
                    (c for c in cookies_after_restart if c.get("name") == test_cookie["name"]),
                    None
                )

                assert persisted_cookie is not None, "Cookie {} not found in list".format(
                    test_cookie["name"]
                )

                # Verify value matches
                assert persisted_cookie.get("value") == test_cookie["value"], \
                    "Cookie {} value mismatch: expected '{}', got '{}'".format(
                        test_cookie["name"],
                        test_cookie["value"],
                        persisted_cookie.get("value")
                    )

                logger.info("[PASS] Cookie value correct: {} = {}".format(
                    test_cookie["name"],
                    persisted_cookie.get("value")
                ))

            logger.info("Phase 2 complete - all cookies persisted successfully!")

        logger.info("Cookie persistence test PASSED")

    finally:
        # Cleanup
        test_server.stop()

        # Remove temporary profile directory
        if os.path.exists(temp_profile_dir):
            shutil.rmtree(temp_profile_dir)
            logger.info("Cleaned up temporary profile: {}".format(temp_profile_dir))


def test_cookies_persist_multiple_restarts():
    """
    Test that cookies persist across multiple browser restarts.

    This is a more thorough test that verifies cookies survive
    multiple open/close cycles.
    """

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    # Create a temporary profile directory for this test
    temp_profile_dir = tempfile.mkdtemp(prefix="firefox_multi_restart_test_")
    logger.info("Created temporary profile: {}".format(temp_profile_dir))

    try:
        logger.info("Starting multiple restart cookie persistence test...")

        # Test cookie with expiry time for persistence
        import time
        expiry_time = int(time.time()) + (24 * 60 * 60)  # 24 hours from now

        test_cookie = {
            "name": "multi_restart_cookie",
            "value": "persistent_value",
            "domain": "127.0.0.1",  # Use 127.0.0.1 instead of localhost for proper persistence
            "path": "/",
            "httpOnly": False,
            "secure": False,
            "sameSite": "lax",
            "expiry": expiry_time
        }

        # Number of restart cycles to test
        num_restarts = 3

        for cycle in range(num_restarts):
            logger.info("Restart cycle {}/{}".format(cycle + 1, num_restarts))

            with FirefoxController.FirefoxRemoteDebugInterface(
                headless=False,
                profile_dir=temp_profile_dir,
                additional_options=["--width=800", "--height=600"]
            ) as firefox:

                # Navigate to test page
                firefox.blocking_navigate_and_get_source(test_server.get_url("/cookies"), timeout=15)

                if cycle == 0:
                    # First cycle: set the cookie
                    success = firefox.set_cookie(test_cookie)
                    assert success, "Failed to set cookie in cycle 0"
                    logger.info("Cycle 0: Set cookie {}".format(test_cookie["name"]))
                else:
                    # Subsequent cycles: verify cookie still exists
                    cookies = firefox.get_cookies()
                    cookie_names = [c.get("name") for c in cookies]

                    assert test_cookie["name"] in cookie_names, \
                        "Cookie {} missing after restart cycle {}".format(
                            test_cookie["name"],
                            cycle
                        )

                    # Verify value
                    cookie = next(
                        (c for c in cookies if c.get("name") == test_cookie["name"]),
                        None
                    )
                    assert cookie.get("value") == test_cookie["value"], \
                        "Cookie value changed after restart cycle {}".format(cycle)

                    logger.info("[PASS] Cycle {}: Cookie still exists with correct value".format(cycle))

        logger.info("Multiple restart test PASSED - cookie survived {} restart cycles".format(
            num_restarts
        ))

    finally:
        # Cleanup
        test_server.stop()

        # Remove temporary profile directory
        if os.path.exists(temp_profile_dir):
            shutil.rmtree(temp_profile_dir)
            logger.info("Cleaned up temporary profile: {}".format(temp_profile_dir))


def test_privacy_preferences_are_set():
    """
    Test that the privacy preferences are correctly set in the profile.

    This test verifies that the _ensure_cookie_persistence() method
    is working and setting the correct preferences.
    """

    logger = logging.getLogger("FirefoxController")

    # Create a temporary profile directory for this test
    temp_profile_dir = tempfile.mkdtemp(prefix="firefox_prefs_test_")
    logger.info("Created temporary profile: {}".format(temp_profile_dir))

    try:
        logger.info("Starting privacy preferences test...")

        # Start Firefox with the temporary profile
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            profile_dir=temp_profile_dir,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            logger.info("Firefox started with temporary profile")

            # Give Firefox a moment to fully initialize
            import time
            time.sleep(2)

        # Firefox is now closed, check the prefs.js file
        prefs_file = os.path.join(temp_profile_dir, "prefs.js")

        assert os.path.exists(prefs_file), "prefs.js file not created"
        logger.info("Found prefs.js file: {}".format(prefs_file))

        # Read the prefs.js file
        with open(prefs_file, 'r') as f:
            prefs_content = f.read()

        # Check that cookie persistence preferences are set
        required_prefs = [
            'privacy.sanitize.sanitizeOnShutdown", false',
            'privacy.clearOnShutdown.cookies", false',
            'privacy.clearOnShutdown.cache", false',
            'privacy.clearOnShutdown.sessions", false',
            'privacy.clearOnShutdown.formdata", false',
        ]

        for pref in required_prefs:
            assert pref in prefs_content, \
                "Required preference not found in prefs.js: {}".format(pref)
            logger.info("[PASS] Found preference: {}".format(pref.split('"')[0]))

        logger.info("Privacy preferences test PASSED - all required preferences set correctly")

    finally:
        # Remove temporary profile directory
        if os.path.exists(temp_profile_dir):
            shutil.rmtree(temp_profile_dir)
            logger.info("Cleaned up temporary profile: {}".format(temp_profile_dir))


if __name__ == "__main__":
    # Run pytest when this file is executed directly
    import pytest
    import sys

    # Setup logging for pytest runs
    FirefoxController.setup_logging(verbose=True)

    # Run pytest on this file
    sys.exit(pytest.main([__file__, "-v"]))
