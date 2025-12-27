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
from .webdriver_bidi_mixin import WebDriverBiDiMixin


class FirefoxRemoteDebugInterface(WebDriverBiDiMixin):
    """
    High-level interface for Firefox remote debugging.
    
    This class provides a more convenient interface similar to ChromeController's
    ChromeRemoteDebugInterface, but adapted for Firefox's protocol.
    It inherits from WebDriverBiDiMixin to provide comprehensive WebDriver-BiDi functionality.
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

        # Request logging state (per-tab, single-threaded)
        self._request_logging_enabled = False
        self._request_log_cache = {}  # url -> {'url': url, 'mimetype': str, 'content': bytes}
        self._data_collector_id = None
    
    def __enter__(self):
        """Context manager entry"""
        self.manager.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Disable request logging if enabled
        if self._request_logging_enabled:
            try:
                self.disable_request_logging()
            except Exception as e:
                self.log.debug("Error disabling request logging on exit: {}".format(e))

        return self.manager.__exit__(exc_type, exc_val, exc_tb)
    
    def blocking_navigate_and_get_source(self, url: str, timeout: int = 30) -> str:
        """
        Navigate to a URL and get the page source (blocking).

        This is similar to ChromeController's blocking_navigate_and_get_source.
        """
        # Navigate to URL using THIS tab's context
        self.blocking_navigate(url, timeout)

        # Get page source
        return self.get_page_source()
    
    def get_page_source(self) -> str:
        """Get the page source for the current browsing context"""
        try:
            # Use the BiDi method from the mixin
            return self.bidi_get_page_source()
        except Exception as e:
            self.log.warning("Failed to get page source: {}".format(e))
            return ""
    
    def get_current_url(self) -> str:
        """Get the current URL for the browsing context"""
        try:
            # Use the BiDi method from the mixin
            return self.bidi_get_current_url()
        except Exception as e:
            self.log.warning("Failed to get current URL: {}".format(e))
            return ""
    
    def get_page_url_title(self) -> tuple:
        """Get page URL and title for the current browsing context"""
        url = self.get_current_url()
        
        try:
            # Use the BiDi method from the mixin
            title = self.bidi_get_page_title()
        except Exception as e:
            self.log.warning("Failed to get page title: {}".format(e))
            title = ""
        
        return title, url
    
    def take_screenshot(self, format: str = "png") -> bytes:
        """Take a screenshot of the current browsing context"""
        try:
            # Use the BiDi method from the mixin
            return self.bidi_capture_screenshot(format=format)
        except Exception as e:
            self.log.warning("Failed to take screenshot: {}".format(e))
            return b""
    
    def __exec_js(self, script: str, should_call: bool = False, args: list = None, await_promise: bool = False) -> Any:
        """
        Internal method to execute JavaScript in the browser context.
        
        Args:
            script: JavaScript code to execute
            should_call: Whether to call the script as a function
            args: Arguments to pass if should_call is True
            await_promise: Whether to await a promise result
        
        Returns:
            Result of JavaScript execution
        """
        try:
            if should_call:
                # Use the BiDi call function method
                return self.bidi_call_function(script, arguments=args, await_promise=await_promise)
            else:
                # Use the BiDi evaluate script method
                return self.bidi_evaluate_script(script, await_promise=await_promise)
        except Exception as e:
            self.log.warning("Failed to execute JavaScript: {}".format(e))
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
        return self.__exec_js(script, should_call=True, args=args, await_promise=False)
    
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
                script = 'window.location.href = "{}"'.format(url)
            else:
                script = "window.location.href = '{}'".format(url)
            
            result = self.execute_javascript_statement(script)
            return True
        except Exception as e:
            self.log.warning("Failed to navigate via JavaScript: {}".format(e))
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
            # Use the BiDi method from the mixin
            self.bidi_navigate(url, wait="complete")
            return True
        except Exception as e:
            self.log.warning("Blocking navigation failed: {}".format(e))
            return False
    
    def get_cookies(self) -> List[Dict[str, Any]]:
        """
        Get all cookies for the current browsing context.
        
        Returns:
            List of cookie dictionaries
        """
        try:
            # Use the BiDi method from the mixin
            return self.bidi_get_cookies()
        except Exception as e:
            self.log.warning("Failed to get cookies: {}".format(e))
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
            # Use the BiDi method from the mixin
            return self.bidi_set_cookie(cookie)
        except Exception as e:
            self.log.warning("Failed to set cookie: {}".format(e))
            return False
    
    def clear_cookies(self) -> bool:
        """
        Clear all cookies for the current browsing context.
        
        Returns:
            True if cookies were cleared successfully, False otherwise
        """
        try:
            # Use the BiDi method from the mixin
            return self.bidi_delete_all_cookies()
        except Exception as e:
            self.log.warning("Failed to clear cookies: {}".format(e))
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
                function() {
                    try {
                        // Try as CSS selector first
                        let element = document.querySelector(arguments[0]);
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
                            let result = document.evaluate(arguments[0], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
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
            """
            
            result = self.execute_javascript_function(script, [search])
            
            if result and result.get("found"):
                return result
            else:
                return None
                
        except Exception as e:
            self.log.warning("Failed to find element: {}".format(e))
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
                function() {
                    try {
                        let element = document.querySelector(arguments[0]);
                        if (element) {
                            element.click();
                            return true;
                        }
                        return false;
                    } catch (e) {
                        return false;
                    }
                }
            """
            
            result = self.execute_javascript_function(script, [selector])
            return bool(result)
                
        except Exception as e:
            self.log.warning("Failed to click element: {}".format(e))
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
                function() {
                    try {
                        let links = document.querySelectorAll('a[href*="' + arguments[0] + '"]');
                        if (links.length > 0) {
                            links[0].click();
                            return true;
                        }
                        return false;
                    } catch (e) {
                        return false;
                    }
                }
            """
            
            result = self.execute_javascript_function(script, [url])
            return bool(result)
                
        except Exception as e:
            self.log.warning("Failed to click link containing URL: {}".format(e))
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
                function() {
                    try {
                        window.scrollBy(arguments[1], arguments[0]);
                        return true;
                    } catch (e) {
                        return false;
                    }
                }
            """
            
            result = self.execute_javascript_function(script, [scroll_y_delta, scroll_x_delta])
            return bool(result)
                
        except Exception as e:
            self.log.warning("Failed to scroll page: {}".format(e))
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
            self.log.warning("Failed to get rendered page source: {}".format(e))
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
            self.log.warning("Failed to wait for DOM idle: {}".format(e))
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

    # ========================================================================
    # Request Logging Methods
    # ========================================================================

    def process_events(self, max_events: int = 100) -> int:
        """
        Process pending events from this tab's event queue.

        This should be called periodically when request logging is enabled
        to process network events and capture response data.

        Args:
            max_events: Maximum number of events to process in one call

        Returns:
            Number of events processed
        """
        # Only process if logging is enabled for this tab
        if not self._request_logging_enabled:
            return 0

        events_processed = 0
        context = self.active_browsing_context or self.manager.browsing_context

        # Get this tab's event queue
        event_queue = self.manager.get_event_queue_for_context(context)

        for _ in range(max_events):
            try:
                # Non-blocking get from this tab's queue
                event = event_queue.get_nowait()

                method = event.get("method")
                self.log.debug("process_events: Got event with method={}".format(method))

                # Check if this is a network.responseCompleted event
                if method == "network.responseCompleted":
                    params = event.get("params", {})
                    # Process this event (it's already in the right queue for this tab)
                    self._handle_response_completed_event(params)
                    events_processed += 1

            except:
                # Queue is empty
                break

        if events_processed > 0:
            self.log.debug("process_events: Processed {} network events".format(events_processed))

        return events_processed

    def poll_events(self, timeout: float = 0.1) -> int:
        """
        Poll for new events and process them for ALL tabs.

        This calls the manager's poll_for_events() to read from WebSocket,
        then processes network events for ALL tabs that have logging enabled.

        Args:
            timeout: How long to wait for events (seconds)

        Returns:
            Total number of events processed across all tabs
        """
        # Poll WebSocket for new events (distributes to per-tab queues)
        events_received = self.manager.poll_for_events(timeout)
        self.log.debug("poll_events: Received {} events from WebSocket".format(events_received))

        # Process events for ALL tabs with logging enabled
        total_processed = 0
        with self.manager._logging_interfaces_lock:
            # Create a copy of the list to avoid holding lock during processing
            interfaces_to_process = list(self.manager._logging_interfaces)

        for interface in interfaces_to_process:
            try:
                processed = interface.process_events()
                total_processed += processed
            except Exception as e:
                self.log.warning("Error processing events for interface: {}".format(e))

        self.log.debug("poll_events: Processed {} total network events across all tabs".format(total_processed))

        return total_processed

    def _handle_response_completed_event(self, params: Dict[str, Any]):
        """Handle a network.responseCompleted event

        Note: Caller should have already verified this event belongs to our context
        """
        try:
            # Extract request and response information
            request_data = params.get("request", {})
            response_data = params.get("response", {})

            request_id = request_data.get("request")  # This is the request ID string
            url = response_data.get("url", "")

            if not request_id or not url:
                return

            # Get MIME type from response headers
            mimetype = "application/octet-stream"  # Default
            headers = response_data.get("headers", [])
            for header in headers:
                if header.get("name", "").lower() == "content-type":
                    mimetype = header.get("value", {}).get("value", mimetype)
                    break

            # Fetch the response data using network.getData
            try:
                # Use our data collector to get the response body
                params = {
                    'dataType': 'response',
                    'request': request_id
                }
                # Include collector ID to ensure we get data from this tab's collector
                if self._data_collector_id:
                    params['collector'] = self._data_collector_id

                data_response = self.manager._send_message({
                    'method': 'network.getData',
                    'params': params
                })

                # Extract the response body
                if data_response.get("type") == "success" and "result" in data_response:
                    result = data_response["result"]

                    # The response format is {"bytes": {"type": "string"|"base64", "value": "..."}}
                    if "bytes" in result:
                        bytes_value = result["bytes"]
                        value_type = bytes_value.get("type")

                        if value_type == "string":
                            # Data is a string value, encode to bytes
                            content = bytes_value.get("value", "").encode('utf-8')
                        elif value_type == "base64":
                            # Data is base64 encoded
                            import base64
                            content = base64.b64decode(bytes_value.get("value", ""))
                        else:
                            # Unknown format
                            self.log.warning("Unknown bytes type: {}".format(value_type))
                            return

                        # Store in cache
                        self._request_log_cache[url] = {
                            'url': url,
                            'mimetype': mimetype,
                            'content': content
                        }

                        self.log.debug("Cached response for URL: {} ({} bytes)".format(url, len(content)))

            except Exception as e:
                self.log.debug("Failed to fetch response data for {}: {}".format(url, e))

        except Exception as e:
            self.log.debug("Error handling responseCompleted event: {}".format(e))

    def enable_request_logging(self):
        """
        Enable request logging for this browsing context.

        This will start capturing all HTTP(s) responses fetched by the browser.
        You must call poll_events() periodically to process captured responses.
        """
        if self._request_logging_enabled:
            self.log.warning("Request logging already enabled")
            return

        try:
            context = self.active_browsing_context or self.manager.browsing_context
            if not context:
                raise FirefoxError("No browsing context available")

            # Add a data collector for response data
            # Set max size to 100MB per response
            response = self.manager._send_message({
                'method': 'network.addDataCollector',
                'params': {
                    'dataTypes': ['response'],
                    'maxEncodedDataSize': 100 * 1024 * 1024,
                    'contexts': [context]
                }
            })

            if response.get("type") == "success" and "result" in response:
                self._data_collector_id = response["result"].get("collector")

            # Use global subscription approach for multi-tab support
            with self.manager.network_subscription_lock:
                if not self.manager.network_events_subscribed:
                    # First tab to enable logging - subscribe globally
                    self.bidi_subscribe(["network.responseCompleted"])
                    self.manager.network_events_subscribed = True
                    self.log.debug("Subscribed to network events globally")

                self.manager.network_logging_refs += 1
                self.log.debug("Network logging refs: {}".format(self.manager.network_logging_refs))

            # Register this interface for automatic polling
            with self.manager._logging_interfaces_lock:
                if self not in self.manager._logging_interfaces:
                    self.manager._logging_interfaces.append(self)

            # Track this context as having logging enabled
            with self.manager.logging_contexts_lock:
                self.manager.logging_enabled_contexts.add(context)

            self._request_logging_enabled = True
            self.log.info("Request logging enabled - call poll_events() to process responses")

        except Exception as e:
            self.log.error("Failed to enable request logging: {}".format(e))
            raise

    def disable_request_logging(self):
        """
        Disable request logging for this browsing context.

        This will stop capturing responses and clear the cache.
        """
        if not self._request_logging_enabled:
            return

        try:
            # Unregister this interface from automatic polling
            with self.manager._logging_interfaces_lock:
                if self in self.manager._logging_interfaces:
                    self.manager._logging_interfaces.remove(self)

            # Remove this context from logging enabled set
            context = self.active_browsing_context or self.manager.browsing_context
            with self.manager.logging_contexts_lock:
                self.manager.logging_enabled_contexts.discard(context)

            # Use global subscription approach for multi-tab support
            with self.manager.network_subscription_lock:
                self.manager.network_logging_refs -= 1
                self.log.debug("Network logging refs: {}".format(self.manager.network_logging_refs))

                if self.manager.network_logging_refs == 0 and self.manager.network_events_subscribed:
                    # Last tab to disable logging - unsubscribe globally
                    self.bidi_unsubscribe(["network.responseCompleted"])
                    self.manager.network_events_subscribed = False
                    self.log.debug("Unsubscribed from network events globally")

            # Remove data collector
            if self._data_collector_id:
                try:
                    self.manager._send_message({
                        'method': 'network.removeDataCollector',
                        'params': {
                            'collector': self._data_collector_id
                        }
                    })
                except Exception as e:
                    self.log.debug("Failed to remove data collector: {}".format(e))

                self._data_collector_id = None

            # Clear cache
            self._request_log_cache.clear()

            self._request_logging_enabled = False
            self.log.info("Request logging disabled")

        except Exception as e:
            self.log.error("Failed to disable request logging: {}".format(e))
            raise

    def get_fetched_urls(self) -> List[str]:
        """
        Get list of URLs that have been captured.

        Returns:
            List of URLs present in the cache
        """
        return list(self._request_log_cache.keys())

    def get_content_for_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get the cached content for a specific URL.

        Args:
            url: The URL to get content for

        Returns:
            Dictionary with 'url', 'mimetype', and 'content' keys, or None if not found
        """
        return self._request_log_cache.get(url)

    def clear_request_log_cache(self):
        """
        Clear the request log cache without disabling logging.

        This is useful to prevent unbounded memory growth when navigating
        to many pages.
        """
        self._request_log_cache.clear()
        self.log.debug("Request log cache cleared")