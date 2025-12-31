#!/usr/bin/env python3
"""
Debug test for automatic port selection
"""

import logging
from FirefoxController import FirefoxRemoteDebugInterface, find_available_port

# Enable verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("Testing find_available_port() function directly...")
try:
    port = find_available_port()
    print(f"[PASS] find_available_port() returned: {port}")
    print(f"[PASS] Port is valid: {1024 <= port <= 65535}")
except Exception as e:
    print(f"[FAIL] find_available_port() failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("Testing FirefoxRemoteDebugInterface with port=None...")
print("="*50 + "\n")

try:
    with FirefoxRemoteDebugInterface(port=None, headless=True) as firefox:
        print(f"\n[PASS] Firefox started on port: {firefox.port}")
        print(f"[PASS] Manager port: {firefox.manager.port}")
except Exception as e:
    print(f"\n[FAIL] Failed: {e}")
    import traceback
    traceback.print_exc()
