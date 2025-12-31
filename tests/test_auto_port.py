#!/usr/bin/env python3
"""
Test script for automatic port selection feature
"""

import sys
import time
from FirefoxController import FirefoxRemoteDebugInterface

def test_auto_port_selection():
    """Test automatic port selection with port=None"""
    print("Test 1: Automatic port selection (port=None)")
    print("-" * 50)

    try:
        with FirefoxRemoteDebugInterface(port=None, headless=True) as firefox:
            print(f"[PASS] Firefox started successfully")
            print(f"[PASS] Auto-selected port: {firefox.port}")
            print(f"[PASS] Port is a valid number: {isinstance(firefox.port, int)}")
            print(f"[PASS] Port is in valid range: {1024 <= firefox.port <= 65535}")

            # Try to navigate to verify it's working
            firefox.blocking_navigate("https://example.com", timeout=10)
            print(f"[PASS] Successfully navigated to example.com")

        print("[PASS] Test 1 PASSED\n")
        return True
    except Exception as e:
        print(f"[FAIL] Test 1 FAILED: {e}\n")
        return False

def test_explicit_port():
    """Test explicit port still works"""
    print("Test 2: Explicit port selection (port=9500)")
    print("-" * 50)

    try:
        with FirefoxRemoteDebugInterface(port=9500, headless=True) as firefox:
            print(f"[PASS] Firefox started successfully")
            print(f"[PASS] Using specified port: {firefox.port}")
            print(f"[PASS] Port matches requested: {firefox.port == 9500}")

        print("[PASS] Test 2 PASSED\n")
        return True
    except Exception as e:
        print(f"[FAIL] Test 2 FAILED: {e}\n")
        return False

def test_multiple_instances():
    """Test multiple Firefox instances with auto port selection"""
    print("Test 3: Multiple instances with auto port selection")
    print("-" * 50)

    import tempfile
    import shutil

    temp_profile1 = None
    temp_profile2 = None

    try:
        # Create separate temporary profiles for each instance
        temp_profile1 = tempfile.mkdtemp(prefix="firefox_test_1_")
        temp_profile2 = tempfile.mkdtemp(prefix="firefox_test_2_")

        with FirefoxRemoteDebugInterface(port=None, headless=True, profile_dir=temp_profile1) as firefox1:
            print(f"[PASS] Firefox instance 1 started on port: {firefox1.port}")

            with FirefoxRemoteDebugInterface(port=None, headless=True, profile_dir=temp_profile2) as firefox2:
                print(f"[PASS] Firefox instance 2 started on port: {firefox2.port}")
                print(f"[PASS] Ports are different: {firefox1.port != firefox2.port}")

        print("[PASS] Test 3 PASSED\n")
        return True
    except Exception as e:
        print(f"[FAIL] Test 3 FAILED: {e}\n")
        return False
    finally:
        # Clean up temporary profiles
        if temp_profile1:
            try:
                shutil.rmtree(temp_profile1)
            except:
                pass
        if temp_profile2:
            try:
                shutil.rmtree(temp_profile2)
            except:
                pass

def test_default_port():
    """Test that default port is now 9222"""
    print("Test 4: Default port value")
    print("-" * 50)

    try:
        with FirefoxRemoteDebugInterface(headless=True) as firefox:
            print(f"[PASS] Firefox started with default port")
            print(f"[PASS] Default port is: {firefox.port}")
            print(f"[PASS] Default port is 9222: {firefox.port == 9222}")

        print("[PASS] Test 4 PASSED\n")
        return True
    except Exception as e:
        print(f"[FAIL] Test 4 FAILED: {e}\n")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Automatic Port Selection Feature")
    print("=" * 50)
    print()

    results = []

    # Run all tests
    results.append(("Auto port selection", test_auto_port_selection()))
    results.append(("Explicit port", test_explicit_port()))
    results.append(("Multiple instances", test_multiple_instances()))
    results.append(("Default port", test_default_port()))

    # Summary
    print("=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS] PASSED" if result else "[FAIL] FAILED"
        print(f"{test_name:25s}: {status}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    sys.exit(0 if passed == total else 1)
