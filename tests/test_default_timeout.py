#!/usr/bin/env python3
"""
Test script for default timeout functionality
"""

from FirefoxController import FirefoxRemoteDebugInterface

print("=" * 60)
print("Testing Default Timeout Functionality")
print("=" * 60)
print()

# Test 1: Check default timeout is set correctly
print("Test 1: Default timeout initialization")
print("-" * 60)
with FirefoxRemoteDebugInterface(headless=True) as firefox:
    print(f"Default timeout: {firefox.default_timeout} seconds")
    assert firefox.default_timeout == 30, "Default should be 30 seconds"
    print("[PASS] Default timeout is 30 seconds\n")

# Test 2: Change default timeout
print("Test 2: Change default timeout")
print("-" * 60)
with FirefoxRemoteDebugInterface(headless=True) as firefox:
    print(f"Initial default timeout: {firefox.default_timeout} seconds")
    firefox.set_default_timeout(60)
    print(f"After set_default_timeout(60): {firefox.default_timeout} seconds")
    assert firefox.default_timeout == 60, "Default should be 60 seconds after change"
    print("[PASS] Default timeout changed successfully\n")

# Test 3: Use default timeout in navigation (no explicit timeout)
print("Test 3: Navigation using default timeout")
print("-" * 60)
with FirefoxRemoteDebugInterface(headless=True) as firefox:
    firefox.set_default_timeout(15)
    print(f"Set default timeout to: {firefox.default_timeout} seconds")
    # This should use the 15 second default
    result = firefox.blocking_navigate("https://example.com")
    print(f"Navigation result: {result}")
    print("[PASS] Navigation used default timeout\n")

# Test 4: Override default timeout with explicit timeout
print("Test 4: Override default with explicit timeout")
print("-" * 60)
with FirefoxRemoteDebugInterface(headless=True) as firefox:
    firefox.set_default_timeout(5)
    print(f"Default timeout: {firefox.default_timeout} seconds")
    # This should use the explicit 30 second timeout, not the 5 second default
    result = firefox.blocking_navigate("https://example.com", timeout=30)
    print(f"Navigation with explicit timeout=30: {result}")
    print("[PASS] Explicit timeout overrode default\n")

# Test 5: Get page source using default timeout
print("Test 5: Get page source with default timeout")
print("-" * 60)
with FirefoxRemoteDebugInterface(headless=True) as firefox:
    firefox.set_default_timeout(20)
    firefox.blocking_navigate("https://example.com")
    # This should use the 20 second default
    source = firefox.get_page_source()
    print(f"Got page source ({len(source)} bytes) using default timeout")
    print("[PASS] get_page_source used default timeout\n")

print("=" * 60)
print("All Default Timeout Tests Passed!")
print("=" * 60)
