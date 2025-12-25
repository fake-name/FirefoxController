#!/usr/bin/env python3

"""
FirefoxController Main Interface

This module provides the high-level interface for Firefox remote debugging,
similar to ChromeController's ChromeRemoteDebugInterface.
"""

import logging
import time
import json
import base64
from typing import Optional, Dict, Any, List, Union

from .execution_manager import FirefoxExecutionManager
from .exceptions import FirefoxError


class FirefoxRemoteDebugInterface:
    """
    High-level interface for Firefox remote debugging.
    
    This class provides a more convenient interface similar to ChromeController's
    ChromeRemoteDebugInterface, but adapted for Firefox's protocol.
    """
    
    def __init__(self,
                 binary: str = "firefox",
                 host: str = "localhost", 
                 port: int = 6000,
                 headless: bool = False,
                 additional_options: List[str] = None,
                 profile_dir: str = None,
                 manager: Optional['FirefoxExecutionManager'] = None):
        """
        Initialize Firefox remote debug interface.
        
        Args:
            binary: Path to Firefox binary
            host: Host to connect to
            port: Debug port to use
            headless: Run Firefox in headless mode
            additional_options: Additional command line options
            profile_dir: Custom profile directory (None for temporary profile)
            manager: Optional execution manager (for multi-tab support)
        """
        if manager:
            # Use the provided manager (for multi-tab support)
            self.manager = manager
        else:
            # Create a new manager (for single-tab use)
            self.manager = FirefoxExecutionManager(
                binary=binary,
                host=host,
                port=port,
                headless=headless,
                additional_options=additional_options,
                profile_dir=profile_dir
            )
        
        self.log = logging.getLogger("FirefoxController.RemoteDebugInterface")
        
        # This interface is associated with a specific browsing context
        # The manager tracks all contexts, this interface tracks its own
        self.active_browsing_context = None  # Will be set when associated with a context
    
    def __enter__(self):
        """Context manager entry"""
        self.manager.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        return self.manager.__exit__(exc_type, exc_val, exc_tb)
    
    def blocking_navigate_and_get_source(self, url: str, timeout: int = 30) -> str:
        """
        Navigate to a URL and get the page source (blocking).
        
        This is similar to ChromeController's blocking_navigate_and_get_source.
        """
        # Navigate to URL using WebDriver BiDi
        self.manager.navigate(url, timeout)
        
        # Get page source
        return self.get_page_source()
    
    def get_page_source(self) -> str:
        """Get the page source for the current browsing context"""
        try:
            # Use the interface's own browsing context, not the manager's global one
            context = self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise FirefoxError("No browsing context available")
            
            # Get page source using WebDriver BiDi
            # Note: WebDriver BiDi doesn't have a direct getDOM command, so we use executeScript
            response = self.manager._send_message({
                'method': 'script.evaluate',
                'params': {
                    'expression': 'document.documentElement.outerHTML',
                    'target': {'context': context},
                    'awaitPromise': False
                }
            })
            
            # The response structure is: response["result"]["result"]["value"]
            if "result" in response and "result" in response["result"] and "value" in response["result"]["result"]:
                return str(response["result"]["result"]["value"])
            else:
                return ""
                
        except Exception as e:
            self.log.warning(f"Failed to get page source: {e}")
            return ""
    
    def get_current_url(self) -> str:
        """Get the current URL for the browsing context"""
        try:
            if not self.manager.browsing_context:
                raise FirefoxError("No browsing context available")
            
            # Method 1: Try to get URL from browsing context info (most reliable)
            try:
                # Use the interface's own browsing context, not the manager's global one
                context_id = self.active_browsing_context or self.manager.browsing_context
                
                # Get the browsing context information which includes URL
                contexts = self.manager._list_browsing_contexts()
                
                # Find our current browsing context
                for context in contexts:
                    if context.get("actor") == context_id:
                        url = context.get("url", "")
                        if url:
                            return url
                        break
            except Exception:
                pass
            
            # Method 2: Try WebDriver BiDi method
            try:
                response = self.manager._send_message({
                    'method': 'browsingContext.getCurrentURL',
                    'params': {
                        'context': self.manager.browsing_context
                    }
                })
                
                if "result" in response and "url" in response["result"]:
                    return response["result"]["url"]
            except Exception:
                pass
            
            # Method 3: Fallback to JavaScript (always works but less reliable)
            try:
                response = self.manager._send_message({
                    'method': 'script.evaluate',
                    'params': {
                        'expression': 'window.location.href',
                        'target': {'context': self.manager.browsing_context},
                        'awaitPromise': False
                    }
                })
                
                # The response structure is: response["result"]["result"]["value"]
                if "result" in response and "result" in response["result"] and "value" in response["result"]["result"]:
                    return str(response["result"]["result"]["value"])
            except Exception:
                pass
            
            return ""
                
        except Exception as e:
            self.log.warning(f"Failed to get current URL: {e}")
            return ""
    
    def get_page_url_title(self) -> tuple:
        """Get page URL and title for the current browsing context"""
        url = self.get_current_url()
        
        try:
            # Get title using WebDriver BiDi
            response = self.manager._send_message({
                'method': 'script.evaluate',
                'params': {
                    'expression': 'document.title',
                    'target': {'context': self.manager.browsing_context},
                    'awaitPromise': False
                }
            })
            
            # The response structure is: response["result"]["result"]["value"]
            if "result" in response and "result" in response["result"] and "value" in response["result"]["result"]:
                title = str(response["result"]["result"]["value"])
            else:
                title = ""
                
        except Exception as e:
            self.log.warning(f"Failed to get page title: {e}")
            title = ""
        
        return title, url
    
    def take_screenshot(self, format: str = "png") -> bytes:
        """Take a screenshot of the current browsing context"""
        try:
            if not self.manager.browsing_context:
                raise FirefoxError("No browsing context available")
            
            # Take screenshot using WebDriver BiDi
            response = self.manager._send_message({
                'method': 'browsingContext.captureScreenshot',
                'params': {
                    'context': self.manager.browsing_context,
                    'format': format
                }
            })
            
            if "result" in response and "data" in response["result"]:
                return base64.b64decode(response["result"]["data"])
            else:
                return b""
                
        except Exception as e:
            self.log.warning(f"Failed to take screenshot: {e}")
            return b""
    
    def __exec_js(self, script: str, should_call: bool = False, args: list = None) -> Any:
        """
        Internal method to execute JavaScript in the browser context.
        
        Args:
            script: JavaScript code to execute
            should_call: Whether to call the script as a function
            args: Arguments to pass if should_call is True
        
        Returns:
            Result of JavaScript execution
        """
        try:
            # Use the interface's own browsing context, not the manager's global one
            context = self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise FirefoxError("No browsing context available")
            
            if should_call:
                # Execute as function call
                if args is None:
                    args = []
                # Create a function call expression
                call_expr = f"({script}).apply(null, {json.dumps(args)})"
                response = self.manager._send_message({
                    'method': 'script.evaluate',
                    'params': {
                        'expression': call_expr,
                        'target': {'context': context},
                        'awaitPromise': True
                    }
                })
            else:
                # Execute as statement
                response = self.manager._send_message({
                    'method': 'script.evaluate',
                    'params': {
                        'expression': script,
                        'target': {'context': context},
                        'awaitPromise': False
                    }
                })
            
            # Parse the WebDriver BiDi response structure
            # The response has nested result objects
            if "result" in response:
                result_obj = response["result"]
                # Check if this is the outer result with type/success
                if isinstance(result_obj, dict) and "type" in result_obj and result_obj["type"] == "success":
                    inner_result = result_obj.get("result", {})
                    if "value" in inner_result:
                        return inner_result["value"]
                    elif "type" in inner_result and "value" in inner_result:
                        # Some responses have type and value at the same level
                        return inner_result["value"]
                # Direct value access (older style)
                elif "value" in result_obj:
                    return result_obj["value"]
            
            return None
                
        except Exception as e:
            self.log.warning(f"Failed to execute JavaScript: {e}")
            return None
    
    def execute_javascript_statement(self, script: str) -> Any:
        """
        Execute a JavaScript statement in the browser context.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result of JavaScript execution
        """
        return self.__exec_js(script, should_call=False)
    
    def execute_javascript_function(self, script: str, args: list = None) -> Any:
        """
        Execute a JavaScript function in the browser context.
        
        Args:
            script: JavaScript function definition
            args: Arguments to pass to the function
            
        Returns:
            Result of function execution
        """
        return self.__exec_js(script, should_call=True, args=args)
    
    def navigate_to(self, url: str) -> bool:
        """
        Navigate to a URL using JavaScript (window.location.href).
        
        This is useful for referrer spoofing and stateful navigation.
        
        Args:
            url: URL to navigate to
            
        Returns:
            True if navigation was initiated, False otherwise
        """
        try:
            if "'" in url:
                # Use double quotes if URL contains single quotes
                script = f'window.location.href = "{url}"'
            else:
                script = f"window.location.href = '{url}'"
            
            result = self.execute_javascript_statement(script)
            return True
        except Exception as e:
            self.log.warning(f"Failed to navigate via JavaScript: {e}")
            return False
    
    def blocking_navigate(self, url: str, timeout: int = 30) -> bool:
        """
        Perform a blocking navigation to a URL.
        
        Args:
            url: URL to navigate to
            timeout: Maximum time to wait for navigation to complete
            
        Returns:
            True if navigation succeeded, False otherwise
        """
        try:
            # Use the existing navigate method which is already blocking
            result = self.manager.navigate(url, timeout)
            return result.get("status") == "success"
        except Exception as e:
            self.log.warning(f"Blocking navigation failed: {e}")
            return False
    
    def get_cookies(self) -> List[Dict[str, Any]]:
        """
        Get all cookies for the current browsing context.
        
        Returns:
            List of cookie dictionaries
        """
        try:
            if not self.manager.browsing_context:
                raise FirefoxError("No browsing context available")
            
            # Get cookies using JavaScript execution (fallback method)
            # WebDriver BiDi network commands may not be available in all versions
            script = """
                function getAllCookies() {
                    try {
                        // Return document.cookie parsed into an array of objects
                        const cookies = document.cookie.split(';').map(cookie => {
                            const [name, value] = cookie.trim().split('=');
                            return { name, value };
                        }).filter(cookie => cookie.name);
                        return cookies;
                    } catch (e) {
                        return [];
                    }
                }
                getAllCookies();
            """
            
            result = self.execute_javascript_statement(script)
            
            if result and isinstance(result, list):
                return result
            else:
                return []
                
        except Exception as e:
            self.log.warning(f"Failed to get cookies: {e}")
            return []
    
    def set_cookie(self, cookie: Dict[str, Any]) -> bool:
        """
        Set a cookie for the current browsing context.
        
        Args:
            cookie: Cookie dictionary with name, value, domain, etc.
            
        Returns:
            True if cookie was set successfully, False otherwise
        """
        try:
            if not self.manager.browsing_context:
                raise FirefoxError("No browsing context available")
            
            # Set cookie using JavaScript execution
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            domain = cookie.get("domain", "")
            path = cookie.get("path", "/")
            expires = cookie.get("expires", "")
            secure = cookie.get("secure", False)
            
            # Build cookie string
            cookie_str = f"{name}={value}"
            if domain:
                cookie_str += f"; domain={domain}"
            if path:
                cookie_str += f"; path={path}"
            if expires:
                cookie_str += f"; expires={expires}"
            if secure:
                cookie_str += "; secure"
            
            script = f"document.cookie = '{cookie_str}'"
            result = self.execute_javascript_statement(script)
            
            return True
                
        except Exception as e:
            self.log.warning(f"Failed to set cookie: {e}")
            return False
    
    def clear_cookies(self) -> bool:
        """
        Clear all cookies for the current browsing context.
        
        Returns:
            True if cookies were cleared successfully, False otherwise
        """
        try:
            if not self.manager.browsing_context:
                raise FirefoxError("No browsing context available")
            
            # Clear cookies by setting expiration to past date
            # This is a JavaScript-based approach since WebDriver BiDi network commands
            # may not be available in all versions
            script = """
                function clearAllCookies() {
                    try {
                        const cookies = document.cookie.split(';');
                        for (let i = 0; i < cookies.length; i++) {
                            const cookie = cookies[i];
                            const eqPos = cookie.indexOf('=');
                            const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
                            if (name) {
                                document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=' + window.location.hostname;
                            }
                        }
                        return true;
                    } catch (e) {
                        return false;
                    }
                }
                clearAllCookies();
            """
            
            result = self.execute_javascript_statement(script)
            return bool(result)
                
        except Exception as e:
            self.log.warning(f"Failed to clear cookies: {e}")
            return False
    
    def find_element(self, search: str) -> Optional[Dict[str, Any]]:
        """
        Find a DOM element using a CSS selector or XPath.
        
        Args:
            search: CSS selector or XPath expression
            
        Returns:
            Dictionary containing element information, or None if not found
        """
        try:
            # Try to find element using querySelector
            script = """
                function findElement(search) {
                    try {
                        // Try as CSS selector first
                        let element = document.querySelector(search);
                        if (element) {
                            return {
                                found: true,
                                tagName: element.tagName,
                                id: element.id,
                                className: element.className,
                                textContent: element.textContent?.substring(0, 100),
                                href: element.href,
                                outerHTML: element.outerHTML?.substring(0, 500)
                            };
                        }
                        
                        // Try as XPath if CSS selector fails
                        try {
                            let result = document.evaluate(search, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                            let xpathElement = result.singleNodeValue;
                            if (xpathElement) {
                                return {
                                    found: true,
                                    tagName: xpathElement.tagName,
                                    id: xpathElement.id,
                                    className: xpathElement.className,
                                    textContent: xpathElement.textContent?.substring(0, 100),
                                    href: xpathElement.href,
                                    outerHTML: xpathElement.outerHTML?.substring(0, 500)
                                };
                            }
                        } catch (e) {
                            // Not XPath either
                        }
                        
                        return { found: false };
                    } catch (e) {
                        return { found: false, error: e.message };
                    }
                }
                findElement(arguments[0]);
            """
            
            result = self.execute_javascript_function(script, [search])
            
            if result and result.get("found"):
                return result
            else:
                return None
                
        except Exception as e:
            self.log.warning(f"Failed to find element: {e}")
            return None
    
    def click_element(self, selector: str) -> bool:
        """
        Click a DOM element using a CSS selector.
        
        Args:
            selector: CSS selector for the element to click
            
        Returns:
            True if click was successful, False otherwise
        """
        try:
            script = """
                function clickElement(selector) {
                    try {
                        let element = document.querySelector(selector);
                        if (element) {
                            element.click();
                            return true;
                        }
                        return false;
                    } catch (e) {
                        return false;
                    }
                }
                clickElement(arguments[0]);
            """
            
            result = self.execute_javascript_function(script, [selector])
            return bool(result)
                
        except Exception as e:
            self.log.warning(f"Failed to click element: {e}")
            return False
    
    def click_link_containing_url(self, url: str) -> bool:
        """
        Click a link that contains a specific URL.
        
        Args:
            url: URL to search for in links
            
        Returns:
            True if a matching link was found and clicked, False otherwise
        """
        try:
            script = """
                function clickLinkContainingUrl(url) {
                    try {
                        let links = document.querySelectorAll('a[href*="' + url + '"]');
                        if (links.length > 0) {
                            links[0].click();
                            return true;
                        }
                        return false;
                    } catch (e) {
                        return false;
                    }
                }
                clickLinkContainingUrl(arguments[0]);
            """
            
            result = self.execute_javascript_function(script, [url])
            return bool(result)
                
        except Exception as e:
            self.log.warning(f"Failed to click link containing URL: {e}")
            return False
    
    def scroll_page(self, scroll_y_delta: int, scroll_x_delta: int = 0, mouse_pos_x: int = 10, mouse_pos_y: int = 10) -> bool:
        """
        Scroll the page by specified deltas.
        
        Args:
            scroll_y_delta: Vertical scroll amount (positive = down, negative = up)
            scroll_x_delta: Horizontal scroll amount (positive = right, negative = left)
            mouse_pos_x: Mouse X position for scroll events
            mouse_pos_y: Mouse Y position for scroll events
            
        Returns:
            True if scroll was successful, False otherwise
        """
        try:
            script = """
                function scrollPage(yDelta, xDelta) {
                    try {
                        window.scrollBy(xDelta, yDelta);
                        return true;
                    } catch (e) {
                        return false;
                    }
                }
                scrollPage(arguments[0], arguments[1]);
            """
            
            result = self.execute_javascript_function(script, [scroll_y_delta, scroll_x_delta])
            return bool(result)
                
        except Exception as e:
            self.log.warning(f"Failed to scroll page: {e}")
            return False
    
    def get_rendered_page_source(self, dom_idle_requirement_secs: int = 3, max_wait_timeout: int = 30) -> str:
        """
        Get the rendered page source after waiting for DOM to be idle.
        
        Args:
            dom_idle_requirement_secs: Number of seconds DOM must be idle
            max_wait_timeout: Maximum time to wait for DOM to become idle
            
        Returns:
            Rendered page source as string
        """
        try:
            # First wait for DOM to be idle
            self.wait_for_dom_idle(dom_idle_requirement_secs, max_wait_timeout)
            
            # Then get the page source
            return self.get_page_source()
                
        except Exception as e:
            self.log.warning(f"Failed to get rendered page source: {e}")
            return ""
    
    def wait_for_dom_idle(self, dom_idle_requirement_secs: int = 3, max_wait_timeout: int = 30) -> bool:
        """
        Wait for the DOM to be idle (no changes) for a specified period.
        
        Args:
            dom_idle_requirement_secs: Number of seconds DOM must be idle
            max_wait_timeout: Maximum time to wait for DOM to become idle
            
        Returns:
            True if DOM became idle, False if timeout occurred
        """
        try:
            start_time = time.time()
            last_dom_change = time.time()
            
            script = """
                // Get a simple DOM fingerprint
                function getDOMSignature() {
                    try {
                        // Count elements and get some basic info
                        return {
                            elementCount: document.querySelectorAll('*').length,
                            bodyTextLength: document.body.textContent.length,
                            timestamp: Date.now()
                        };
                    } catch (e) {
                        return { error: e.message };
                    }
                }
                getDOMSignature();
            """
            
            while time.time() - start_time < max_wait_timeout:
                current_signature = self.execute_javascript_statement(script)
                
                if current_signature and not current_signature.get("error"):
                    # If DOM hasn't changed for the required time, we're idle
                    if time.time() - last_dom_change >= dom_idle_requirement_secs:
                        return True
                    
                    # Store current signature for comparison
                    last_signature = current_signature
                    last_dom_change = time.time()
                
                time.sleep(0.5)  # Check every 500ms
            
            return False  # Timeout occurred
                
        except Exception as e:
            self.log.warning(f"Failed to wait for DOM idle: {e}")
            return False
    
    def new_tab(self, url: str = "about:blank") -> 'FirefoxRemoteDebugInterface':
        """
        Create a new tab and return a FirefoxRemoteDebugInterface instance for it.
        
        Args:
            url: URL to navigate to in the new tab
            
        Returns:
            FirefoxRemoteDebugInterface instance for the new tab
        """
        # Use the execution manager's new_tab method which returns an interface instance
        return self.manager.new_tab(url)