#!/usr/bin/env python3

"""
Test script for console logging feature

Tests the WebDriver-BiDi log.entryAdded event capture functionality
"""

import pytest
import FirefoxController
from FirefoxController import ConsoleLogEntry
import logging
import time
import sys
import os

# Add tests directory to path so we can import test_server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_server import TestServer


def test_console_logging_basic():
    """Test basic console message capture"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging basic test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable console logging
            result = firefox.enable_console_logging()
            assert result, "enable_console_logging() should return True"

            # Navigate to the console test page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/console"), timeout=15)

            # Wait for console messages to be generated
            time.sleep(1)
            firefox.poll_console_events()

            # Get all console messages
            messages = firefox.get_console_messages()
            logger.info("Captured {} console messages".format(len(messages)))

            for msg in messages:
                logger.info("  [{}] {}".format(msg.level, msg.text))

            # Should have captured at least some messages
            assert len(messages) > 0, "Should have captured at least one console message"

            # Verify we captured different log levels
            levels = [msg.level for msg in messages]
            logger.info("Captured levels: {}".format(set(levels)))

            # Disable console logging
            firefox.disable_console_logging()

            logger.info("Console logging basic test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_filter_by_level():
    """Test filtering console messages by level"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging filter by level test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable console logging
            firefox.enable_console_logging()

            # Navigate to the console test page (generates various log levels)
            firefox.blocking_navigate_and_get_source(test_server.get_url("/console"), timeout=15)

            # Wait for console messages
            time.sleep(1)
            firefox.poll_console_events()

            # Get all messages first
            all_messages = firefox.get_console_messages()
            logger.info("Total messages: {}".format(len(all_messages)))

            # Test filtering by error level
            errors = firefox.get_console_errors()
            logger.info("Error messages: {}".format(len(errors)))

            for msg in errors:
                assert msg.level == "error", "All error messages should have error level"

            # Test filtering by warn level
            warnings = firefox.get_console_warnings()
            logger.info("Warning messages: {}".format(len(warnings)))

            for msg in warnings:
                assert msg.level == "warn", "All warning messages should have warn level"

            # Test custom level filter
            info_messages = firefox.get_console_messages(level='info')
            logger.info("Info messages: {}".format(len(info_messages)))

            for msg in info_messages:
                assert msg.level == "info", "All info messages should have info level"

            logger.info("Console logging filter by level test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_clear_messages():
    """Test clearing console messages"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging clear messages test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable console logging
            firefox.enable_console_logging()

            # Navigate to generate messages
            firefox.blocking_navigate_and_get_source(test_server.get_url("/console"), timeout=15)
            time.sleep(1)
            firefox.poll_console_events()

            # Should have some messages
            messages_before = firefox.get_console_messages()
            assert len(messages_before) > 0, "Should have captured some messages"
            logger.info("Messages before clear: {}".format(len(messages_before)))

            # Clear messages
            firefox.clear_console_messages()

            # Should have no messages
            messages_after = firefox.get_console_messages()
            assert len(messages_after) == 0, "Should have no messages after clearing"
            logger.info("Messages after clear: {}".format(len(messages_after)))

            # Navigate to generate more messages
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Execute some JavaScript to generate new messages
            firefox.execute_javascript_statement('console.log("New message after clear")')
            time.sleep(0.5)
            firefox.poll_console_events()

            # Should have the new message
            new_messages = firefox.get_console_messages()
            logger.info("Messages after new navigation: {}".format(len(new_messages)))

            has_new_message = any("New message after clear" in msg.text for msg in new_messages)
            assert has_new_message, "Should capture new messages after clearing"

            logger.info("Console logging clear messages test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_wait_for_message():
    """Test waiting for a specific console message"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging wait for message test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable console logging
            firefox.enable_console_logging()

            # Navigate to a simple page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Trigger a console message via JavaScript
            firefox.execute_javascript_statement('setTimeout(() => console.log("Delayed test message"), 500)')

            # Wait for the specific message
            msg = firefox.wait_for_console_message(text_pattern="Delayed test message", timeout=5)

            assert msg is not None, "Should have received the delayed message"
            assert "Delayed test message" in msg.text, "Message text should match"
            logger.info("Received expected message: {}".format(msg.text))

            # Test timeout when message doesn't appear
            nonexistent_msg = firefox.wait_for_console_message(
                text_pattern="This message will never appear",
                timeout=1
            )
            assert nonexistent_msg is None, "Should timeout for non-existent message"
            logger.info("Correctly timed out for non-existent message")

            logger.info("Console logging wait for message test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_execute_javascript():
    """Test capturing console messages from executed JavaScript"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging execute JavaScript test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable console logging
            firefox.enable_console_logging()

            # Navigate to a simple page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Clear any existing messages
            firefox.clear_console_messages()

            # Execute JavaScript that logs messages
            firefox.execute_javascript_statement('console.log("Test log message")')
            firefox.execute_javascript_statement('console.warn("Test warn message")')
            firefox.execute_javascript_statement('console.error("Test error message")')

            # Wait for messages
            time.sleep(0.5)
            firefox.poll_console_events()

            # Get messages
            messages = firefox.get_console_messages()
            logger.info("Captured {} messages from executed JavaScript".format(len(messages)))

            for msg in messages:
                logger.info("  [{}] {}".format(msg.level, msg.text))

            # Verify we got all the messages
            texts = [msg.text for msg in messages]

            has_log = any("Test log message" in t for t in texts)
            has_warn = any("Test warn message" in t for t in texts)
            has_error = any("Test error message" in t for t in texts)

            assert has_log, "Should have captured log message"
            assert has_warn, "Should have captured warn message"
            assert has_error, "Should have captured error message"

            logger.info("Console logging execute JavaScript test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_disable_clears_nothing():
    """Test that disabling console logging preserves captured messages"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging disable test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable console logging
            firefox.enable_console_logging()

            # Navigate to generate messages
            firefox.blocking_navigate_and_get_source(test_server.get_url("/console"), timeout=15)
            time.sleep(1)
            firefox.poll_console_events()

            # Should have some messages
            messages_before = firefox.get_console_messages()
            count_before = len(messages_before)
            assert count_before > 0, "Should have captured some messages"
            logger.info("Messages before disable: {}".format(count_before))

            # Disable console logging
            firefox.disable_console_logging()

            # Messages should still be there (preserved)
            messages_after = firefox.get_console_messages(poll_first=False)
            count_after = len(messages_after)
            logger.info("Messages after disable: {}".format(count_after))

            assert count_after == count_before, "Messages should be preserved after disabling"

            logger.info("Console logging disable test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_enable_disable_reenable():
    """Test enabling, disabling, and re-enabling console logging"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging re-enable test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Navigate to a page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # First enable
            firefox.enable_console_logging()
            firefox.execute_javascript_statement('console.log("First enable message")')
            time.sleep(0.5)
            firefox.poll_console_events()

            messages1 = firefox.get_console_messages()
            assert any("First enable message" in m.text for m in messages1), "Should have first message"
            logger.info("First enable: {} messages".format(len(messages1)))

            # Disable
            firefox.disable_console_logging()

            # Re-enable
            firefox.enable_console_logging()

            # Clear old messages to start fresh (drains any stale events)
            firefox.poll_console_events()  # Process any buffered events
            firefox.clear_console_messages()

            # Execute more JS - should be captured
            firefox.execute_javascript_statement('console.log("After re-enable message")')
            time.sleep(0.5)
            firefox.poll_console_events()

            messages2 = firefox.get_console_messages()
            logger.info("After re-enable: {} messages".format(len(messages2)))

            # Should have the new message
            has_reenable_msg = any("After re-enable message" in m.text for m in messages2)
            assert has_reenable_msg, "Should have message after re-enable"

            logger.info("Console logging re-enable test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_has_errors_check():
    """Test the has_console_errors convenience method"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging has errors check test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable console logging
            firefox.enable_console_logging()

            # Navigate to a simple page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Clear any existing messages
            firefox.clear_console_messages()

            # Initially should have no errors
            assert not firefox.has_console_errors(), "Should have no errors initially"

            # Generate a non-error message
            firefox.execute_javascript_statement('console.log("Not an error")')
            time.sleep(0.5)
            firefox.poll_console_events()

            # Still should have no errors
            assert not firefox.has_console_errors(), "Should have no errors after log"

            # Generate an error
            firefox.execute_javascript_statement('console.error("This is an error")')
            time.sleep(0.5)
            firefox.poll_console_events()

            # Now should have errors
            assert firefox.has_console_errors(), "Should have errors after console.error"

            logger.info("Console logging has errors check test completed successfully")

    finally:
        test_server.stop()


def test_console_log_entry_structure():
    """Test the ConsoleLogEntry structure and methods"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console log entry structure test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Enable console logging
            firefox.enable_console_logging()

            # Navigate to a simple page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Clear and generate a new message
            firefox.clear_console_messages()
            firefox.execute_javascript_statement('console.log("Structure test message")')
            time.sleep(0.5)
            firefox.poll_console_events()

            # Get messages
            messages = firefox.get_console_messages()
            assert len(messages) > 0, "Should have at least one message"

            # Check the structure
            msg = messages[0]
            assert isinstance(msg, ConsoleLogEntry), "Message should be a ConsoleLogEntry"

            # Check attributes exist
            assert hasattr(msg, 'level'), "Should have level attribute"
            assert hasattr(msg, 'source'), "Should have source attribute"
            assert hasattr(msg, 'text'), "Should have text attribute"
            assert hasattr(msg, 'timestamp'), "Should have timestamp attribute"

            logger.info("Message attributes:")
            logger.info("  level: {}".format(msg.level))
            logger.info("  source: {}".format(msg.source))
            logger.info("  text: {}".format(msg.text))
            logger.info("  timestamp: {}".format(msg.timestamp))

            # Test to_dict method
            msg_dict = msg.to_dict()
            assert isinstance(msg_dict, dict), "to_dict should return a dict"
            assert 'level' in msg_dict, "Dict should have level"
            assert 'text' in msg_dict, "Dict should have text"

            # Test __str__ method
            msg_str = str(msg)
            assert msg.level.upper() in msg_str, "String should contain level"
            logger.info("String representation: {}".format(msg_str))

            # Test __repr__ method
            msg_repr = repr(msg)
            assert "ConsoleLogEntry" in msg_repr, "Repr should contain class name"
            logger.info("Repr: {}".format(msg_repr))

            logger.info("Console log entry structure test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_multiple_tabs_independent():
    """Test that console logging is independent per tab"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging multiple tabs independent test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Navigate main tab to a page
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Create a second tab
            tab2 = firefox.new_tab(test_server.get_url("/javascript"))
            firefox.poll_events()

            # Enable logging on main tab only
            firefox.enable_console_logging()

            # Generate message on main tab - should be logged
            firefox.execute_javascript_statement('console.log("Main tab message")')
            time.sleep(0.5)
            firefox.poll_console_events()

            # Generate message on tab2 - should NOT be logged (logging not enabled)
            tab2.execute_javascript_statement('console.log("Tab2 message")')
            time.sleep(0.5)
            tab2.poll_events()

            # Check main tab has captured messages
            main_tab_messages = firefox.get_console_messages()
            logger.info("Main tab captured {} messages".format(len(main_tab_messages)))

            main_has_msg = any("Main tab message" in m.text for m in main_tab_messages)
            assert main_has_msg, "Main tab should have its message"

            # Main tab should NOT have tab2's messages
            main_has_tab2_msg = any("Tab2 message" in m.text for m in main_tab_messages)
            assert not main_has_tab2_msg, "Main tab should not have tab2's messages"

            # Check tab2 has no captured messages (logging not enabled)
            tab2_messages = tab2.get_console_messages(poll_first=False)
            logger.info("Tab2 captured {} messages".format(len(tab2_messages)))
            assert len(tab2_messages) == 0, "Tab2 should have no messages (logging not enabled)"

            # Now enable logging on tab2
            tab2.enable_console_logging()

            # Clear tab2's message buffer
            tab2.clear_console_messages()

            # Generate message on tab2 - should now be logged
            tab2.execute_javascript_statement('console.log("Tab2 message after enable")')
            time.sleep(0.5)
            tab2.poll_console_events()

            # Check tab2 now has captured messages
            tab2_messages_after = tab2.get_console_messages()
            logger.info("Tab2 captured {} messages after enabling".format(len(tab2_messages_after)))

            tab2_has_msg = any("Tab2 message after enable" in m.text for m in tab2_messages_after)
            assert tab2_has_msg, "Tab2 should have its message after enabling"

            # Tab2 should NOT have main tab's messages
            tab2_has_main_msg = any("Main tab message" in m.text for m in tab2_messages_after)
            assert not tab2_has_main_msg, "Tab2 should not have main tab's messages"

            logger.info("Console logging multiple tabs independent test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_both_tabs_enabled():
    """Test console logging with both tabs enabled"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging both tabs enabled test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Create second tab
            tab2 = firefox.new_tab(test_server.get_url("/simple"))

            # Enable logging on both tabs
            firefox.enable_console_logging()
            tab2.enable_console_logging()

            # Generate unique messages in each tab
            firefox.execute_javascript_statement('console.log("Tab1 unique message")')
            tab2.execute_javascript_statement('console.log("Tab2 unique message")')

            # Wait for messages
            time.sleep(0.5)
            firefox.poll_console_events()
            tab2.poll_console_events()

            # Get messages from both tabs
            tab1_messages = firefox.get_console_messages()
            tab2_messages = tab2.get_console_messages()

            logger.info("Tab1 captured {} messages".format(len(tab1_messages)))
            logger.info("Tab2 captured {} messages".format(len(tab2_messages)))

            # Each tab should have its own message
            tab1_has_own = any("Tab1 unique message" in m.text for m in tab1_messages)
            tab2_has_own = any("Tab2 unique message" in m.text for m in tab2_messages)

            assert tab1_has_own, "Tab1 should have its own message"
            assert tab2_has_own, "Tab2 should have its own message"

            # Messages should be isolated (tab1 shouldn't have tab2's and vice versa)
            tab1_has_tab2 = any("Tab2 unique message" in m.text for m in tab1_messages)
            tab2_has_tab1 = any("Tab1 unique message" in m.text for m in tab2_messages)

            assert not tab1_has_tab2, "Tab1 should not have tab2's message"
            assert not tab2_has_tab1, "Tab2 should not have tab1's message"

            logger.info("Console logging both tabs enabled test completed successfully")

    finally:
        test_server.stop()


def test_console_logging_disable_one_tab_others_continue():
    """Test that disabling logging on one tab doesn't affect others"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting console logging disable one tab test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False
        ) as firefox:

            # Create second tab
            tab2 = firefox.new_tab(test_server.get_url("/simple"))

            # Enable logging on both tabs
            firefox.enable_console_logging()
            tab2.enable_console_logging()

            # Generate messages on both
            firefox.execute_javascript_statement('console.log("Tab1 before disable")')
            tab2.execute_javascript_statement('console.log("Tab2 before disable")')
            time.sleep(0.5)
            firefox.poll_console_events()
            tab2.poll_console_events()

            # Both should have messages
            assert len(firefox.get_console_messages()) > 0
            assert len(tab2.get_console_messages()) > 0

            logger.info("Before disable - Tab1: {} messages, Tab2: {} messages".format(
                len(firefox.get_console_messages()),
                len(tab2.get_console_messages())
            ))

            # Disable logging on tab1 only
            firefox.disable_console_logging()

            # Clear tab2 messages to make checking easier
            tab2.clear_console_messages()

            # Generate messages again
            firefox.execute_javascript_statement('console.log("Tab1 after disable")')
            tab2.execute_javascript_statement('console.log("Tab2 after disable")')
            time.sleep(0.5)
            tab2.poll_console_events()

            # Tab2 should have captured the new message
            tab2_messages = tab2.get_console_messages()
            logger.info("After disable - Tab2: {} messages".format(len(tab2_messages)))

            tab2_has_new = any("Tab2 after disable" in m.text for m in tab2_messages)
            assert tab2_has_new, "Tab2 should still be capturing messages"

            logger.info("Console logging disable one tab test completed successfully")

    finally:
        test_server.stop()


if __name__ == "__main__":
    # Setup logging for pytest runs
    FirefoxController.setup_logging(verbose=True)

    # Run pytest on this file
    sys.exit(pytest.main([__file__, "-v"]))
