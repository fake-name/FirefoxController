#!/usr/bin/env python3

"""
Live WebDriver-BiDi tests that run against a real Firefox instance

This test suite verifies WebDriver-BiDi functionality with actual Firefox browser instances.
"""

import pytest
import time
import base64
from FirefoxController.interface import FirefoxRemoteDebugInterface


class TestWebDriverBiDiLiveIntegration:
    """Test WebDriver-BiDi functionality with live Firefox instances"""
    
    @pytest.fixture(scope="function")
    def firefox_interface(self):
        """Fixture that provides a Firefox interface for testing"""
        # Use headless mode and a high port to avoid conflicts
        with FirefoxRemoteDebugInterface(
            headless=True,
            port=6080 + hash(time.time()) % 1000  # Random port to avoid conflicts
        ) as interface:
            yield interface
    
    def test_bidi_navigate_live(self, firefox_interface):
        """Test WebDriver-BiDi navigation with live Firefox"""
        # Navigate using WebDriver-BiDi
        result = firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Verify navigation result
        assert result is not None
        assert isinstance(result, dict)
        
        # Get current URL using WebDriver-BiDi
        current_url = firefox_interface.bidi_get_current_url()
        assert current_url == "https://example.com/"
        
        # Get page title using WebDriver-BiDi
        title = firefox_interface.bidi_get_page_title()
        assert title == "Example Domain"
    
    def test_bidi_evaluate_script_live(self, firefox_interface):
        """Test WebDriver-BiDi script evaluation with live Firefox"""
        # Navigate to a test page
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Test simple script evaluation
        result = firefox_interface.bidi_evaluate_script("return document.title")
        assert result == "Example Domain"
        
        # Test complex object return
        result = firefox_interface.bidi_evaluate_script("""
            return {
                title: document.title,
                url: window.location.href,
                elementCount: document.querySelectorAll('*').length
            }
        """)
        assert isinstance(result, dict)
        assert result['title'] == "Example Domain"
        assert 'example.com' in result['url']
        assert result['elementCount'] > 0
        
        # Test array return
        result = firefox_interface.bidi_evaluate_script("""
            return Array.from(document.querySelectorAll('h1')).map(el => el.textContent)
        """)
        assert isinstance(result, list)
    
    def test_bidi_get_page_source_live(self, firefox_interface):
        """Test WebDriver-BiDi page source retrieval with live Firefox"""
        # Navigate to a test page
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Get page source using WebDriver-BiDi
        source = firefox_interface.bidi_get_page_source()
        
        # Verify we got HTML content
        assert isinstance(source, str)
        assert len(source) > 0
        assert '<html' in source.lower()
        assert 'example domain' in source.lower()
        
        # Compare with original method
        original_source = firefox_interface.get_page_source()
        assert source == original_source
    
    def test_bidi_capture_screenshot_live(self, firefox_interface):
        """Test WebDriver-BiDi screenshot capture with live Firefox"""
        # Navigate to a test page
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Capture screenshot using WebDriver-BiDi
        screenshot_data = firefox_interface.bidi_capture_screenshot()
        
        # Verify we got screenshot data
        assert isinstance(screenshot_data, bytes)
        assert len(screenshot_data) > 0
        
        # Verify it's valid PNG data (PNG header)
        assert screenshot_data[:8] == b'\x89PNG\r\n\x1a\n'
        
        # Compare with original method
        original_screenshot = firefox_interface.take_screenshot()
        assert screenshot_data == original_screenshot
    
    def test_bidi_cookie_management_live(self, firefox_interface):
        """Test WebDriver-BiDi cookie management with live Firefox"""
        # Navigate to a test page
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Get cookies using WebDriver-BiDi
        cookies = firefox_interface.bidi_get_cookies()
        assert isinstance(cookies, list)
        
        # Set a cookie using WebDriver-BiDi
        success = firefox_interface.bidi_set_cookie({
            "name": "test_cookie",
            "value": "test_value",
            "domain": ".example.com",
            "path": "/",
            "secure": False
        })
        assert success is True
        
        # Verify cookie was set by getting cookies again
        cookies_after = firefox_interface.bidi_get_cookies()
        cookie_names = [cookie.get('name', '') for cookie in cookies_after]
        assert 'test_cookie' in cookie_names
        
        # Delete the cookie using WebDriver-BiDi
        success = firefox_interface.bidi_delete_cookie("test_cookie")
        assert success is True
        
        # Verify cookie was deleted
        cookies_final = firefox_interface.bidi_get_cookies()
        final_names = [cookie.get('name', '') for cookie in cookies_final]
        assert 'test_cookie' not in final_names
    
    def test_bidi_context_management_live(self, firefox_interface):
        """Test WebDriver-BiDi context management with live Firefox"""
        # Get current browsing context tree
        contexts = firefox_interface.bidi_get_browsing_context_tree()
        assert isinstance(contexts, list)
        assert len(contexts) >= 1  # Should have at least the current context
        
        # Get current URL using WebDriver-BiDi
        current_url = firefox_interface.bidi_get_current_url()
        assert isinstance(current_url, str)
        
        # Navigate and verify URL changes
        firefox_interface.bidi_navigate("https://example.org", wait="complete")
        new_url = firefox_interface.bidi_get_current_url()
        assert new_url == "https://example.org/"
        assert new_url != current_url
    
    def test_bidi_script_function_call_live(self, firefox_interface):
        """Test WebDriver-BiDi function calling with live Firefox"""
        # Navigate to a test page
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Call a function that returns a simple value
        result = firefox_interface.bidi_call_function(
            "function(a, b) { return a + b; }",
            [5, 3]
        )
        assert result == 8
        
        # Call a function that interacts with the DOM
        result = firefox_interface.bidi_call_function(
            "function() { return document.title.length; }"
        )
        assert result == 14  # "Example Domain" has 14 characters
        
        # Call a function with array argument
        result = firefox_interface.bidi_call_function(
            "function(arr) { return arr.reduce((sum, val) => sum + val, 0); }",
            [[1, 2, 3, 4]]
        )
        assert result == 10
    
    def test_bidi_multiple_contexts_live(self, firefox_interface):
        """Test WebDriver-BiDi with multiple browsing contexts"""
        # Get initial context count
        initial_contexts = firefox_interface.bidi_get_browsing_context_tree()
        initial_count = len(initial_contexts)
        
        # Create a new tab using the original method
        new_tab = firefox_interface.new_tab("https://example.org")
        
        # Get updated context tree
        updated_contexts = firefox_interface.bidi_get_browsing_context_tree()
        updated_count = len(updated_contexts)
        
        # Verify we have one more context
        assert updated_count == initial_count + 1
        
        # Verify the new tab can use WebDriver-BiDi methods
        new_url = new_tab.bidi_get_current_url()
        assert "example.org" in new_url
        
        new_title = new_tab.bidi_get_page_title()
        assert new_title == "Example Domain"
    
    def test_bidi_error_handling_live(self, firefox_interface):
        """Test WebDriver-BiDi error handling with live Firefox"""
        # Test navigation to invalid URL (should handle gracefully)
        try:
            result = firefox_interface.bidi_navigate("https://invalid-url-that-does-not-exist.com", wait="complete")
            # If it doesn't raise an exception, that's fine - some browsers handle this differently
        except Exception:
            # Expected - invalid URL should cause an error
            pass
        
        # Test script evaluation with invalid script (should return None)
        result = firefox_interface.bidi_evaluate_script("invalid javascript syntax here!!!")
        assert result is None  # Should return None on error
        
        # Test getting current URL when navigation fails (should return empty string or previous URL)
        current_url = firefox_interface.bidi_get_current_url()
        assert isinstance(current_url, str)  # Should always return a string
    
    def test_bidi_performance_comparison(self, firefox_interface):
        """Compare WebDriver-BiDi methods with original methods for consistency"""
        # Navigate to test page
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Compare URL retrieval
        bidi_url = firefox_interface.bidi_get_current_url()
        original_url = firefox_interface.get_current_url()
        assert bidi_url == original_url
        
        # Compare title retrieval
        bidi_title = firefox_interface.bidi_get_page_title()
        original_title, _ = firefox_interface.get_page_url_title()
        assert bidi_title == original_title
        
        # Compare page source retrieval
        bidi_source = firefox_interface.bidi_get_page_source()
        original_source = firefox_interface.get_page_source()
        assert bidi_source == original_source
        
        # Compare screenshot capture
        bidi_screenshot = firefox_interface.bidi_capture_screenshot()
        original_screenshot = firefox_interface.take_screenshot()
        assert bidi_screenshot == original_screenshot
    
    def test_bidi_event_waiting_live(self, firefox_interface):
        """Test WebDriver-BiDi event waiting functionality"""
        # Subscribe to events
        success = firefox_interface.bidi_subscribe([
            "browsingContext.domContentLoaded"
        ])
        assert success is True
        
        # Navigate to trigger events
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Wait for an event (with short timeout since we just navigated)
        event = firefox_interface.bidi_wait_for_event(
            "browsingContext.domContentLoaded",
            timeout=2
        )
        # Event may or may not be available depending on timing, but method should not crash
        
        # Unsubscribe from events
        success = firefox_interface.bidi_unsubscribe([
            "browsingContext.domContentLoaded"
        ])
        assert success is True


class TestWebDriverBiDiAdvancedFeatures:
    """Test advanced WebDriver-BiDi features"""
    
    @pytest.fixture(scope="function")
    def firefox_interface(self):
        """Fixture that provides a Firefox interface for testing"""
        with FirefoxRemoteDebugInterface(
            headless=True,
            port=6180 + hash(time.time()) % 1000
        ) as interface:
            yield interface
    
    def test_bidi_complex_script_execution(self, firefox_interface):
        """Test complex script execution with WebDriver-BiDi"""
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Test script that creates and manipulates DOM elements
        result = firefox_interface.bidi_evaluate_script("""
            const div = document.createElement('div');
            div.id = 'test-element';
            div.textContent = 'Test Content';
            document.body.appendChild(div);
            return div.outerHTML;
        """)
        
        assert isinstance(result, str)
        assert 'test-element' in result
        assert 'Test Content' in result
        
        # Verify the element was actually created
        result = firefox_interface.bidi_evaluate_script("""
            const element = document.getElementById('test-element');
            return element ? element.textContent : null;
        """)
        assert result == "Test Content"
    
    def test_bidi_window_management(self, firefox_interface):
        """Test window/browsing context management"""
        # Get initial context info
        initial_contexts = firefox_interface.bidi_get_browsing_context_tree()
        initial_count = len(initial_contexts)
        
        # Create new browsing context using WebDriver-BiDi
        new_context_id = firefox_interface.bidi_create_browsing_context("tab")
        assert isinstance(new_context_id, str)
        assert len(new_context_id) > 0
        
        # Verify context count increased
        updated_contexts = firefox_interface.bidi_get_browsing_context_tree()
        assert len(updated_contexts) == initial_count + 1
        
        # Navigate the new context
        firefox_interface.bidi_navigate("https://example.org", context_id=new_context_id)
        
        # Get URL from the new context
        url = firefox_interface.bidi_get_current_url(context_id=new_context_id)
        assert "example.org" in url
    
    def test_bidi_network_interception_setup(self, firefox_interface):
        """Test network interception setup (note: actual interception requires event handling)"""
        # Add a network intercept
        intercept_id = firefox_interface.bidi_add_intercept(["beforeRequestSent"])
        assert isinstance(intercept_id, str)
        assert len(intercept_id) > 0
        
        # Verify intercept can be removed
        success = firefox_interface.bidi_remove_intercept(intercept_id)
        assert success is True
        
        # Test intercept with URL patterns (using proper WebDriver-BiDi format)
        intercept_id2 = firefox_interface.bidi_add_intercept(
            ["beforeRequestSent"],
            url_patterns=[{"type": "pattern", "hostname": "example.com"}]
        )
        assert isinstance(intercept_id2, str)
        assert len(intercept_id2) > 0
        
        # Clean up
        firefox_interface.bidi_remove_intercept(intercept_id2)
    
    def test_bidi_session_management(self, firefox_interface):
        """Test session management features"""
        # Get current session info (indirectly via successful operations)
        success = firefox_interface.bidi_subscribe(["browsingContext.domContentLoaded"])
        assert success is True
        
        # Test unsubscribe
        success = firefox_interface.bidi_unsubscribe(["browsingContext.domContentLoaded"])
        assert success is True
        
        # Test multiple event subscription
        success = firefox_interface.bidi_subscribe([
            "browsingContext.domContentLoaded",
            "browsingContext.load"
        ])
        assert success is True
        
        # Clean up
        firefox_interface.bidi_unsubscribe([
            "browsingContext.domContentLoaded",
            "browsingContext.load"
        ])


class TestWebDriverBiDiEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture(scope="function")
    def firefox_interface(self):
        """Fixture that provides a Firefox interface for testing"""
        with FirefoxRemoteDebugInterface(
            headless=True,
            port=6280 + hash(time.time()) % 1000
        ) as interface:
            yield interface
    
    def test_bidi_methods_with_invalid_context(self, firefox_interface):
        """Test WebDriver-BiDi methods with invalid context IDs"""
        # These should handle invalid contexts gracefully
        result = firefox_interface.bidi_get_current_url(context_id="invalid-context-id")
        assert isinstance(result, str)  # Should return empty string or handle gracefully
        
        result = firefox_interface.bidi_get_page_title(context_id="invalid-context-id")
        assert isinstance(result, str)  # Should return empty string or handle gracefully
    
    def test_bidi_empty_script_execution(self, firefox_interface):
        """Test WebDriver-BiDi with empty or minimal scripts"""
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Empty script
        result = firefox_interface.bidi_evaluate_script("")
        assert result is None  # Empty script should return None
        
        # Script that returns undefined
        result = firefox_interface.bidi_evaluate_script("return undefined")
        assert result is None  # undefined should be converted to None
        
        # Script that returns null
        result = firefox_interface.bidi_evaluate_script("return null")
        assert result is None  # null should be converted to None
    
    def test_bidi_screenshot_formats(self, firefox_interface):
        """Test WebDriver-BiDi screenshot with different formats"""
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Test PNG format (default) - Firefox only supports PNG format
        png_data = firefox_interface.bidi_capture_screenshot(format="png")
        assert isinstance(png_data, bytes)
        assert len(png_data) > 0
        assert png_data[:8] == b'\x89PNG\r\n\x1a\n'  # PNG header
        
        # Test that other formats fall back to PNG (Firefox limitation)
        # When an unsupported format is requested, Firefox should still return PNG
        jpeg_data = firefox_interface.bidi_capture_screenshot(format="jpeg")
        assert isinstance(jpeg_data, bytes)
        assert len(jpeg_data) > 0
        # Should still be PNG format due to Firefox limitation
        assert jpeg_data[:8] == b'\x89PNG\r\n\x1a\n'  # PNG header
    
    def test_bidi_context_fallback_behavior(self, firefox_interface):
        """Test context fallback behavior when no specific context is provided"""
        # Navigate to establish a context
        firefox_interface.bidi_navigate("https://example.com", wait="complete")
        
        # Get current context ID
        contexts = firefox_interface.bidi_get_browsing_context_tree()
        assert len(contexts) >= 1
        
        # Methods without context_id should use the current context
        url = firefox_interface.bidi_get_current_url()
        assert "example.com" in url
        
        title = firefox_interface.bidi_get_page_title()
        assert title == "Example Domain"


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--maxfail=3",  # Stop after 3 failures to save time
        "-x"  # Stop on first failure
    ])