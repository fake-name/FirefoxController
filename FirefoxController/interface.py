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
from .exceptions import FirefoxError, FirefoxNavigateTimedOut
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
                 port: Optional[int] = 9222,
                 headless: bool = False,
                 additional_options: List[str] = None,
                 profile_dir: str = None,
                 manager: Optional['FirefoxExecutionManager'] = None):
        """
        Initialize Firefox remote debug interface.
        
        Args:
            binary: Path to Firefox binary
            host: Host to connect to
            port: Debug port to use (9222 default, None for automatic selection)
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

        # Default timeout for operations (can be changed with set_default_timeout())
        self.default_timeout = 30
    
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

    @property
    def port(self) -> int:
        """Get the actual port being used by Firefox"""
        return self.manager.port

    def set_default_timeout(self, timeout: int) -> None:
        """
        Set the default timeout for all operations.

        Args:
            timeout: Default timeout in seconds

        Example:
            firefox.set_default_timeout(60)  # Set all operations to 60 second timeout
        """
        self.default_timeout = timeout
        self.log.debug("Default timeout set to {} seconds".format(timeout))

    def blocking_navigate_and_get_source(self, url: str, timeout: int = None) -> str:
        """
        Navigate to a URL and get the page source (blocking).

        Args:
            url: URL to navigate to
            timeout: Timeout in seconds (uses default_timeout if None)

        Returns:
            Page source HTML as string
        """
        # Use default timeout if not specified
        timeout = timeout if timeout is not None else self.default_timeout

        # Navigate to URL using THIS tab's context
        self.blocking_navigate(url, timeout)

        # Get page source
        return self.get_page_source(timeout=timeout)
    
    def get_page_source(self, timeout: int = None) -> str:
        """Get the page source for the current browsing context

        Args:
            timeout: Timeout in seconds (uses default_timeout if None)

        Returns:
            Page source HTML as string
        """
        # Use default timeout if not specified
        timeout = timeout if timeout is not None else self.default_timeout

        try:
            # Use the BiDi method from the mixin
            return self.bidi_get_page_source(timeout=timeout)
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
    
    def __exec_js(self, script: str, should_call: bool = False, args: list = None, await_promise: bool = False, timeout: int = None) -> Any:
        """
        Internal method to execute JavaScript in the browser context.

        Args:
            script: JavaScript code to execute
            should_call: Whether to call the script as a function
            args: Arguments to pass if should_call is True
            await_promise: Whether to await a promise result
            timeout: Timeout in seconds (uses default_timeout if None)

        Returns:
            Result of JavaScript execution
        """
        # Use default timeout if not specified
        timeout = timeout if timeout is not None else self.default_timeout

        try:
            if should_call:
                # Use the BiDi call function method
                return self.bidi_call_function(script, arguments=args, await_promise=await_promise, timeout=timeout)
            else:
                # Use the BiDi evaluate script method
                return self.bidi_evaluate_script(script, await_promise=await_promise, timeout=timeout)
        except Exception as e:
            self.log.warning("Failed to execute JavaScript: {}".format(e))
            return None
    
    def execute_javascript_statement(self, script: str, timeout: int = None) -> Any:
        """
        Execute a JavaScript statement in the browser context.

        Args:
            script: JavaScript code to execute
            timeout: Timeout in seconds (uses default_timeout if None)

        Returns:
            Result of JavaScript execution
        """
        return self.__exec_js(script, should_call=False, timeout=timeout)

    def execute_javascript_function(self, script: str, args: list = None, timeout: int = None) -> Any:
        """
        Execute a JavaScript function in the browser context.

        Args:
            script: JavaScript function definition
            args: Arguments to pass to the function
            timeout: Timeout in seconds (uses default_timeout if None)

        Returns:
            Result of function execution
        """
        return self.__exec_js(script, should_call=True, args=args, await_promise=False, timeout=timeout)
    
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
    
    def blocking_navigate(self, url: str, timeout: int = None) -> bool:
        """
        Perform a blocking navigation to a URL.

        Args:
            url: URL to navigate to
            timeout: Timeout in seconds (uses default_timeout if None)

        Returns:
            True if navigation succeeded, False otherwise

        Raises:
            FirefoxNavigateTimedOut: If navigation times out
        """
        # Use default timeout if not specified
        timeout = timeout if timeout is not None else self.default_timeout

        try:
            # Use the BiDi method from the mixin, passing timeout
            self.bidi_navigate(url, wait="complete", timeout=timeout)
            return True
        except FirefoxNavigateTimedOut:
            # Re-raise navigation timeout for user to handle
            self.log.error("Navigation to {} timed out after {} seconds".format(url, timeout))
            raise
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

    # ========================================================================
    # XHR Fetch Methods
    # ========================================================================

    def xhr_fetch(self, url: str, headers: Dict[str, str] = None,
                  post_data: str = None, post_type: str = None,
                  use_chunks: bool = False, chunk_size: int = 512 * 1024) -> Dict[str, Any]:
        """
        Fetch content via XMLHttpRequest without triggering Firefox's download manager.

        Uses FileReader.readAsDataURL() for efficient blob->base64 conversion with
        zero byte iteration. Subject to same-origin policy restrictions.

        Single requests limited to ~700KB due to WebSocket 1MB frame limit.
        For larger files, use use_chunks=True.

        Args:
            url: URL to fetch
            headers: Optional request headers
            post_data: Optional POST data
            post_type: Optional Content-Type for POST
            use_chunks: Enable chunked transfer for large files (default False)
            chunk_size: Chunk size in bytes when use_chunks=True (default 512KB, max ~700KB)

        Returns:
            Dict with keys: url, headers, resp_headers, post, response (text),
            content (bytes), mimetype, code
        """
        # Only use chunking if explicitly requested and not a POST
        if use_chunks and not post_data:
            try:
                head_result = self._xhr_head(url, headers)
                content_length = head_result.get('content_length', 0)

                # Use chunked transfer for files larger than chunk_size
                if content_length > chunk_size:
                    self.log.info("Large file detected ({} bytes), using chunked transfer".format(content_length))
                    return self._xhr_fetch_chunked(url, headers, content_length, chunk_size)
                elif content_length > 0:
                    self.log.debug("File size {} is below chunk threshold, using single request".format(content_length))
            except Exception as e:
                self.log.debug("HEAD request failed, falling back to normal fetch: {}".format(e))

        # Default: single request
        return self._xhr_fetch_single(url, headers, post_data, post_type)

    def _xhr_head(self, url: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Send HEAD request to get content length"""
        try:
            js_script = """
                function(url, headers) {
                    try {
                        var req = new XMLHttpRequest();
                        req.open("HEAD", url, false);

                        if (headers) {
                            let entries = Object.entries(headers);
                            for (let idx = 0; idx < entries.length; idx += 1) {
                                req.setRequestHeader(entries[idx][0], entries[idx][1]);
                            }
                        }

                        req.send();

                        var contentLength = parseInt(req.getResponseHeader("Content-Length")) || 0;

                        return {
                            content_length: contentLength,
                            mimetype: req.getResponseHeader("Content-Type"),
                            code: req.status
                        };
                    } catch (e) {
                        return { content_length: 0, code: 0, error: e.toString() };
                    }
                }
            """

            result = self.execute_javascript_function(js_script, [url, headers or {}])
            self.log.info("HEAD request result: {}".format(result))
            return result if result else {'content_length': 0, 'code': 0}
        except Exception as e:
            self.log.warning("HEAD request failed: {}".format(e))
            return {'content_length': 0, 'code': 0}

    def _xhr_fetch_chunked(self, url: str, headers: Dict[str, str],
                          content_length: int, chunk_size: int) -> Dict[str, Any]:
        """Fetch large file in chunks using Range requests"""
        try:
            chunks = []
            offset = 0
            resp_headers = None
            mimetype = None
            status_code = 0

            while offset < content_length:
                end = min(offset + chunk_size - 1, content_length - 1)

                # Add Range header
                chunk_headers = headers.copy() if headers else {}
                chunk_headers['Range'] = 'bytes={}-{}'.format(offset, end)

                self.log.info("Fetching chunk: bytes {}-{} of {}, headers={}".format(
                    offset, end, content_length, chunk_headers))

                # Fetch this chunk
                chunk_result = self._xhr_fetch_single(url, chunk_headers, None, None)
                self.log.info("Chunk result code: {}, content length: {}, error: {}".format(
                    chunk_result.get('code'), len(chunk_result.get('content', b'')),
                    chunk_result.get('error', 'none')))

                if chunk_result.get('code') not in (200, 206):  # 206 = Partial Content
                    raise Exception("Chunk fetch failed with code {}".format(chunk_result.get('code')))

                # Store metadata from first chunk
                if offset == 0:
                    resp_headers = chunk_result.get('resp_headers', '')
                    mimetype = chunk_result.get('mimetype')
                    status_code = chunk_result.get('code')

                # Append chunk data
                chunk_content = chunk_result.get('content', b'')
                chunks.append(chunk_content)

                offset += len(chunk_content)

                # Safety check
                if len(chunk_content) == 0:
                    break

            # Combine all chunks
            full_content = b''.join(chunks)

            # Try to decode as text
            try:
                response_text = full_content.decode('utf-8')
            except UnicodeDecodeError:
                response_text = ''

            return {
                'url': url,
                'headers': headers,
                'resp_headers': resp_headers,
                'post': None,
                'response': response_text,
                'content': full_content,
                'mimetype': mimetype,
                'code': status_code,
                'chunked': True,
                'chunks': len(chunks)
            }

        except Exception as e:
            self.log.error("Chunked fetch failed: {}".format(e))
            return {
                'url': url,
                'headers': headers,
                'resp_headers': '',
                'post': None,
                'response': '',
                'content': b'',
                'mimetype': None,
                'code': 0,
                'error': str(e)
            }

    def _xhr_fetch_single(self, url: str, headers: Dict[str, str] = None,
                         post_data: str = None, post_type: str = None) -> Dict[str, Any]:
        """Fetch content in a single request (internal method)"""
        try:
            # Use FileReader.readAsDataURL for efficient blob->base64 conversion
            js_script = """
                function(url, headers, post_data, post_type) {
                    return new Promise((resolve, reject) => {
                        var req = new XMLHttpRequest();
                        if (post_data) {
                            req.open("POST", url, true);
                            if (post_type) {
                                req.setRequestHeader("Content-Type", post_type);
                            }
                        } else {
                            req.open("GET", url, true);
                        }

                        req.responseType = 'blob';

                        if (headers) {
                            let entries = Object.entries(headers);
                            for (let idx = 0; idx < entries.length; idx += 1) {
                                console.log('Setting header:', entries[idx][0], '=', entries[idx][1]);
                                req.setRequestHeader(entries[idx][0], entries[idx][1]);
                            }
                        }

                        req.onload = function() {
                            // Use FileReader to convert blob to base64 - no byte iteration!
                            var reader = new FileReader();
                            reader.onloadend = function() {
                                // DataURL format: data:[<mediatype>][;base64],<data>
                                var dataUrl = reader.result;
                                var base64_response = dataUrl.split(',')[1];  // Extract base64 part

                                resolve({
                                    url: url,
                                    headers: headers,
                                    resp_headers: req.getAllResponseHeaders(),
                                    post: post_data,
                                    binary_response: base64_response,
                                    mimetype: req.getResponseHeader("Content-Type"),
                                    code: req.status
                                });
                            };
                            reader.onerror = function() {
                                resolve({
                                    url: url,
                                    headers: headers,
                                    resp_headers: '',
                                    post: post_data,
                                    binary_response: '',
                                    mimetype: null,
                                    code: 0,
                                    error: 'FileReader error'
                                });
                            };
                            reader.readAsDataURL(req.response);
                        };

                        req.onerror = function() {
                            resolve({
                                url: url,
                                headers: headers,
                                resp_headers: '',
                                post: post_data,
                                binary_response: '',
                                mimetype: null,
                                code: 0,
                                error: 'Network error'
                            });
                        };

                        if (post_data) {
                            req.send(post_data);
                        } else {
                            req.send();
                        }
                    });
                }
            """

            result = self.__exec_js(js_script, should_call=True, args=[url, headers or {}, post_data, post_type], await_promise=True)

            if result is None:
                return {
                    'url': url,
                    'headers': headers,
                    'resp_headers': '',
                    'post': post_data,
                    'response': '',
                    'content': b'',
                    'mimetype': None,
                    'code': 0
                }

            # Decode base64 response to bytes
            if 'binary_response' in result:
                try:
                    content = base64.b64decode(result['binary_response'])
                    result['content'] = content

                    # For backward compatibility, also try to decode as text
                    try:
                        result['response'] = content.decode('utf-8')
                    except UnicodeDecodeError:
                        # Binary content, not valid UTF-8
                        result['response'] = ''
                except Exception as e:
                    self.log.warning("Failed to decode binary response: {}".format(e))
                    result['content'] = b''
                    result['response'] = ''
            else:
                result['content'] = b''
                result['response'] = ''

            return result

        except Exception as e:
            self.log.warning("xhr_fetch failed: {}".format(e))
            return {
                'url': url,
                'headers': headers,
                'resp_headers': '',
                'post': post_data,
                'response': '',
                'content': b'',
                'mimetype': None,
                'code': 0,
                'error': str(e)
            }

    # ========================================================================
    # XPath Element Selection Methods
    # ========================================================================

    def get_element_by_xpath(self, xpath: str) -> Optional[Dict[str, Any]]:
        """
        Find a DOM element using an XPath expression.

        Args:
            xpath: XPath expression to evaluate

        Returns:
            Dictionary containing element information, or None if not found.
            The dictionary includes:
                - found: True if element was found
                - tagName: Element tag name
                - id: Element ID
                - className: Element class name
                - textContent: First 100 chars of text content
                - value: Input value (for form elements)
                - type: Input type (for input elements)
                - outerHTML: First 500 chars of outer HTML
        """
        try:
            script = """
                function(xpath) {
                    try {
                        let result = document.evaluate(
                            xpath,
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        let element = result.singleNodeValue;
                        if (element) {
                            return {
                                found: true,
                                tagName: element.tagName || '',
                                id: element.id || '',
                                className: element.className || '',
                                textContent: (element.textContent || '').substring(0, 100),
                                value: element.value !== undefined ? element.value : null,
                                type: element.type || null,
                                outerHTML: (element.outerHTML || '').substring(0, 500)
                            };
                        }
                        return { found: false };
                    } catch (e) {
                        return { found: false, error: e.message };
                    }
                }
            """

            result = self.execute_javascript_function(script, [xpath])

            if result and result.get("found"):
                return result
            else:
                return None

        except Exception as e:
            self.log.warning("Failed to get element by xpath: {}".format(e))
            return None

    def get_elements_by_xpath(self, xpath: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Find all DOM elements matching an XPath expression.

        Args:
            xpath: XPath expression to evaluate
            max_results: Maximum number of results to return (default 100)

        Returns:
            List of dictionaries containing element information
        """
        try:
            script = """
                function(xpath, maxResults) {
                    try {
                        let result = document.evaluate(
                            xpath,
                            document,
                            null,
                            XPathResult.ORDERED_NODE_ITERATOR_TYPE,
                            null
                        );
                        let elements = [];
                        let element;
                        let count = 0;
                        while ((element = result.iterateNext()) && count < maxResults) {
                            elements.push({
                                tagName: element.tagName || '',
                                id: element.id || '',
                                className: element.className || '',
                                textContent: (element.textContent || '').substring(0, 100),
                                value: element.value !== undefined ? element.value : null,
                                type: element.type || null,
                                outerHTML: (element.outerHTML || '').substring(0, 500)
                            });
                            count++;
                        }
                        return elements;
                    } catch (e) {
                        return [];
                    }
                }
            """

            result = self.execute_javascript_function(script, [xpath, max_results])
            return result if result else []

        except Exception as e:
            self.log.warning("Failed to get elements by xpath: {}".format(e))
            return []

    def select_input_by_xpath(self, xpath: str) -> bool:
        """
        Select (focus) an input element using an XPath expression.

        This method finds an input element using XPath and gives it focus,
        preparing it for keyboard input.

        Args:
            xpath: XPath expression that identifies the input element

        Returns:
            True if the element was found and focused, False otherwise
        """
        try:
            script = """
                function(xpath) {
                    try {
                        let result = document.evaluate(
                            xpath,
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        let element = result.singleNodeValue;
                        if (element && typeof element.focus === 'function') {
                            element.focus();
                            // For input elements, also select any existing text
                            if (typeof element.select === 'function') {
                                element.select();
                            }
                            return true;
                        }
                        return false;
                    } catch (e) {
                        return false;
                    }
                }
            """

            result = self.execute_javascript_function(script, [xpath])
            return bool(result)

        except Exception as e:
            self.log.warning("Failed to select input by xpath: {}".format(e))
            return False

    def click_element_by_xpath(self, xpath: str) -> bool:
        """
        Click a DOM element using an XPath expression.

        Args:
            xpath: XPath expression that identifies the element to click

        Returns:
            True if the element was found and clicked, False otherwise
        """
        try:
            script = """
                function(xpath) {
                    try {
                        let result = document.evaluate(
                            xpath,
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        let element = result.singleNodeValue;
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

            result = self.execute_javascript_function(script, [xpath])
            return bool(result)

        except Exception as e:
            self.log.warning("Failed to click element by xpath: {}".format(e))
            return False

    def get_input_value_by_xpath(self, xpath: str) -> Optional[str]:
        """
        Get the value of an input element using XPath.

        Args:
            xpath: XPath expression that identifies the input element

        Returns:
            The input value as a string, or None if element not found
        """
        try:
            script = """
                function(xpath) {
                    try {
                        let result = document.evaluate(
                            xpath,
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        let element = result.singleNodeValue;
                        if (element && element.value !== undefined) {
                            return element.value;
                        }
                        return null;
                    } catch (e) {
                        return null;
                    }
                }
            """

            return self.execute_javascript_function(script, [xpath])

        except Exception as e:
            self.log.warning("Failed to get input value by xpath: {}".format(e))
            return None

    def set_input_value_by_xpath(self, xpath: str, value: str) -> bool:
        """
        Set the value of an input element using XPath.

        Note: This sets the value directly via JavaScript, which doesn't
        trigger keyboard events. Use type_text_in_input() for more realistic
        input simulation.

        Args:
            xpath: XPath expression that identifies the input element
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            script = """
                function(xpath, value) {
                    try {
                        let result = document.evaluate(
                            xpath,
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        let element = result.singleNodeValue;
                        if (element) {
                            element.value = value;
                            // Trigger input and change events for frameworks that listen to them
                            element.dispatchEvent(new Event('input', { bubbles: true }));
                            element.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                        return false;
                    } catch (e) {
                        return false;
                    }
                }
            """

            result = self.execute_javascript_function(script, [xpath, value])
            return bool(result)

        except Exception as e:
            self.log.warning("Failed to set input value by xpath: {}".format(e))
            return False

    # ========================================================================
    # Keyboard Event Methods
    # ========================================================================

    def dispatch_key_event(self, key: str, event_type: str = "keydown",
                          modifiers: List[str] = None) -> bool:
        """
        Dispatch a keyboard event to the currently focused element.

        This uses the WebDriver-BiDi input.performActions command to send
        keyboard events in a realistic manner.

        Args:
            key: The key to dispatch (e.g., 'a', 'Enter', 'Backspace', 'Tab')
            event_type: Type of event ('keydown', 'keyup', or 'keypress')
            modifiers: List of modifier keys to hold ('Shift', 'Control', 'Alt', 'Meta')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build the key action sequence
            actions = []

            # Handle modifier keys
            modifier_actions = []
            if modifiers:
                for mod in modifiers:
                    modifier_actions.append({'type': 'keyDown', 'value': self._get_key_code(mod)})

            # Build the key action
            key_code = self._get_key_code(key)

            key_sequence = []
            # Add modifier key downs
            key_sequence.extend(modifier_actions)

            # Add the actual key event
            if event_type in ('keydown', 'keypress'):
                key_sequence.append({'type': 'keyDown', 'value': key_code})
            if event_type in ('keyup', 'keypress'):
                key_sequence.append({'type': 'keyUp', 'value': key_code})

            # Release modifiers in reverse order
            if modifiers:
                for mod in reversed(modifiers):
                    key_sequence.append({'type': 'keyUp', 'value': self._get_key_code(mod)})

            actions = [{
                'type': 'key',
                'id': 'keyboard',
                'actions': key_sequence
            }]

            return self.bidi_perform_actions(actions)

        except Exception as e:
            self.log.warning("Failed to dispatch key event: {}".format(e))
            return False

    def type_text(self, text: str, delay_ms: int = 0) -> bool:
        """
        Type text character by character using keyboard events.

        This method simulates realistic typing by sending individual key events
        for each character in the text string.

        Args:
            text: The text to type
            delay_ms: Delay between keystrokes in milliseconds (0 for no delay)

        Returns:
            True if all characters were typed successfully, False otherwise
        """
        try:
            # Build actions for all characters
            key_actions = []

            for char in text:
                key_code = self._get_key_code(char)
                key_actions.append({'type': 'keyDown', 'value': key_code})
                key_actions.append({'type': 'keyUp', 'value': key_code})
                if delay_ms > 0:
                    key_actions.append({'type': 'pause', 'duration': delay_ms})

            actions = [{
                'type': 'key',
                'id': 'keyboard',
                'actions': key_actions
            }]

            return self.bidi_perform_actions(actions)

        except Exception as e:
            self.log.warning("Failed to type text: {}".format(e))
            return False

    def type_text_in_input(self, xpath: str, text: str, clear_first: bool = True,
                          delay_ms: int = 0) -> bool:
        """
        Type text into an input field identified by XPath.

        This is a convenience method that combines selecting an input field
        and typing text into it, simulating realistic user interaction.

        Args:
            xpath: XPath expression identifying the input element
            text: Text to type into the input
            clear_first: If True, clear the input field before typing
            delay_ms: Delay between keystrokes in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # First, focus the input element
            if not self.select_input_by_xpath(xpath):
                self.log.warning("Could not find/focus input element: {}".format(xpath))
                return False

            # Give the focus a moment to take effect
            time.sleep(0.05)

            # Clear the field if requested
            if clear_first:
                # Select all and delete
                self.dispatch_key_event('a', modifiers=['Control'])
                time.sleep(0.02)
                self.dispatch_key_event('Backspace')
                time.sleep(0.02)

            # Type the text
            return self.type_text(text, delay_ms)

        except Exception as e:
            self.log.warning("Failed to type text in input: {}".format(e))
            return False

    def send_key_combination(self, keys: List[str]) -> bool:
        """
        Send a key combination (e.g., Ctrl+C, Alt+Tab).

        Args:
            keys: List of keys to press simultaneously. The last key is the
                  main key, all others are treated as modifiers.
                  Example: ['Control', 'Shift', 'a'] for Ctrl+Shift+A

        Returns:
            True if successful, False otherwise
        """
        if not keys:
            return False

        if len(keys) == 1:
            return self.dispatch_key_event(keys[0])

        # All keys except the last are modifiers
        modifiers = keys[:-1]
        main_key = keys[-1]

        return self.dispatch_key_event(main_key, modifiers=modifiers)

    def press_enter(self) -> bool:
        """
        Press the Enter key.

        Returns:
            True if successful, False otherwise
        """
        return self.dispatch_key_event('Enter')

    def press_tab(self) -> bool:
        """
        Press the Tab key.

        Returns:
            True if successful, False otherwise
        """
        return self.dispatch_key_event('Tab')

    def press_escape(self) -> bool:
        """
        Press the Escape key.

        Returns:
            True if successful, False otherwise
        """
        return self.dispatch_key_event('Escape')

    def _get_key_code(self, key: str) -> str:
        """
        Convert a key name to its WebDriver-BiDi key code.

        Args:
            key: Human-readable key name

        Returns:
            WebDriver-BiDi key code string
        """
        # Special keys mapping (WebDriver spec key values)
        # See: https://w3c.github.io/webdriver/#keyboard-actions
        special_keys = {
            # Modifier keys
            'Shift': '\uE008',
            'Control': '\uE009',
            'Ctrl': '\uE009',
            'Alt': '\uE00A',
            'Meta': '\uE03D',
            'Command': '\uE03D',
            'Win': '\uE03D',

            # Navigation keys
            'Enter': '\uE007',
            'Return': '\uE007',
            'Tab': '\uE004',
            'Escape': '\uE00C',
            'Esc': '\uE00C',
            'Backspace': '\uE003',
            'Delete': '\uE017',
            'Insert': '\uE016',

            # Arrow keys
            'ArrowUp': '\uE013',
            'Up': '\uE013',
            'ArrowDown': '\uE015',
            'Down': '\uE015',
            'ArrowLeft': '\uE012',
            'Left': '\uE012',
            'ArrowRight': '\uE014',
            'Right': '\uE014',

            # Other navigation
            'Home': '\uE011',
            'End': '\uE010',
            'PageUp': '\uE00E',
            'PageDown': '\uE00F',

            # Function keys
            'F1': '\uE031',
            'F2': '\uE032',
            'F3': '\uE033',
            'F4': '\uE034',
            'F5': '\uE035',
            'F6': '\uE036',
            'F7': '\uE037',
            'F8': '\uE038',
            'F9': '\uE039',
            'F10': '\uE03A',
            'F11': '\uE03B',
            'F12': '\uE03C',

            # Whitespace
            'Space': ' ',
        }

        if key in special_keys:
            return special_keys[key]

        # For regular characters, return as-is
        return key

    # ========================================================================
    # Mouse Event Methods
    # ========================================================================

    def get_element_coordinates_by_xpath(self, xpath: str) -> Optional[Dict[str, float]]:
        """
        Get the center coordinates of an element using XPath.

        Args:
            xpath: XPath expression that identifies the element

        Returns:
            Dictionary with 'x' and 'y' keys for the element's center coordinates,
            or None if element not found
        """
        try:
            script = """
                function(xpath) {
                    try {
                        let result = document.evaluate(
                            xpath,
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        let element = result.singleNodeValue;
                        if (element) {
                            let rect = element.getBoundingClientRect();
                            return {
                                x: rect.left + rect.width / 2,
                                y: rect.top + rect.height / 2,
                                width: rect.width,
                                height: rect.height,
                                top: rect.top,
                                left: rect.left,
                                bottom: rect.bottom,
                                right: rect.right
                            };
                        }
                        return null;
                    } catch (e) {
                        return null;
                    }
                }
            """

            return self.execute_javascript_function(script, [xpath])

        except Exception as e:
            self.log.warning("Failed to get element coordinates: {}".format(e))
            return None

    def get_element_coordinates(self, selector: str) -> Optional[Dict[str, float]]:
        """
        Get the center coordinates of an element using a CSS selector.

        Args:
            selector: CSS selector that identifies the element

        Returns:
            Dictionary with 'x' and 'y' keys for the element's center coordinates,
            or None if element not found
        """
        try:
            script = """
                function(selector) {
                    try {
                        let element = document.querySelector(selector);
                        if (element) {
                            let rect = element.getBoundingClientRect();
                            return {
                                x: rect.left + rect.width / 2,
                                y: rect.top + rect.height / 2,
                                width: rect.width,
                                height: rect.height,
                                top: rect.top,
                                left: rect.left,
                                bottom: rect.bottom,
                                right: rect.right
                            };
                        }
                        return null;
                    } catch (e) {
                        return null;
                    }
                }
            """

            return self.execute_javascript_function(script, [selector])

        except Exception as e:
            self.log.warning("Failed to get element coordinates: {}".format(e))
            return None

    def move_mouse_to(self, x: float, y: float, duration_ms: int = 0) -> bool:
        """
        Move the mouse to specific coordinates.

        Args:
            x: X coordinate to move to
            y: Y coordinate to move to
            duration_ms: Duration of the movement in milliseconds (0 for instant)

        Returns:
            True if successful, False otherwise
        """
        try:
            actions = [{
                'type': 'pointer',
                'id': 'mouse',
                'parameters': {'pointerType': 'mouse'},
                'actions': [
                    {
                        'type': 'pointerMove',
                        'x': int(x),
                        'y': int(y),
                        'duration': duration_ms,
                        'origin': 'viewport'
                    }
                ]
            }]

            return self.bidi_perform_actions(actions)

        except Exception as e:
            self.log.warning("Failed to move mouse: {}".format(e))
            return False

    def move_mouse_to_element_by_xpath(self, xpath: str, duration_ms: int = 0) -> bool:
        """
        Move the mouse to the center of an element identified by XPath.

        Args:
            xpath: XPath expression that identifies the element
            duration_ms: Duration of the movement in milliseconds (0 for instant)

        Returns:
            True if successful, False otherwise
        """
        try:
            coords = self.get_element_coordinates_by_xpath(xpath)
            if not coords:
                self.log.warning("Could not find element: {}".format(xpath))
                return False

            return self.move_mouse_to(coords['x'], coords['y'], duration_ms)

        except Exception as e:
            self.log.warning("Failed to move mouse to element: {}".format(e))
            return False

    def move_mouse_to_element(self, selector: str, duration_ms: int = 0) -> bool:
        """
        Move the mouse to the center of an element identified by CSS selector.

        Args:
            selector: CSS selector that identifies the element
            duration_ms: Duration of the movement in milliseconds (0 for instant)

        Returns:
            True if successful, False otherwise
        """
        try:
            coords = self.get_element_coordinates(selector)
            if not coords:
                self.log.warning("Could not find element: {}".format(selector))
                return False

            return self.move_mouse_to(coords['x'], coords['y'], duration_ms)

        except Exception as e:
            self.log.warning("Failed to move mouse to element: {}".format(e))
            return False

    def mouse_click(self, x: float, y: float, button: str = "left",
                   click_count: int = 1) -> bool:
        """
        Perform a mouse click at specific coordinates.

        Args:
            x: X coordinate to click at
            y: Y coordinate to click at
            button: Mouse button to use ('left', 'middle', 'right')
            click_count: Number of clicks (1 for single, 2 for double-click)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Map button names to WebDriver button indices
            button_map = {
                'left': 0,
                'middle': 1,
                'right': 2
            }
            button_idx = button_map.get(button, 0)

            # Build click action sequence
            click_actions = [
                {
                    'type': 'pointerMove',
                    'x': int(x),
                    'y': int(y),
                    'duration': 0,
                    'origin': 'viewport'
                }
            ]

            # Add click(s)
            for _ in range(click_count):
                click_actions.append({
                    'type': 'pointerDown',
                    'button': button_idx
                })
                click_actions.append({
                    'type': 'pointerUp',
                    'button': button_idx
                })

            actions = [{
                'type': 'pointer',
                'id': 'mouse',
                'parameters': {'pointerType': 'mouse'},
                'actions': click_actions
            }]

            return self.bidi_perform_actions(actions)

        except Exception as e:
            self.log.warning("Failed to perform mouse click: {}".format(e))
            return False

    def mouse_click_element_by_xpath(self, xpath: str, button: str = "left",
                                     click_count: int = 1) -> bool:
        """
        Click on an element identified by XPath using mouse events.

        This performs a realistic mouse click by moving to the element's
        center coordinates and clicking, rather than using JavaScript click().

        Args:
            xpath: XPath expression that identifies the element
            button: Mouse button to use ('left', 'middle', 'right')
            click_count: Number of clicks (1 for single, 2 for double-click)

        Returns:
            True if successful, False otherwise
        """
        try:
            coords = self.get_element_coordinates_by_xpath(xpath)
            if not coords:
                self.log.warning("Could not find element: {}".format(xpath))
                return False

            return self.mouse_click(coords['x'], coords['y'], button, click_count)

        except Exception as e:
            self.log.warning("Failed to click element by xpath: {}".format(e))
            return False

    def mouse_click_element(self, selector: str, button: str = "left",
                           click_count: int = 1) -> bool:
        """
        Click on an element identified by CSS selector using mouse events.

        This performs a realistic mouse click by moving to the element's
        center coordinates and clicking, rather than using JavaScript click().

        Args:
            selector: CSS selector that identifies the element
            button: Mouse button to use ('left', 'middle', 'right')
            click_count: Number of clicks (1 for single, 2 for double-click)

        Returns:
            True if successful, False otherwise
        """
        try:
            coords = self.get_element_coordinates(selector)
            if not coords:
                self.log.warning("Could not find element: {}".format(selector))
                return False

            return self.mouse_click(coords['x'], coords['y'], button, click_count)

        except Exception as e:
            self.log.warning("Failed to click element: {}".format(e))
            return False

    def mouse_double_click(self, x: float, y: float, button: str = "left") -> bool:
        """
        Perform a double-click at specific coordinates.

        Args:
            x: X coordinate to click at
            y: Y coordinate to click at
            button: Mouse button to use ('left', 'middle', 'right')

        Returns:
            True if successful, False otherwise
        """
        return self.mouse_click(x, y, button, click_count=2)

    def mouse_double_click_element_by_xpath(self, xpath: str,
                                            button: str = "left") -> bool:
        """
        Double-click on an element identified by XPath.

        Args:
            xpath: XPath expression that identifies the element
            button: Mouse button to use ('left', 'middle', 'right')

        Returns:
            True if successful, False otherwise
        """
        return self.mouse_click_element_by_xpath(xpath, button, click_count=2)

    def mouse_right_click_element_by_xpath(self, xpath: str) -> bool:
        """
        Right-click (context menu) on an element identified by XPath.

        Args:
            xpath: XPath expression that identifies the element

        Returns:
            True if successful, False otherwise
        """
        return self.mouse_click_element_by_xpath(xpath, button="right", click_count=1)

    def mouse_drag(self, start_x: float, start_y: float,
                   end_x: float, end_y: float, duration_ms: int = 100) -> bool:
        """
        Perform a mouse drag from one point to another.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration_ms: Duration of the drag movement in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            actions = [{
                'type': 'pointer',
                'id': 'mouse',
                'parameters': {'pointerType': 'mouse'},
                'actions': [
                    {
                        'type': 'pointerMove',
                        'x': int(start_x),
                        'y': int(start_y),
                        'duration': 0,
                        'origin': 'viewport'
                    },
                    {
                        'type': 'pointerDown',
                        'button': 0
                    },
                    {
                        'type': 'pointerMove',
                        'x': int(end_x),
                        'y': int(end_y),
                        'duration': duration_ms,
                        'origin': 'viewport'
                    },
                    {
                        'type': 'pointerUp',
                        'button': 0
                    }
                ]
            }]

            return self.bidi_perform_actions(actions)

        except Exception as e:
            self.log.warning("Failed to perform mouse drag: {}".format(e))
            return False

    def mouse_drag_element_by_xpath(self, source_xpath: str, target_xpath: str,
                                    duration_ms: int = 100) -> bool:
        """
        Drag an element to another element, both identified by XPath.

        Args:
            source_xpath: XPath of the element to drag
            target_xpath: XPath of the element to drag to
            duration_ms: Duration of the drag movement in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            source_coords = self.get_element_coordinates_by_xpath(source_xpath)
            target_coords = self.get_element_coordinates_by_xpath(target_xpath)

            if not source_coords:
                self.log.warning("Could not find source element: {}".format(source_xpath))
                return False
            if not target_coords:
                self.log.warning("Could not find target element: {}".format(target_xpath))
                return False

            return self.mouse_drag(
                source_coords['x'], source_coords['y'],
                target_coords['x'], target_coords['y'],
                duration_ms
            )

        except Exception as e:
            self.log.warning("Failed to drag element: {}".format(e))
            return False

    def hover_element_by_xpath(self, xpath: str, duration_ms: int = 0) -> bool:
        """
        Hover over an element identified by XPath.

        This is an alias for move_mouse_to_element_by_xpath.

        Args:
            xpath: XPath expression that identifies the element
            duration_ms: Duration of the movement in milliseconds

        Returns:
            True if successful, False otherwise
        """
        return self.move_mouse_to_element_by_xpath(xpath, duration_ms)