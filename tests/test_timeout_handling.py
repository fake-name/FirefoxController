#!/usr/bin/env python3
"""
Test script for timeout handling feature
"""

import time
from FirefoxController import FirefoxRemoteDebugInterface, FirefoxNavigateTimedOut, FirefoxResponseNotReceived

print("=" * 60)
print("Testing Timeout Handling Implementation")
print("=" * 60)
print()

# Test 1: Normal navigation with adequate timeout
print("Test 1: Normal navigation with adequate timeout")
print("-" * 60)
try:
    with FirefoxRemoteDebugInterface(headless=True) as firefox:
        print("[PASS] Firefox started")
        result = firefox.blocking_navigate("https://example.com", timeout=30)
        print(f"[PASS] Navigation result: {result}")
        print("[PASS] Test 1 PASSED\n")
except Exception as e:
    print(f"[FAIL] Test 1 FAILED: {e}\n")

# Test 2: Test FirefoxNavigateTimedOut exception is raised
print("Test 2: Navigation timeout exception handling")
print("-" * 60)
try:
    with FirefoxRemoteDebugInterface(headless=True) as firefox:
        print("[PASS] Firefox started")
        # Try to navigate with an impossibly short timeout (1 second)
        # This should trigger the timeout
        try:
            firefox.blocking_navigate("https://httpbin.org/delay/10", timeout=1)
            print("[FAIL] Expected FirefoxNavigateTimedOut but navigation succeeded")
        except FirefoxNavigateTimedOut as e:
            print(f"[PASS] FirefoxNavigateTimedOut raised as expected: {e}")
            print("[PASS] Test 2 PASSED\n")
except Exception as e:
    print(f"[FAIL] Test 2 FAILED with unexpected error: {e}\n")

# Test 3: Test get_page_source with timeout
print("Test 3: Get page source with timeout")
print("-" * 60)
try:
    with FirefoxRemoteDebugInterface(headless=True) as firefox:
        print("[PASS] Firefox started")
        firefox.blocking_navigate("https://example.com", timeout=30)
        print("[PASS] Navigated to example.com")

        source = firefox.get_page_source(timeout=10)
        print(f"[PASS] Got page source ({len(source)} bytes)")
        print(f"[PASS] Source contains 'Example Domain': {'Example Domain' in source}")
        print("[PASS] Test 3 PASSED\n")
except Exception as e:
    print(f"[FAIL] Test 3 FAILED: {e}\n")

# Test 4: Test JavaScript execution with timeout
print("Test 4: JavaScript execution with timeout")
print("-" * 60)
try:
    with FirefoxRemoteDebugInterface(headless=True) as firefox:
        print("[PASS] Firefox started")
        firefox.blocking_navigate("https://example.com", timeout=30)
        print("[PASS] Navigated to example.com")

        # Execute a simple JavaScript statement
        result = firefox.execute_javascript_statement("document.title", timeout=10)
        print(f"[PASS] JavaScript result: {result}")
        print("[PASS] Test 4 PASSED\n")
except Exception as e:
    print(f"[FAIL] Test 4 FAILED: {e}\n")

# Test 5: Test default timeout behavior (uses websocket_timeout)
print("Test 5: Default timeout behavior")
print("-" * 60)
try:
    with FirefoxRemoteDebugInterface(headless=True) as firefox:
        print("[PASS] Firefox started")
        # Navigate without specifying timeout - should use websocket_timeout default (10s)
        firefox.blocking_navigate("https://example.com")
        print("[PASS] Navigation completed (using default websocket_timeout)")

        # Get page source without timeout - should use default
        source = firefox.get_page_source()
        print(f"[PASS] Got page source with default timeout ({len(source)} bytes)")
        print("[PASS] Test 5 PASSED\n")
except Exception as e:
    print(f"[FAIL] Test 5 FAILED: {e}\n")

print("=" * 60)
print("Timeout Handling Tests Complete")
print("=" * 60)
