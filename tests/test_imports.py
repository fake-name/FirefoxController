#!/usr/bin/env python3

"""
Simple import test for FirefoxController

This script tests that all modules can be imported correctly.
"""

def test_imports():
    """Test that all FirefoxController modules can be imported"""
    print("🧪 Testing FirefoxController imports...")
    
    try:
        # Test main package import
        import FirefoxController
        print("✅ FirefoxController main package imported")
        
        # Test individual modules
        from FirefoxController import FirefoxRemoteDebugInterface
        print("✅ FirefoxRemoteDebugInterface imported")
        
        from FirefoxController import FirefoxExecutionManager
        print("✅ FirefoxExecutionManager imported")
        
        from FirefoxController import (
            FirefoxControllerException,
            FirefoxStartupException,
            FirefoxConnectFailure,
            FirefoxCommunicationsError,
            FirefoxTabNotFoundError,
            FirefoxError,
            FirefoxDiedError,
            FirefoxNavigateTimedOut,
            FirefoxResponseNotReceived
        )
        print("✅ All exceptions imported")
        
        from FirefoxController import setup_logging, main
        print("✅ Utility functions imported")
        
        # Test that the interface has all expected methods
        interface = FirefoxRemoteDebugInterface
        expected_methods = [
            'blocking_navigate_and_get_source',
            'get_page_source',
            'get_current_url',
            'get_page_url_title',
            'take_screenshot',
            'execute_javascript_statement',
            'execute_javascript_function',
            'navigate_to',
            'blocking_navigate',
            'get_cookies',
            'set_cookie',
            'clear_cookies',
            'find_element',
            'click_element',
            'click_link_containing_url',
            'scroll_page',
            'get_rendered_page_source',
            'wait_for_dom_idle',
            'new_tab'
        ]
        
        for method in expected_methods:
            if hasattr(interface, method):
                print(f"✅ Method {method} found")
            else:
                print(f"❌ Method {method} missing")
                return False
        
        print("🎉 All imports and methods verified successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n🎉 Import test PASSED")
        exit(0)
    else:
        print("\n❌ Import test FAILED")
        exit(1)