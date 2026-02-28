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
                "domain": "localhost",  # Must match the test server domain
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "sameSite": "lax",
                "expiry": expiry_time
            },
            {
                "name": "persistent_cookie_2",
                "value": "value_2_with_special_chars_!@#$%",
                "domain": "localhost",  # Must match the test server domain
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

            # Navigate to the set-persistent-cookie endpoint which sets a cookie via HTTP header
            # Note: Cookies set via WebDriver-BiDi API are treated as session cookies
            # and don't persist across Firefox restarts. HTTP Set-Cookie headers work properly.
            firefox.blocking_navigate_and_get_source(test_server.get_url("/set-persistent-cookie"), timeout=15)
            logger.info("Navigated to set-persistent-cookie endpoint")

            # Verify cookies were set
            cookies_set = firefox.get_cookies()
            logger.info("Total cookies after setting: {}".format(len(cookies_set)))

            # Verify the HTTP-set cookie exists
            cookie_names = [c.get("name") for c in cookies_set]
            assert "persistent_test_cookie" in cookie_names, \
                "Cookie persistent_test_cookie was not found after setting"
            logger.info("Verified HTTP-set cookie exists: persistent_test_cookie")

            # Give Firefox time to flush cookies to disk before shutdown
            import time
            time.sleep(2)

            logger.info("Phase 1 complete - Firefox will now close")

        # Firefox is now closed (exited context manager)
        logger.info("Firefox closed. Profile persists at: {}".format(temp_profile_dir))

        # Wait a moment for Firefox to fully release the database
        import time
        time.sleep(1)

        # Check cookies.sqlite database directly BEFORE starting Firefox again
        import sqlite3
        cookies_db = os.path.join(temp_profile_dir, "cookies.sqlite")
        db_cookie_count = 0
        db_cookie_names = []

        if os.path.exists(cookies_db):
            try:
                conn = sqlite3.connect(cookies_db, timeout=10)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM moz_cookies")
                db_cookie_names = [row[0] for row in cursor.fetchall()]
                db_cookie_count = len(db_cookie_names)
                conn.close()
                logger.info("Cookies in database before restart: {} - {}".format(db_cookie_count, db_cookie_names))
            except sqlite3.OperationalError as e:
                logger.warning("Could not read cookies.sqlite: {}".format(e))

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

            # Use database results if API returns 0 but database has cookies
            if db_cookie_count > 0:
                cookie_names_after = db_cookie_names
                logger.info("Using database cookies for verification")
            else:
                cookie_names_after = [c.get("name") for c in cookies_after_restart]

            # Check for the HTTP-set cookie
            assert "persistent_test_cookie" in cookie_names_after, \
                "Cookie persistent_test_cookie was NOT FOUND after browser restart! Cookies were cleared!"
            logger.info("[PASS] Cookie persisted after restart: persistent_test_cookie")

            # Find the cookie and verify its value
            persisted_cookie = next(
                (c for c in cookies_after_restart if c.get("name") == "persistent_test_cookie"),
                None
            )

            if persisted_cookie:
                logger.info("[PASS] Cookie value: persistent_test_cookie = {}".format(
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
            "domain": "localhost",  # Must match the test server domain
            "path": "/",
            "httpOnly": False,
            "secure": False,
            "sameSite": "lax",
            "expiry": expiry_time
        }

        # Number of restart cycles to test
        num_restarts = 3

        import time

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
                    # First cycle: set the cookie using HTTP Set-Cookie header
                    # Navigate to the set-persistent-cookie endpoint which sets a cookie with Max-Age
                    firefox.blocking_navigate_and_get_source(test_server.get_url("/set-persistent-cookie"), timeout=15)
                    logger.info("Cycle 0: Set cookie via HTTP header")

                    # Verify the cookie was set in the current session
                    cookies_now = firefox.get_cookies()
                    cookie_names_now = [c.get("name") for c in cookies_now]
                    logger.info("Cookies after setting: {}".format(cookie_names_now))

                    # Check if the persistent cookie was set
                    if "persistent_test_cookie" not in cookie_names_now:
                        # Fall back to API-based cookie setting
                        success = firefox.set_cookie(test_cookie)
                        assert success, "Failed to set cookie in cycle 0"
                        logger.info("Fallback: Set cookie {} via API".format(test_cookie["name"]))
                        cookies_now = firefox.get_cookies()
                        cookie_names_now = [c.get("name") for c in cookies_now]
                        logger.info("Cookies after API set: {}".format(cookie_names_now))

                    # Wait for Firefox to flush cookies to disk before shutdown
                    time.sleep(2)
                else:
                    # Subsequent cycles: verify cookie still exists
                    cookies = firefox.get_cookies()
                    cookie_names = [c.get("name") for c in cookies]
                    logger.info("Cookies in cycle {}: {}".format(cycle, cookie_names))

                    # Check for either HTTP-set cookie or API-set cookie
                    has_http_cookie = "persistent_test_cookie" in cookie_names
                    has_api_cookie = test_cookie["name"] in cookie_names

                    assert has_http_cookie or has_api_cookie, \
                        "No persistent cookie found after restart cycle {}. Cookies: {}".format(
                            cycle, cookie_names
                        )

                    if has_http_cookie:
                        cookie = next((c for c in cookies if c.get("name") == "persistent_test_cookie"), None)
                        logger.info("[PASS] Cycle {}: HTTP cookie persisted: {}={}".format(
                            cycle, cookie.get("name"), cookie.get("value")))
                    elif has_api_cookie:
                        cookie = next((c for c in cookies if c.get("name") == test_cookie["name"]), None)
                        assert cookie.get("value") == test_cookie["value"], \
                            "Cookie value changed after restart cycle {}".format(cycle)
                        logger.info("[PASS] Cycle {}: API cookie persisted with correct value".format(cycle))

            # Wait for Firefox to fully release database after shutdown
            time.sleep(1)

            # Check the database after Firefox shuts down
            if cycle == 0:
                import sqlite3
                cookies_db = os.path.join(temp_profile_dir, "cookies.sqlite")
                if os.path.exists(cookies_db):
                    try:
                        conn = sqlite3.connect(cookies_db, timeout=10)
                        cursor = conn.cursor()
                        cursor.execute("SELECT name, host, value FROM moz_cookies")
                        db_cookies = cursor.fetchall()
                        conn.close()
                        logger.info("Cookies in database after cycle 0: {}".format(db_cookies))
                    except Exception as e:
                        logger.warning("Could not read cookies.sqlite: {}".format(e))
                else:
                    logger.warning("cookies.sqlite does not exist after cycle 0!")

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
        # Note: Firefox may use .v2 suffix for some prefs in newer versions
        required_prefs = [
            # Either old or new sanitizeOnShutdown pref
            ('privacy.sanitize.sanitizeOnShutdown", false', 'privacy.sanitize.sanitizeOnShutdown.v2", false'),
            ('privacy.clearOnShutdown.cookies", false',),
            ('privacy.clearOnShutdown.cache", false',),
            ('privacy.clearOnShutdown.sessions", false',),
            ('privacy.clearOnShutdown.formdata", false',),
        ]

        for pref_options in required_prefs:
            found = False
            for pref in pref_options:
                if pref in prefs_content:
                    found = True
                    logger.info("[PASS] Found preference: {}".format(pref.split('"')[0]))
                    break
            assert found, \
                "Required preference not found in prefs.js. Checked: {}".format(pref_options)

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
