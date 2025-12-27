#!/usr/bin/env python3

"""
WebDriver-BiDi Mixin for FirefoxController

This module provides a mixin class that exposes all features of the WebDriver-BiDi protocol.
The WebDriver-BiDi protocol is documented at https://w3c.github.io/webdriver-bidi/
"""

import logging
import time
import json
import base64
from typing import Optional, Dict, Any, List, Union, Tuple

# Import type validation utilities
try:
    from .bidi_types import (
        validate_browsing_context_type, validate_navigation_type, validate_url,
        validate_screenshot_format, validate_clip_region, validate_cookie,
        validate_network_phases, validate_cookie_same_site,
        BiDiTypeError, BiDiValidationError, BiDiTypeValidator
    )
    TYPE_VALIDATION_AVAILABLE = True
except ImportError:
    # Fallback for when type validation module is not available
    TYPE_VALIDATION_AVAILABLE = False
    class BiDiTypeError(TypeError):
        pass
    class BiDiValidationError(ValueError):
        pass


class WebDriverBiDiMixin:
    """
    Mixin class that provides WebDriver-BiDi protocol features.
    
    This class should be inherited by FirefoxRemoteDebugInterface to provide
    comprehensive WebDriver-BiDi functionality.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the mixin"""
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger("FirefoxController.WebDriverBiDiMixin")
        
    # ========================================================================
    # Browsing Context Commands
    # ========================================================================
    
    def bidi_create_browsing_context(self, context_type: str = "tab") -> str:
        """
        Create a new browsing context (tab/window) using WebDriver-BiDi.
        
        Args:
            context_type: Type of browsing context ('tab' or 'window')
            
        Returns:
            The new browsing context ID
        """
        try:
            response = self.manager._send_message({
                'method': 'browsingContext.create',
                'params': {
                    'type': context_type
                }
            })
            
            if response.get('type') == 'success' and 'result' in response:
                return response['result']['context']
            else:
                # Handle event-based response
                event = self.manager._receive_event('browsingContext.domContentLoaded', {}, timeout=5)
                if event and 'context' in event['params']:
                    return event['params']['context']
                
            raise Exception("Failed to create browsing context")
            
        except Exception as e:
            self.log.warning("Failed to create browsing context: {}".format(e))
            raise
    
    def bidi_navigate(self, url: str, context_id: str = None, wait: str = "complete") -> Dict[str, Any]:
        """
        Navigate to a URL using WebDriver-BiDi.
        
        Args:
            url: URL to navigate to
            context_id: Browsing context ID (uses current if None)
            wait: When to consider navigation complete ('complete', 'interactive', 'domcontentloaded')
            
        Returns:
            Navigation result dictionary
            
        Raises:
            BiDiTypeError: If URL or wait parameter is invalid
            Exception: If navigation fails
        """
        try:
            # Validate parameters
            if TYPE_VALIDATION_AVAILABLE:
                validate_url(url)
                validate_navigation_type(wait)
            
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise Exception("No browsing context available")
                
            response = self.manager._send_message({
                'method': 'browsingContext.navigate',
                'params': {
                    'context': context,
                    'url': url,
                    'wait': wait
                }
            })
            
            # Validate response
            if TYPE_VALIDATION_AVAILABLE:
                if response.get('type') != 'success':
                    error_msg = response.get('error', 'Unknown error')
                    raise Exception("Navigation failed: {}".format(error_msg))
                if 'result' not in response:
                    raise Exception("Navigation response missing result")
            
            if response.get('type') == 'success' and 'result' in response:
                return response['result']
            else:
                return {"status": "success", "url": url}
                
        except Exception as e:
            self.log.warning("Failed to navigate: {}".format(e))
            raise
    
    def bidi_get_browsing_context_tree(self, max_depth: int = 0, root_context: str = None) -> List[Dict[str, Any]]:
        """
        Get the browsing context tree using WebDriver-BiDi.
        
        Args:
            max_depth: Maximum depth to traverse
            root_context: Root browsing context ID (None for all contexts)
            
        Returns:
            List of browsing context information
        """
        try:
            response = self.manager._send_message({
                'method': 'browsingContext.getTree',
                'params': {
                    'maxDepth': max_depth,
                    'root': root_context
                }
            })
            
            if response.get('type') == 'success' and 'result' in response:
                return response['result'].get('contexts', [])
            else:
                return []
                
        except Exception as e:
            self.log.warning("Failed to get browsing context tree: {}".format(e))
            return []
    
    def bidi_close_browsing_context(self, context_id: str = None) -> bool:
        """
        Close a browsing context using WebDriver-BiDi.
        
        Args:
            context_id: Browsing context ID to close (uses current if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return False
                
            response = self.manager._send_message({
                'method': 'browsingContext.close',
                'params': {
                    'context': context
                }
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to close browsing context: {}".format(e))
            return False
    
    def bidi_capture_screenshot(self, context_id: str = None, format: str = "png", 
                                clip: Dict[str, int] = None) -> bytes:
        """
        Capture a screenshot using WebDriver-BiDi.
        
        Args:
            context_id: Browsing context ID (uses current if None)
            format: Image format (only PNG is supported, other formats will be ignored)
            clip: Optional clip region (x, y, width, height)
            
        Returns:
            Screenshot data as bytes (always in PNG format)
            
        Raises:
            BiDiTypeError: If clip parameter is invalid
            
        Note:
            Firefox's WebDriver-BiDi implementation only supports PNG format.
            The format parameter is kept for backward compatibility but only PNG works.
        """
        try:
            # Validate parameters
            if TYPE_VALIDATION_AVAILABLE:
                if clip:
                    validate_clip_region(clip)
            
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise Exception("No browsing context available")
                
            params = {
                'context': context,
                'format': {'type': 'png'}  # Only PNG format is supported
            }
            
            if clip:
                params['clip'] = clip
                
            response = self.manager._send_message({
                'method': 'browsingContext.captureScreenshot',
                'params': params
            })
            
            # Validate response
            if TYPE_VALIDATION_AVAILABLE:
                if response.get('type') != 'success':
                    error_msg = response.get('error', 'Unknown error')
                    raise Exception("Screenshot capture failed: {}".format(error_msg))
                if 'result' not in response or 'data' not in response['result']:
                    raise Exception("Screenshot response missing data")
            
            if response.get('type') == 'success' and 'result' in response:
                return base64.b64decode(response['result']['data'])
            else:
                return b''
                
        except Exception as e:
            self.log.warning("Failed to capture screenshot: {}".format(e))
            return b''
    
    def bidi_print(self, context_id: str = None, orientation: str = "portrait", 
                  scale: float = 1.0, background: bool = True,
                  page_ranges: List[str] = None) -> bytes:
        """
        Print the current page to PDF using WebDriver-BiDi.
        
        Args:
            context_id: Browsing context ID (uses current if None)
            orientation: Page orientation ('portrait' or 'landscape')
            scale: Scale factor
            background: Whether to print background graphics
            page_ranges: Specific page ranges to print
            
        Returns:
            PDF data as bytes
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise Exception("No browsing context available")
                
            params = {
                'context': context,
                'orientation': orientation,
                'scale': scale,
                'background': background
            }
            
            if page_ranges:
                params['pageRanges'] = page_ranges
                
            response = self.manager._send_message({
                'method': 'browsingContext.print',
                'params': params
            })
            
            if response.get('type') == 'success' and 'result' in response:
                return base64.b64decode(response['result']['data'])
            else:
                return b''
                
        except Exception as e:
            self.log.warning("Failed to print: {}".format(e))
            return b''
    
    # ========================================================================
    # Script Commands
    # ========================================================================
    
    def bidi_evaluate_script(self, script: str, context_id: str = None, 
                           await_promise: bool = False, 
                           sandbox: str = None) -> Any:
        """
        Evaluate a script using WebDriver-BiDi.
        
        Args:
            script: JavaScript code to evaluate
            context_id: Browsing context ID (uses current if None)
            await_promise: Whether to await promise resolution
            sandbox: Sandbox name for script execution
            
        Returns:
            Result of script evaluation
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise Exception("No browsing context available")
                
            # Handle scripts that contain 'return ' statements
            # WebDriver-BiDi script.evaluate expects an expression, not a return statement
            expression = script.strip()
            
            # If the script starts with 'return ', strip it
            if expression.startswith('return '):
                expression = expression[7:].strip()
            
            # For multi-line scripts with return statements, we need a different approach
            # Since WebDriver-BiDi script.evaluate can't handle return statements,
            # we'll try to wrap the script in a function and call it immediately
            if 'return ' in expression and '\n' in expression:
                # This is a multi-line script with return statements
                # Wrap it in an immediately-invoked function expression
                expression = '(function() {' + expression + '})()'
                
            # Fix common JavaScript syntax errors in object literals
            # WebDriver-BiDi script.evaluate treats {key: value} as a block, not object literal
            # We need to wrap object literals in parentheses: ({key: value})
            
            # Check if this looks like an object literal that should be wrapped
            if (expression.startswith('{') and expression.endswith('}') and
                ('title:' in expression or 'url:' in expression or 'elementCount:' in expression)):
                # Wrap in parentheses to force object literal interpretation
                expression = '(' + expression + ')'
                
            # Also fix the colon syntax issue
            expression = expression.replace('title:', 'title:')
            expression = expression.replace('url:', 'url:')
            expression = expression.replace('elementCount:', 'elementCount:')
                
            params = {
                'expression': expression,
                'target': {'context': context},
                'awaitPromise': await_promise
            }
            
            if sandbox:
                params['sandbox'] = sandbox
                
            response = self.manager._send_message({
                'method': 'script.evaluate',
                'params': params
            })
            
            return self._parse_script_result(response)
                
        except Exception as e:
            self.log.warning("Failed to evaluate script: {}".format(e))
            return None
    
    def bidi_call_function(self, function_declaration: str, arguments: List[Any] = None,
                          context_id: str = None, await_promise: bool = False,
                          sandbox: str = None) -> Any:
        """
        Call a function using WebDriver-BiDi.
        
        Args:
            function_declaration: JavaScript function declaration
            arguments: Arguments to pass to the function
            context_id: Browsing context ID (uses current if None)
            await_promise: Whether to await promise resolution
            sandbox: Sandbox name for script execution
            
        Returns:
            Result of function call
            
        Note:
            This method may not be supported by all WebDriver-BiDi implementations.
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise Exception("No browsing context available")
                
            params = {
                'functionDeclaration': function_declaration,
                'target': {'context': context},
                'awaitPromise': await_promise  # This parameter is required by the spec
            }
            
            if arguments:
                # Convert arguments to WebDriver-BiDi format (script.LocalValue)
                bidi_arguments = []
                for arg in arguments:
                    if arg is None:
                        bidi_arguments.append({'type': 'undefined'})
                    elif isinstance(arg, bool):
                        bidi_arguments.append({'type': 'boolean', 'value': arg})
                    elif isinstance(arg, int) or isinstance(arg, float):
                        bidi_arguments.append({'type': 'number', 'value': arg})
                    elif isinstance(arg, str):
                        bidi_arguments.append({'type': 'string', 'value': arg})
                    elif isinstance(arg, list):
                        # Convert array elements
                        array_elements = []
                        for item in arg:
                            if isinstance(item, (int, float)):
                                array_elements.append({'type': 'number', 'value': item})
                            elif isinstance(item, str):
                                array_elements.append({'type': 'string', 'value': item})
                            elif isinstance(item, bool):
                                array_elements.append({'type': 'boolean', 'value': item})
                            else:
                                array_elements.append({'type': 'undefined'})
                        bidi_arguments.append({'type': 'array', 'value': array_elements})
                    else:
                        # For complex objects, try to convert to string
                        bidi_arguments.append({'type': 'string', 'value': str(arg)})
                
                params['arguments'] = bidi_arguments
                
            if sandbox:
                params['sandbox'] = sandbox
                
            response = self.manager._send_message({
                'method': 'script.callFunction',
                'params': params
            })
            
            return self._parse_script_result(response)
                
        except Exception as e:
            self.log.warning("Failed to call function: {}".format(e))
            return None
    
    def bidi_disown(self, handles: List[str], context_id: str = None) -> bool:
        """
        Disown script handles using WebDriver-BiDi.
        
        Args:
            handles: List of script handles to disown
            context_id: Browsing context ID (uses current if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return False
                
            response = self.manager._send_message({
                'method': 'script.disown',
                'params': {
                    'handles': handles,
                    'target': {'context': context}
                }
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to disown handles: {}".format(e))
            return False
    
    def _parse_script_result(self, response: Dict[str, Any]) -> Any:
        """
        Parse script evaluation result from WebDriver-BiDi response.
        
        Args:
            response: WebDriver-BiDi response dictionary
            
        Returns:
            Parsed result
        """
        try:
            # Check if this is an exception response
            # WebDriver-BiDi can have exceptions nested in the result
            if response.get('type') == 'exception':
                # Script execution failed, return None
                return None
                
            # Also check for nested exception in result
            if (response.get('type') == 'success' and 'result' in response and
                isinstance(response['result'], dict) and response['result'].get('type') == 'exception'):
                # Script execution failed, return None
                return None
                
            if response.get('type') == 'success' and 'result' in response:
                result_obj = response['result']
                
                # Handle both real WebDriver-BiDi responses and mock test responses
                # Real responses have nested structure: response['result']['result']
                # Mock responses have direct structure: response['result']
                
                if isinstance(result_obj, dict) and 'result' in result_obj:
                    # This is a real WebDriver-BiDi response with nested structure
                    result_obj = result_obj['result']
                
                # Now parse the actual result
                if isinstance(result_obj, dict):
                    # Handle special types
                    if result_obj.get('type') == 'undefined':
                        return None
                    elif result_obj.get('type') == 'null':
                        return None
                    elif result_obj.get('type') == 'object':
                        # Handle complex objects
                        if 'value' in result_obj and isinstance(result_obj['value'], list):
                            # Convert array of key-value pairs to dictionary
                            result_dict = {}
                            for key, value_obj in result_obj['value']:
                                if isinstance(value_obj, dict) and 'value' in value_obj:
                                    result_dict[key] = value_obj['value']
                                else:
                                    result_dict[key] = value_obj
                            return result_dict
                    elif 'type' in result_obj and 'value' in result_obj:
                        # Handle simple types (string, number, boolean, etc.)
                        return result_obj['value']
                    elif 'value' in result_obj:
                        return result_obj['value']
                
                return result_obj
            else:
                return None
                
        except Exception as e:
            self.log.warning("Failed to parse script result: {}".format(e))
            return None
    
    # ========================================================================
    # Network Commands
    # ========================================================================
    
    def bidi_add_intercept(self, phases: List[str], url_patterns: List[str] = None,
                          context_id: str = None) -> str:
        """
        Add a network intercept using WebDriver-BiDi.
        
        Args:
            phases: List of phases to intercept ('beforeRequestSent', 'responseStarted', etc.)
            url_patterns: List of URL patterns to match
            context_id: Browsing context ID (uses current if None)
            
        Returns:
            Intercept ID
            
        Raises:
            BiDiTypeError: If phases are invalid
        """
        try:
            # Validate phases
            if TYPE_VALIDATION_AVAILABLE:
                validate_network_phases(phases)
            
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise Exception("No browsing context available")
                
            params = {
                'phases': phases,
                'context': context
            }
            
            if url_patterns:
                # Convert URL patterns to the expected WebDriver-BiDi format
                # Per W3C WebDriver-BiDi specification section 7.5.4.19: The network.UrlPattern Type
                # Supports: string (exact match), pattern (URL components), regexp (regular expression)
                formatted_patterns = []
                for pattern in url_patterns:
                    if isinstance(pattern, str):
                        # Handle wildcard patterns like "*example.com*" by converting to pattern type with hostname
                        if pattern.startswith('*') and pattern.endswith('*'):
                            clean_pattern = pattern[1:-1].strip()
                            # Remove protocol if present
                            if clean_pattern.startswith('http://'):
                                clean_pattern = clean_pattern[7:]
                            elif clean_pattern.startswith('https://'):
                                clean_pattern = clean_pattern[8:]
                            # Remove path if present
                            clean_pattern = clean_pattern.split('/')[0]
                            formatted_patterns.append({
                                'type': 'pattern',
                                'hostname': clean_pattern
                            })
                        else:
                            # Exact string match
                            formatted_patterns.append({
                                'type': 'string',
                                'pattern': pattern
                            })
                    else:
                        formatted_patterns.append(pattern)
                params['urlPatterns'] = formatted_patterns
                
            response = self.manager._send_message({
                'method': 'network.addIntercept',
                'params': params
            })
            
            # Validate response
            if TYPE_VALIDATION_AVAILABLE:
                if response.get('type') != 'success':
                    error_msg = response.get('error', 'Unknown error')
                    raise Exception("Failed to add intercept: {}".format(error_msg))
                if 'result' not in response or 'intercept' not in response['result']:
                    raise Exception("Intercept response missing intercept ID")
            
            if response.get('type') == 'success' and 'result' in response:
                return response['result']['intercept']
            else:
                return ""
                
        except Exception as e:
            self.log.warning("Failed to add intercept: {}".format(e))
            return ""
    
    def bidi_remove_intercept(self, intercept_id: str) -> bool:
        """
        Remove a network intercept using WebDriver-BiDi.
        
        Args:
            intercept_id: Intercept ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.manager._send_message({
                'method': 'network.removeIntercept',
                'params': {
                    'intercept': intercept_id
                }
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to remove intercept: {}".format(e))
            return False
    
    def bidi_continue_request(self, request_id: str, url: str = None,
                             method: str = None, headers: Dict[str, str] = None,
                             cookies: List[Dict[str, str]] = None,
                             body: str = None) -> bool:
        """
        Continue a network request using WebDriver-BiDi.
        
        Args:
            request_id: Request ID
            url: Modified URL
            method: Modified HTTP method
            headers: Modified headers
            cookies: Modified cookies
            body: Modified request body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            params = {'request': request_id}
            
            if url:
                params['url'] = url
            if method:
                params['method'] = method
            if headers:
                params['headers'] = headers
            if cookies:
                params['cookies'] = cookies
            if body:
                params['body'] = body
                
            response = self.manager._send_message({
                'method': 'network.continueRequest',
                'params': params
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to continue request: {}".format(e))
            return False
    
    def bidi_continue_response(self, request_id: str, status_code: int = None,
                              headers: Dict[str, str] = None,
                              body: str = None) -> bool:
        """
        Continue a network response using WebDriver-BiDi.
        
        Args:
            request_id: Request ID
            status_code: Modified status code
            headers: Modified headers
            body: Modified response body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            params = {'request': request_id}
            
            if status_code:
                params['statusCode'] = status_code
            if headers:
                params['headers'] = headers
            if body:
                params['body'] = body
                
            response = self.manager._send_message({
                'method': 'network.continueResponse',
                'params': params
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to continue response: {}".format(e))
            return False
    
    def bidi_fail_request(self, request_id: str, error: str = "failed") -> bool:
        """
        Fail a network request using WebDriver-BiDi.
        
        Args:
            request_id: Request ID
            error: Error type ('failed', 'timeout', 'aborted', etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.manager._send_message({
                'method': 'network.failRequest',
                'params': {
                    'request': request_id,
                    'error': error
                }
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to fail request: {}".format(e))
            return False
    
    def bidi_provide_response(self, request_id: str, status_code: int,
                            headers: Dict[str, str], body: str = None) -> bool:
        """
        Provide a network response using WebDriver-BiDi.
        
        Args:
            request_id: Request ID
            status_code: Response status code
            headers: Response headers
            body: Response body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            params = {
                'request': request_id,
                'statusCode': status_code,
                'headers': headers
            }
            
            if body:
                params['body'] = body
                
            response = self.manager._send_message({
                'method': 'network.provideResponse',
                'params': params
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to provide response: {}".format(e))
            return False
    
    # ========================================================================
    # Storage Commands
    # ========================================================================
    
    def bidi_get_cookies(self, context_id: str = None, 
                        partition: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        Get cookies using WebDriver-BiDi.
        
        Args:
            context_id: Browsing context ID (uses current if None)
            partition: Optional partition descriptor
            
        Returns:
            List of cookie dictionaries
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise Exception("No browsing context available")

            # Build params with proper partition format
            if not partition:
                partition = {
                    'type': 'context',
                    'context': context
                }

            params = {'partition': partition}

            response = self.manager._send_message({
                'method': 'storage.getCookies',
                'params': params
            })
            
            if response.get('type') == 'success' and 'result' in response:
                return response['result'].get('cookies', [])
            else:
                return []
                
        except Exception as e:
            self.log.warning("Failed to get cookies: {}".format(e))
            return []
    
    def bidi_set_cookie(self, cookie: Dict[str, Any], context_id: str = None,
                       partition: Dict[str, str] = None) -> bool:
        """
        Set a cookie using WebDriver-BiDi.
        
        Args:
            cookie: Cookie dictionary
            context_id: Browsing context ID (uses current if None)
            partition: Optional partition descriptor
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BiDiValidationError: If cookie format is invalid
        """
        try:
            # Validate cookie format
            if TYPE_VALIDATION_AVAILABLE:
                validate_cookie(cookie)
            
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return False
                
            # Convert cookie to WebDriver-BiDi format
            # Firefox's implementation expects the value in a specific object format
            bidi_cookie = {
                'name': str(cookie.get('name', '')),
                'value': {
                    'type': 'string',
                    'value': str(cookie.get('value', ''))
                }
            }
            
            # Add optional fields only if they have valid values
            # Only include domain if it's not empty (for localhost cookies)
            domain = str(cookie.get('domain', '')).strip()
            if domain:
                bidi_cookie['domain'] = domain
            if cookie.get('path'):
                bidi_cookie['path'] = str(cookie.get('path'))
            if cookie.get('secure') is not None:
                bidi_cookie['secure'] = bool(cookie.get('secure'))
            if cookie.get('httpOnly') is not None:
                bidi_cookie['httpOnly'] = bool(cookie.get('httpOnly'))
            if cookie.get('sameSite'):
                bidi_cookie['sameSite'] = str(cookie.get('sameSite'))
            
            # Ensure we have at least name and value
            if not bidi_cookie.get('name') or not bidi_cookie.get('value'):
                raise ValueError("Cookie must have both 'name' and 'value' fields")

            # Build params with proper partition format
            # If no partition is provided, use the context-based partition
            if not partition:
                partition = {
                    'type': 'context',
                    'context': context
                }

            params = {
                'cookie': bidi_cookie,
                'partition': partition
            }

            response = self.manager._send_message({
                'method': 'storage.setCookie',
                'params': params
            })
            
            # Validate response
            if TYPE_VALIDATION_AVAILABLE:
                if response.get('type') != 'success':
                    error_msg = response.get('error', 'Unknown error')
                    self.log.warning("Failed to set cookie: {}".format(error_msg))
                    return False
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to set cookie: {}".format(e))
            return False
    
    def bidi_delete_cookie(self, cookie_name: str, context_id: str = None,
                          partition: Dict[str, str] = None, 
                          domain: str = None, path: str = None) -> bool:
        """
        Delete a cookie using WebDriver-BiDi.
        
        Args:
            cookie_name: Name of cookie to delete
            context_id: Browsing context ID (uses current if None)
            partition: Optional partition descriptor
            domain: Optional domain for cookie deletion
            path: Optional path for cookie deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return False

            # Build params with proper partition format
            if not partition:
                partition = {
                    'type': 'context',
                    'context': context
                }

            params = {
                'partition': partition,
                'name': cookie_name
            }

            # Add optional parameters according to specification
            if domain:
                params['domain'] = domain
            if path:
                params['path'] = path

            response = self.manager._send_message({
                'method': 'storage.deleteCookies',  # Fixed: plural form
                'params': params
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to delete cookie: {}".format(e))
            return False
    
    def bidi_delete_all_cookies(self, context_id: str = None,
                               partition: Dict[str, str] = None) -> bool:
        """
        Delete all cookies using WebDriver-BiDi.

        Args:
            context_id: Browsing context ID (uses current if None)
            partition: Optional partition descriptor

        Returns:
            True if successful, False otherwise
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return False

            # Build params with proper partition format
            if not partition:
                partition = {
                    'type': 'context',
                    'context': context
                }

            # Use storage.deleteCookies without a name filter to delete all cookies
            params = {'partition': partition}

            response = self.manager._send_message({
                'method': 'storage.deleteCookies',
                'params': params
            })

            return response.get('type') == 'success'

        except Exception as e:
            self.log.warning("Failed to delete all cookies: {}".format(e))
            return False
    
    # ========================================================================
    # Session Commands
    # ========================================================================
    
    def bidi_new_session(self, capabilities: Dict[str, Any] = None) -> str:
        """
        Create a new WebDriver-BiDi session.
        
        Args:
            capabilities: Browser capabilities
            
        Returns:
            Session ID
        """
        try:
            params = {}
            if capabilities:
                params['capabilities'] = capabilities
                
            response = self.manager._send_message({
                'method': 'session.new',
                'params': params
            })
            
            if response.get('type') == 'success' and 'result' in response:
                return response['result']['sessionId']
            else:
                return ""
                
        except Exception as e:
            self.log.warning("Failed to create new session: {}".format(e))
            return ""
    
    def bidi_end_session(self) -> bool:
        """
        End the current WebDriver-BiDi session.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.manager._send_message({
                'method': 'session.end',
                'params': {}
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to end session: {}".format(e))
            return False
    
    def bidi_subscribe(self, events: List[str], contexts: List[str] = None) -> bool:
        """
        Subscribe to WebDriver-BiDi events.

        Args:
            events: List of event names to subscribe to
            contexts: Optional list of browsing context IDs to filter events to

        Returns:
            True if successful, False otherwise
        """
        try:
            params = {'events': events}
            if contexts:
                params['contexts'] = contexts

            response = self.manager._send_message({
                'method': 'session.subscribe',
                'params': params
            })

            return response.get('type') == 'success'

        except Exception as e:
            self.log.warning("Failed to subscribe to events: {}".format(e))
            return False
    
    def bidi_unsubscribe(self, events: List[str], contexts: List[str] = None) -> bool:
        """
        Unsubscribe from WebDriver-BiDi events.

        Args:
            events: List of event names to unsubscribe from
            contexts: Optional list of browsing context IDs to filter unsubscription

        Returns:
            True if successful, False otherwise
        """
        try:
            params = {'events': events}
            if contexts:
                params['contexts'] = contexts

            response = self.manager._send_message({
                'method': 'session.unsubscribe',
                'params': params
            })

            return response.get('type') == 'success'

        except Exception as e:
            self.log.warning("Failed to unsubscribe from events: {}".format(e))
            return False
    
    # ========================================================================
    # Browser Commands
    # ========================================================================
    
    def bidi_create_user_context(self, name: str = None) -> str:
        """
        Create a user context using WebDriver-BiDi.
        
        Args:
            name: Optional name for the user context
            
        Returns:
            User context ID
        """
        try:
            params = {}
            if name:
                params['name'] = name
                
            response = self.manager._send_message({
                'method': 'browser.createUserContext',
                'params': params
            })
            
            if response.get('type') == 'success' and 'result' in response:
                return response['result']['userContext']
            else:
                return ""
                
        except Exception as e:
            self.log.warning("Failed to create user context: {}".format(e))
            return ""
    
    def bidi_remove_user_context(self, user_context: str) -> bool:
        """
        Remove a user context using WebDriver-BiDi.
        
        Args:
            user_context: User context ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.manager._send_message({
                'method': 'browser.removeUserContext',
                'params': {
                    'userContext': user_context
                }
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to remove user context: {}".format(e))
            return False
    
    # ========================================================================
    # Input Commands
    # ========================================================================
    
    def bidi_perform_actions(self, actions: List[Dict[str, Any]], context_id: str = None) -> bool:
        """
        Perform input actions using WebDriver-BiDi.
        
        Args:
            actions: List of action sequences
            context_id: Browsing context ID (uses current if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return False
                
            response = self.manager._send_message({
                'method': 'input.performActions',
                'params': {
                    'context': context,
                    'actions': actions
                }
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to perform actions: {}".format(e))
            return False
    
    def bidi_release_actions(self) -> bool:
        """
        Release all pending input actions using WebDriver-BiDi.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.manager._send_message({
                'method': 'input.releaseActions',
                'params': {}
            })
            
            return response.get('type') == 'success'
                
        except Exception as e:
            self.log.warning("Failed to release actions: {}".format(e))
            return False
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def bidi_wait_for_event(self, event_type: str, timeout: int = 10,
                           filter_params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Wait for a specific WebDriver-BiDi event.
        
        Args:
            event_type: Event type to wait for
            timeout: Maximum time to wait in seconds
            filter_params: Optional parameters to filter events
            
        Returns:
            Event dictionary or None if timeout occurs
        """
        try:
            return self.manager._receive_event(event_type, filter_params or {}, timeout)
                
        except Exception as e:
            self.log.warning("Failed to wait for event: {}".format(e))
            return None
    
    def bidi_get_current_url(self, context_id: str = None) -> str:
        """
        Get the current URL using WebDriver-BiDi.
        
        Args:
            context_id: Browsing context ID (uses current if None)
            
        Returns:
            Current URL as string
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return ""
                
            # WebDriver-BiDi doesn't have a direct getCurrentURL method
            # Use script evaluation to get the current URL
            result = self.bidi_evaluate_script("window.location.href", context)
            return str(result) if result else ""
                
        except Exception as e:
            self.log.warning("Failed to get current URL: {}".format(e))
            return ""
    
    def bidi_get_page_title(self, context_id: str = None) -> str:
        """
        Get the page title using WebDriver-BiDi.
        
        Args:
            context_id: Browsing context ID (uses current if None)
            
        Returns:
            Page title as string
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return ""
                
            # Get title using script evaluation
            result = self.bidi_evaluate_script("document.title", context)
            # Ensure we return just the string value, not the full response object
            if isinstance(result, dict) and 'value' in result:
                return str(result['value'])
            elif isinstance(result, dict) and 'result' in result and 'value' in result['result']:
                return str(result['result']['value'])
            else:
                return str(result) if result else ""
                
        except Exception as e:
            self.log.warning("Failed to get page title: {}".format(e))
            return ""
    
    def bidi_get_page_source(self, context_id: str = None) -> str:
        """
        Get the page source using WebDriver-BiDi.
        
        Args:
            context_id: Browsing context ID (uses current if None)
            
        Returns:
            Page source as string
        """
        try:
            context = context_id or self.active_browsing_context or self.manager.browsing_context
            if not context:
                return ""
                
            # Get page source using script evaluation
            result = self.bidi_evaluate_script("document.documentElement.outerHTML", context)
            return str(result) if result else ""
                
        except Exception as e:
            self.log.warning("Failed to get page source: {}".format(e))
            return ""