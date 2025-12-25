#!/usr/bin/env python3

"""
Comprehensive tests for WebDriver-BiDi mixin functionality

This test suite verifies that the WebDriver-BiDi mixin is properly integrated
and that all methods are available and have correct signatures.
"""

import pytest
import inspect
from unittest.mock import Mock, MagicMock, patch
from FirefoxController.interface import FirefoxRemoteDebugInterface
from FirefoxController.webdriver_bidi_mixin import WebDriverBiDiMixin


class TestWebDriverBiDiMixinIntegration:
    """Test WebDriver-BiDi mixin integration with FirefoxRemoteDebugInterface"""
    
    def test_inheritance(self):
        """Test that FirefoxRemoteDebugInterface inherits from WebDriverBiDiMixin"""
        assert issubclass(FirefoxRemoteDebugInterface, WebDriverBiDiMixin)
    
    def test_mixin_instantiation(self):
        """Test that the mixin can be instantiated"""
        mixin = WebDriverBiDiMixin()
        assert mixin is not None
        assert hasattr(mixin, 'log')
    
    def test_interface_instantiation(self):
        """Test that FirefoxRemoteDebugInterface can be instantiated"""
        interface = FirefoxRemoteDebugInterface()
        assert interface is not None
        assert hasattr(interface, 'manager')


class TestWebDriverBiDiMethodAvailability:
    """Test that all WebDriver-BiDi methods are available"""
    
    def test_browsing_context_methods(self):
        """Test browsing context method availability"""
        interface = FirefoxRemoteDebugInterface()
        
        browsing_context_methods = [
            'bidi_create_browsing_context',
            'bidi_navigate',
            'bidi_get_browsing_context_tree',
            'bidi_close_browsing_context',
            'bidi_capture_screenshot',
            'bidi_print',
            'bidi_get_current_url',
            'bidi_get_page_title',
            'bidi_get_page_source'
        ]
        
        for method in browsing_context_methods:
            assert hasattr(interface, method), "Method {} should be available".format(method)
            assert callable(getattr(interface, method)), "Method {} should be callable".format(method)
    
    def test_script_methods(self):
        """Test script method availability"""
        interface = FirefoxRemoteDebugInterface()
        
        script_methods = [
            'bidi_evaluate_script',
            'bidi_call_function',
            'bidi_disown',
            '_parse_script_result'
        ]
        
        for method in script_methods:
            assert hasattr(interface, method), "Method {} should be available".format(method)
            assert callable(getattr(interface, method)), "Method {} should be callable".format(method)
    
    def test_network_methods(self):
        """Test network method availability"""
        interface = FirefoxRemoteDebugInterface()
        
        network_methods = [
            'bidi_add_intercept',
            'bidi_remove_intercept',
            'bidi_continue_request',
            'bidi_continue_response',
            'bidi_fail_request',
            'bidi_provide_response',
            'bidi_wait_for_event'
        ]
        
        for method in network_methods:
            assert hasattr(interface, method), "Method {} should be available".format(method)
            assert callable(getattr(interface, method)), "Method {} should be callable".format(method)
    
    def test_storage_methods(self):
        """Test storage method availability"""
        interface = FirefoxRemoteDebugInterface()
        
        storage_methods = [
            'bidi_get_cookies',
            'bidi_set_cookie',
            'bidi_delete_cookie',
            'bidi_delete_all_cookies'
        ]
        
        for method in storage_methods:
            assert hasattr(interface, method), "Method {} should be available".format(method)
            assert callable(getattr(interface, method)), "Method {} should be callable".format(method)
    
    def test_session_methods(self):
        """Test session method availability"""
        interface = FirefoxRemoteDebugInterface()
        
        session_methods = [
            'bidi_new_session',
            'bidi_end_session',
            'bidi_subscribe',
            'bidi_unsubscribe'
        ]
        
        for method in session_methods:
            assert hasattr(interface, method), "Method {} should be available".format(method)
            assert callable(getattr(interface, method)), "Method {} should be callable".format(method)
    
    def test_browser_methods(self):
        """Test browser method availability"""
        interface = FirefoxRemoteDebugInterface()
        
        browser_methods = [
            'bidi_create_user_context',
            'bidi_remove_user_context'
        ]
        
        for method in browser_methods:
            assert hasattr(interface, method), "Method {} should be available".format(method)
            assert callable(getattr(interface, method)), "Method {} should be callable".format(method)
    
    def test_input_methods(self):
        """Test input method availability"""
        interface = FirefoxRemoteDebugInterface()
        
        input_methods = [
            'bidi_perform_actions',
            'bidi_release_actions'
        ]
        
        for method in input_methods:
            assert hasattr(interface, method), "Method {} should be available".format(method)
            assert callable(getattr(interface, method)), "Method {} should be callable".format(method)


class TestWebDriverBiDiMethodSignatures:
    """Test that WebDriver-BiDi methods have correct signatures"""
    
    def test_bidi_navigate_signature(self):
        """Test bidi_navigate method signature"""
        interface = FirefoxRemoteDebugInterface()
        sig = inspect.signature(interface.bidi_navigate)
        params = list(sig.parameters.keys())
        
        assert 'url' in params
        assert 'context_id' in params
        assert 'wait' in params
        assert len(params) == 3  # self, url, context_id, wait
    
    def test_bidi_evaluate_script_signature(self):
        """Test bidi_evaluate_script method signature"""
        interface = FirefoxRemoteDebugInterface()
        sig = inspect.signature(interface.bidi_evaluate_script)
        params = list(sig.parameters.keys())
        
        assert 'script' in params
        assert 'context_id' in params
        assert 'await_promise' in params
        assert 'sandbox' in params
    
    def test_bidi_capture_screenshot_signature(self):
        """Test bidi_capture_screenshot method signature"""
        interface = FirefoxRemoteDebugInterface()
        sig = inspect.signature(interface.bidi_capture_screenshot)
        params = list(sig.parameters.keys())
        
        assert 'context_id' in params
        assert 'format' in params
        assert 'clip' in params
    
    def test_bidi_add_intercept_signature(self):
        """Test bidi_add_intercept method signature"""
        interface = FirefoxRemoteDebugInterface()
        sig = inspect.signature(interface.bidi_add_intercept)
        params = list(sig.parameters.keys())
        
        assert 'phases' in params
        assert 'url_patterns' in params
        assert 'context_id' in params


class TestWebDriverBiDiMethodBehavior:
    """Test WebDriver-BiDi method behavior with mocked manager"""
    
    def setup_method(self):
        """Setup test with mocked manager"""
        self.interface = FirefoxRemoteDebugInterface()
        self.interface.manager = Mock()
        self.interface.active_browsing_context = "test_context"
        self.interface.manager.browsing_context = "test_context"
    
    def test_bidi_navigate_without_context(self):
        """Test bidi_navigate behavior when no context is available"""
        self.interface.active_browsing_context = None
        self.interface.manager.browsing_context = None
        
        with pytest.raises(Exception, match="No browsing context available"):
            self.interface.bidi_navigate("https://example.com")
    
    def test_bidi_navigate_with_context(self):
        """Test bidi_navigate behavior with valid context"""
        # Mock the _send_message method
        mock_response = {
            'type': 'success',
            'result': {'url': 'https://example.com', 'navigation': 'nav123'}
        }
        self.interface.manager._send_message = Mock(return_value=mock_response)
        
        result = self.interface.bidi_navigate("https://example.com")
        
        # Verify the method was called with correct parameters
        self.interface.manager._send_message.assert_called_once()
        call_args = self.interface.manager._send_message.call_args[0][0]
        assert call_args['method'] == 'browsingContext.navigate'
        assert call_args['params']['url'] == 'https://example.com'
        assert call_args['params']['context'] == 'test_context'
        
        # Verify result
        assert result == mock_response['result']
    
    def test_bidi_evaluate_script_success(self):
        """Test bidi_evaluate_script with successful response"""
        mock_response = {
            'type': 'success',
            'result': {
                'type': 'string',
                'value': 'Hello World'
            }
        }
        self.interface.manager._send_message = Mock(return_value=mock_response)
        
        result = self.interface.bidi_evaluate_script("return 'Hello World'")
        
        # Verify the method was called
        self.interface.manager._send_message.assert_called_once()
        call_args = self.interface.manager._send_message.call_args[0][0]
        assert call_args['method'] == 'script.evaluate'
        
        # Verify result parsing
        assert result == 'Hello World'
    
    def test_bidi_evaluate_script_complex_object(self):
        """Test bidi_evaluate_script with complex object response"""
        # Test the format that the _parse_script_result method expects for complex objects
        mock_response = {
            'type': 'success',
            'result': {
                'type': 'object',
                'value': [
                    ['key1', {'value': 'value1'}],
                    ['key2', {'value': 'value2'}]
                ]
            }
        }
        self.interface.manager._send_message = Mock(return_value=mock_response)
        
        # Call _parse_script_result directly to test the parsing logic
        result = self.interface._parse_script_result(mock_response)
        
        # Verify result parsing for complex objects
        assert isinstance(result, dict)
        assert result['key1'] == 'value1'
        assert result['key2'] == 'value2'
    
    def test_bidi_get_cookies_success(self):
        """Test bidi_get_cookies with successful response"""
        mock_response = {
            'type': 'success',
            'result': {
                'cookies': [
                    {'name': 'cookie1', 'value': 'value1'},
                    {'name': 'cookie2', 'value': 'value2'}
                ]
            }
        }
        self.interface.manager._send_message = Mock(return_value=mock_response)
        
        result = self.interface.bidi_get_cookies()
        
        # Verify the method was called
        self.interface.manager._send_message.assert_called_once()
        call_args = self.interface.manager._send_message.call_args[0][0]
        assert call_args['method'] == 'storage.getCookies'
        
        # Verify result
        assert len(result) == 2
        assert result[0]['name'] == 'cookie1'
        assert result[1]['name'] == 'cookie2'
    
    def test_bidi_capture_screenshot_success(self):
        """Test bidi_capture_screenshot with successful response"""
        import base64
        screenshot_data = b"fake_screenshot_data"
        base64_data = base64.b64encode(screenshot_data).decode('utf-8')
        
        mock_response = {
            'type': 'success',
            'result': {
                'data': base64_data
            }
        }
        self.interface.manager._send_message = Mock(return_value=mock_response)
        
        result = self.interface.bidi_capture_screenshot()
        
        # Verify the method was called
        self.interface.manager._send_message.assert_called_once()
        call_args = self.interface.manager._send_message.call_args[0][0]
        assert call_args['method'] == 'browsingContext.captureScreenshot'
        
        # Verify result
        assert result == screenshot_data
    
    def test_bidi_add_intercept_success(self):
        """Test bidi_add_intercept with successful response"""
        mock_response = {
            'type': 'success',
            'result': {
                'intercept': 'intercept123'
            }
        }
        self.interface.manager._send_message = Mock(return_value=mock_response)
        
        result = self.interface.bidi_add_intercept(['beforeRequestSent'])
        
        # Verify the method was called
        self.interface.manager._send_message.assert_called_once()
        call_args = self.interface.manager._send_message.call_args[0][0]
        assert call_args['method'] == 'network.addIntercept'
        
        # Verify result
        assert result == 'intercept123'
    
    def test_context_fallback_behavior(self):
        """Test that methods properly fall back to manager context"""
        # Set up interface without active_browsing_context
        self.interface.active_browsing_context = None
        self.interface.manager.browsing_context = "manager_context"
        
        mock_response = {
            'type': 'success',
            'result': {'url': 'https://example.com'}
        }
        self.interface.manager._send_message = Mock(return_value=mock_response)
        
        result = self.interface.bidi_navigate("https://example.com")
        
        # Verify it used the manager's context
        call_args = self.interface.manager._send_message.call_args[0][0]
        assert call_args['params']['context'] == 'manager_context'


class TestWebDriverBiDiErrorHandling:
    """Test WebDriver-BiDi error handling"""
    
    def setup_method(self):
        """Setup test with mocked manager"""
        self.interface = FirefoxRemoteDebugInterface()
        self.interface.manager = Mock()
        self.interface.active_browsing_context = "test_context"
        self.interface.manager.browsing_context = "test_context"
    
    def test_bidi_navigate_error_handling(self):
        """Test bidi_navigate error handling"""
        self.interface.manager._send_message = Mock(side_effect=Exception("Connection failed"))
        
        with pytest.raises(Exception, match="Connection failed"):
            self.interface.bidi_navigate("https://example.com")
    
    def test_bidi_evaluate_script_error_handling(self):
        """Test bidi_evaluate_script error handling"""
        self.interface.manager._send_message = Mock(side_effect=Exception("Script execution failed"))
        
        result = self.interface.bidi_evaluate_script("return 'test'")
        assert result is None  # Should return None on error
    
    def test_bidi_get_cookies_error_handling(self):
        """Test bidi_get_cookies error handling"""
        self.interface.manager._send_message = Mock(side_effect=Exception("Cookie retrieval failed"))
        
        result = self.interface.bidi_get_cookies()
        assert result == []  # Should return empty list on error
    
    def test_bidi_capture_screenshot_error_handling(self):
        """Test bidi_capture_screenshot error handling"""
        self.interface.manager._send_message = Mock(side_effect=Exception("Screenshot failed"))
        
        result = self.interface.bidi_capture_screenshot()
        assert result == b''  # Should return empty bytes on error


class TestWebDriverBiDiBackwardCompatibility:
    """Test that WebDriver-BiDi integration doesn't break existing functionality"""
    
    def test_original_methods_still_available(self):
        """Test that original FirefoxController methods are still available"""
        interface = FirefoxRemoteDebugInterface()
        
        original_methods = [
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
        
        for method in original_methods:
            assert hasattr(interface, method), "Original method {} should still be available".format(method)
            assert callable(getattr(interface, method)), "Original method {} should be callable".format(method)
    
    def test_interface_initialization_unchanged(self):
        """Test that interface initialization parameters are unchanged"""
        sig = inspect.signature(FirefoxRemoteDebugInterface.__init__)
        params = list(sig.parameters.keys())
        
        # These are the original parameters
        expected_params = ['self', 'binary', 'host', 'port', 'headless', 'additional_options', 'profile_dir', 'manager']
        
        for param in expected_params:
            assert param in params, "Expected parameter {} should be present".format(param)
    
    def test_context_manager_interface_unchanged(self):
        """Test that context manager interface is unchanged"""
        interface = FirefoxRemoteDebugInterface()
        
        assert hasattr(interface, '__enter__'), "Interface should have __enter__ method"
        assert hasattr(interface, '__exit__'), "Interface should have __exit__ method"
        assert callable(interface.__enter__), "__enter__ should be callable"
        assert callable(interface.__exit__), "__exit__ should be callable"


class TestWebDriverBiDiMethodCount:
    """Test that we have the expected number of WebDriver-BiDi methods"""
    
    def test_total_webdriver_bidi_methods(self):
        """Test total count of WebDriver-BiDi methods"""
        interface = FirefoxRemoteDebugInterface()
        
        # All WebDriver-BiDi methods (including the private _parse_script_result)
        bidi_methods = [
            'bidi_create_browsing_context', 'bidi_navigate', 'bidi_get_browsing_context_tree',
            'bidi_close_browsing_context', 'bidi_capture_screenshot', 'bidi_print',
            'bidi_evaluate_script', 'bidi_call_function', 'bidi_disown', '_parse_script_result',
            'bidi_add_intercept', 'bidi_remove_intercept', 'bidi_continue_request',
            'bidi_continue_response', 'bidi_fail_request', 'bidi_provide_response',
            'bidi_get_cookies', 'bidi_set_cookie', 'bidi_delete_cookie',
            'bidi_delete_all_cookies', 'bidi_new_session', 'bidi_end_session',
            'bidi_subscribe', 'bidi_unsubscribe', 'bidi_create_user_context',
            'bidi_remove_user_context', 'bidi_perform_actions', 'bidi_release_actions',
            'bidi_wait_for_event', 'bidi_get_current_url', 'bidi_get_page_title',
            'bidi_get_page_source'
        ]
        
        # Count how many are actually present
        present_methods = []
        for method in bidi_methods:
            if hasattr(interface, method):
                present_methods.append(method)
        
        assert len(present_methods) == len(bidi_methods), "Expected {} methods, found {}".format(len(bidi_methods), len(present_methods))
        
        # Verify all expected methods are present
        for method in bidi_methods:
            assert hasattr(interface, method), "WebDriver-BiDi method {} should be present".format(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])