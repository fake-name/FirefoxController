#!/usr/bin/env python3

"""
WebDriver-BiDi Type Validation and Utilities

This module provides type validation and utility functions for WebDriver-BiDi protocol
implementation based on the W3C specification: https://www.w3.org/TR/webdriver-bidi/
"""

import json
import re
from typing import Any, Dict, List, Optional, Union, Type, Tuple
from enum import Enum
from datetime import datetime
import base64


class BiDiTypeError(TypeError):
    """Custom exception for WebDriver-BiDi type validation errors"""
    pass


class BiDiValidationError(ValueError):
    """Custom exception for WebDriver-BiDi validation errors"""
    pass


class BrowsingContextType(Enum):
    """Browsing context types as defined in WebDriver-BiDi spec"""
    TAB = "tab"
    WINDOW = "window"


class NavigationType(Enum):
    """Navigation wait types as defined in WebDriver-BiDi spec"""
    COMPLETE = "complete"
    INTERACTIVE = "interactive"
    DOMCONTENTLOADED = "domcontentloaded"


class ScriptResultType(Enum):
    """Script evaluation result types as defined in WebDriver-BiDi spec"""
    UNDEFINED = "undefined"
    NULL = "null"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    BIGINT = "bigint"
    OBJECT = "object"
    FUNCTION = "function"
    SYMBOL = "symbol"
    ARRAY = "array"
    DATE = "date"
    REGEXP = "regexp"
    MAP = "map"
    SET = "set"
    WEAKMAP = "weakmap"
    WEAKSET = "weakset"
    ERROR = "error"
    PROXY = "proxy"
    PROMISE = "promise"
    TYPEDARRAY = "typedarray"
    ARRAYBUFFER = "arraybuffer"


class NetworkPhase(Enum):
    """Network intercept phases as defined in WebDriver-BiDi spec"""
    BEFORE_REQUEST_SENT = "beforeRequestSent"
    RESPONSE_STARTED = "responseStarted"
    RESPONSE_COMPLETED = "responseCompleted"
    AUTH_REQUIRED = "authRequired"


class CookieSameSite(Enum):
    """Cookie SameSite values as defined in WebDriver-BiDi spec"""
    STRICT = "strict"
    LAX = "lax"
    NONE = "none"


class LogLevel(Enum):
    """Console log levels as defined in WebDriver-BiDi spec section 7.8"""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class LogSource(Enum):
    """Console log sources as defined in WebDriver-BiDi spec section 7.8"""
    CONSOLE = "console"
    JAVASCRIPT = "javascript"


def validate_browsing_context_type(context_type: str) -> str:
    """
    Validate browsing context type.
    
    Args:
        context_type: The browsing context type to validate
        
    Returns:
        Validated context type
        
    Raises:
        BiDiTypeError: If the context type is invalid
    """
    try:
        return BrowsingContextType(context_type).value
    except ValueError:
        valid_types = [t.value for t in BrowsingContextType]
        raise BiDiTypeError("Invalid browsing context type '{}'. Valid types: {}".format(context_type, valid_types))


def validate_navigation_type(navigation_type: str) -> str:
    """
    Validate navigation wait type.
    
    Args:
        navigation_type: The navigation type to validate
        
    Returns:
        Validated navigation type
        
    Raises:
        BiDiTypeError: If the navigation type is invalid
    """
    try:
        return NavigationType(navigation_type).value
    except ValueError:
        valid_types = [t.value for t in NavigationType]
        raise BiDiTypeError("Invalid navigation type '{}'. Valid types: {}".format(navigation_type, valid_types))


def validate_network_phases(phases: List[str]) -> List[str]:
    """
    Validate network intercept phases.
    
    Args:
        phases: List of network phases to validate
        
    Returns:
        List of validated phases
        
    Raises:
        BiDiTypeError: If any phase is invalid
    """
    valid_phases = []
    for phase in phases:
        try:
            valid_phases.append(NetworkPhase(phase).value)
        except ValueError:
            valid_phase_values = [p.value for p in NetworkPhase]
            raise BiDiTypeError("Invalid network phase '{}'. Valid phases: {}".format(phase, valid_phase_values))
    return valid_phases


def validate_cookie_same_site(same_site: str) -> str:
    """
    Validate cookie SameSite value.
    
    Args:
        same_site: The SameSite value to validate
        
    Returns:
        Validated SameSite value
        
    Raises:
        BiDiTypeError: If the SameSite value is invalid
    """
    try:
        return CookieSameSite(same_site).value
    except ValueError:
        valid_values = [s.value for s in CookieSameSite]
        raise BiDiTypeError("Invalid SameSite value '{}'. Valid values: {}".format(same_site, valid_values))


def validate_url(url: str) -> str:
    """
    Validate a URL string.
    
    Args:
        url: The URL to validate
        
    Returns:
        Validated URL
        
    Raises:
        BiDiValidationError: If the URL is invalid
    """
    if not url or not isinstance(url, str):
        raise BiDiValidationError("URL must be a non-empty string")
    
    # Basic URL validation - should start with http://, https://, or about:
    if not (url.startswith('http://') or url.startswith('https://') or url.startswith('about:') or url.startswith('data:')):
        raise BiDiValidationError("Invalid URL format: {}".format(url))
    
    return url


def validate_cookie(cookie: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a cookie dictionary according to WebDriver-BiDi specification.
    
    Args:
        cookie: The cookie dictionary to validate
        
    Returns:
        Validated cookie dictionary
        
    Raises:
        BiDiValidationError: If the cookie is invalid
    """
    if not isinstance(cookie, dict):
        raise BiDiValidationError("Cookie must be a dictionary")
    
    required_fields = ['name', 'value']
    for field in required_fields:
        if field not in cookie:
            raise BiDiValidationError("Cookie missing required field: {}".format(field))
        if not isinstance(cookie[field], str):
            raise BiDiValidationError("Cookie field '{}' must be a string".format(field))
    
    optional_fields = {
        'domain': str,
        'path': str,
        'secure': bool,
        'httpOnly': bool,
        'sameSite': str,
        'expiry': int
    }
    
    for field, expected_type in optional_fields.items():
        if field in cookie:
            if field == 'sameSite':
                validate_cookie_same_site(cookie[field])
            elif not isinstance(cookie[field], expected_type):
                raise BiDiValidationError("Cookie field '{}' must be {}".format(field, expected_type.__name__))
    
    return cookie


def validate_screenshot_format(format: str) -> str:
    """
    Validate screenshot format.
    
    Args:
        format: The screenshot format to validate
        
    Returns:
        Validated format
        
    Raises:
        BiDiTypeError: If the format is invalid
    """
    valid_formats = ['png', 'jpeg', 'webp']
    if format.lower() not in valid_formats:
        raise BiDiTypeError("Invalid screenshot format '{}'. Valid formats: {}".format(format, valid_formats))
    return format.lower()


def validate_clip_region(clip: Dict[str, int]) -> Dict[str, int]:
    """
    Validate screenshot clip region.
    
    Args:
        clip: The clip region dictionary to validate
        
    Returns:
        Validated clip region
        
    Raises:
        BiDiValidationError: If the clip region is invalid
    """
    if not isinstance(clip, dict):
        raise BiDiValidationError("Clip region must be a dictionary")
    
    required_fields = ['x', 'y', 'width', 'height']
    for field in required_fields:
        if field not in clip:
            raise BiDiValidationError("Clip region missing required field: {}".format(field))
        if not isinstance(clip[field], int) or clip[field] < 0:
            raise BiDiValidationError("Clip region field '{}' must be a non-negative integer".format(field))
    
    return clip


def validate_script_result_type(result_type: str) -> str:
    """
    Validate script result type.
    
    Args:
        result_type: The script result type to validate
        
    Returns:
        Validated result type
        
    Raises:
        BiDiTypeError: If the result type is invalid
    """
    try:
        return ScriptResultType(result_type).value
    except ValueError:
        valid_types = [t.value for t in ScriptResultType]
        raise BiDiTypeError("Invalid script result type '{}'. Valid types: {}".format(result_type, valid_types))


def parse_script_result(response: Dict[str, Any]) -> Any:
    """
    Parse and validate script evaluation result from WebDriver-BiDi response.
    
    Args:
        response: WebDriver-BiDi response dictionary
        
    Returns:
        Parsed result
        
    Raises:
        BiDiValidationError: If the response is invalid
    """
    # Validate response structure
    if not isinstance(response, dict):
        raise BiDiValidationError("Response must be a dictionary")
    
    # Check for exception
    if response.get('type') == 'exception':
        return None
    
    if response.get('type') != 'success':
        raise BiDiValidationError("Invalid response type: {}".format(response.get('type')))
    
    if 'result' not in response:
        raise BiDiValidationError("Response missing 'result' field")
    
    result_obj = response['result']
    
    # Handle nested structure for real WebDriver-BiDi responses
    if isinstance(result_obj, dict) and 'result' in result_obj:
        result_obj = result_obj['result']
    
    # Handle special types
    if isinstance(result_obj, dict):
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


def validate_browsing_context_id(context_id: str) -> str:
    """
    Validate browsing context ID.
    
    Args:
        context_id: The browsing context ID to validate
        
    Returns:
        Validated context ID
        
    Raises:
        BiDiValidationError: If the context ID is invalid
    """
    if not context_id or not isinstance(context_id, str):
        raise BiDiValidationError("Browsing context ID must be a non-empty string")
    
    # Basic UUID validation - should be a reasonable format
    if len(context_id) < 10 or len(context_id) > 100:
        raise BiDiValidationError("Invalid browsing context ID format: {}".format(context_id))
    
    return context_id


def validate_intercept_id(intercept_id: str) -> str:
    """
    Validate network intercept ID.
    
    Args:
        intercept_id: The intercept ID to validate
        
    Returns:
        Validated intercept ID
        
    Raises:
        BiDiValidationError: If the intercept ID is invalid
    """
    if not intercept_id or not isinstance(intercept_id, str):
        raise BiDiValidationError("Intercept ID must be a non-empty string")
    
    return intercept_id


def validate_base64_data(data: str) -> bytes:
    """
    Validate and decode base64 data.
    
    Args:
        data: Base64 encoded string
        
    Returns:
        Decoded bytes
        
    Raises:
        BiDiValidationError: If the data is not valid base64
    """
    try:
        return base64.b64decode(data)
    except (TypeError, ValueError) as e:
        raise BiDiValidationError("Invalid base64 data: {}".format(e))


def validate_json_data(data: Any) -> Any:
    """
    Validate JSON-serializable data.
    
    Args:
        data: Data to validate
        
    Returns:
        Validated data
        
    Raises:
        BiDiValidationError: If the data is not JSON-serializable
    """
    try:
        json.dumps(data)
        return data
    except (TypeError, ValueError) as e:
        raise BiDiValidationError("Data is not JSON-serializable: {}".format(e))


class BiDiTypeValidator:
    """
    WebDriver-BiDi type validator utility class.
    """
    
    @staticmethod
    def validate_method_parameters(method_name: str, params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate method parameters against a schema.
        
        Args:
            method_name: Name of the WebDriver-BiDi method
            params: Parameters to validate
            schema: Validation schema
            
        Returns:
            Validated parameters
            
        Raises:
            BiDiValidationError: If validation fails
        """
        if not isinstance(params, dict):
            raise BiDiValidationError("{} parameters must be a dictionary".format(method_name))
        
        validated_params = {}
        
        for param_name, param_schema in schema.items():
            if param_name not in params:
                if param_schema.get('required', False):
                    raise BiDiValidationError("Missing required parameter '{}' for method {}".format(param_name, method_name))
                else:
                    continue
            
            param_value = params[param_name]
            param_type = param_schema.get('type')
            
            # Validate type
            if param_type:
                if param_type == 'string':
                    if not isinstance(param_value, str):
                        raise BiDiValidationError("Parameter '{}' must be a string".format(param_name))
                elif param_type == 'number':
                    if not isinstance(param_value, (int, float)):
                        raise BiDiValidationError("Parameter '{}' must be a number".format(param_name))
                elif param_type == 'integer':
                    if not isinstance(param_value, int):
                        raise BiDiValidationError("Parameter '{}' must be an integer".format(param_name))
                elif param_type == 'boolean':
                    if not isinstance(param_value, bool):
                        raise BiDiValidationError("Parameter '{}' must be a boolean".format(param_name))
                elif param_type == 'array':
                    if not isinstance(param_value, list):
                        raise BiDiValidationError("Parameter '{}' must be an array".format(param_name))
                elif param_type == 'object':
                    if not isinstance(param_value, dict):
                        raise BiDiValidationError("Parameter '{}' must be an object".format(param_name))
                elif param_type == 'enum':
                    valid_values = param_schema.get('values', [])
                    if param_value not in valid_values:
                        raise BiDiValidationError("Parameter '{}' must be one of: {}".format(param_name, valid_values))
            
            # Validate custom validators
            if 'validator' in param_schema:
                validator = param_schema['validator']
                if callable(validator):
                    param_value = validator(param_value)
            
            validated_params[param_name] = param_value
        
        return validated_params

    @staticmethod
    def validate_response(method_name: str, response: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate WebDriver-BiDi response against a schema.
        
        Args:
            method_name: Name of the WebDriver-BiDi method
            response: Response to validate
            schema: Validation schema
            
        Returns:
            Validated response
            
        Raises:
            BiDiValidationError: If validation fails
        """
        if not isinstance(response, dict):
            raise BiDiValidationError("{} response must be a dictionary".format(method_name))
        
        # Check response type
        if 'type' not in response:
            raise BiDiValidationError("{} response missing 'type' field".format(method_name))
        
        if response['type'] not in ['success', 'error', 'exception']:
            raise BiDiValidationError("Invalid response type: {}".format(response['type']))
        
        # Validate success response
        if response['type'] == 'success':
            if 'result' not in response:
                raise BiDiValidationError("{} success response missing 'result' field".format(method_name))
            
            # Validate result structure
            result_schema = schema.get('result', {})
            if result_schema:
                BiDiTypeValidator.validate_method_parameters(method_name, response['result'], result_schema)
        
        # Validate error response
        elif response['type'] == 'error':
            if 'error' not in response:
                raise BiDiValidationError("{} error response missing 'error' field".format(method_name))
        
        return response


# WebDriver-BiDi Method Schemas based on W3C specification
METHOD_SCHEMAS = {
    'browsingContext.create': {
        'parameters': {
            'type': {'type': 'string', 'validator': validate_browsing_context_type, 'required': True}
        },
        'response': {
            'result': {
                'context': {'type': 'string', 'validator': validate_browsing_context_id}
            }
        }
    },
    'browsingContext.navigate': {
        'parameters': {
            'context': {'type': 'string', 'validator': validate_browsing_context_id, 'required': True},
            'url': {'type': 'string', 'validator': validate_url, 'required': True},
            'wait': {'type': 'string', 'validator': validate_navigation_type}
        },
        'response': {
            'result': {
                'navigation': {'type': 'string'},
                'url': {'type': 'string'}
            }
        }
    },
    'script.evaluate': {
        'parameters': {
            'expression': {'type': 'string', 'required': True},
            'target': {'type': 'object', 'required': True},
            'awaitPromise': {'type': 'boolean'}
        }
    },
    'browsingContext.captureScreenshot': {
        'parameters': {
            'context': {'type': 'string', 'validator': validate_browsing_context_id, 'required': True},
            'format': {'type': 'object', 'required': True},
            'clip': {'type': 'object', 'validator': validate_clip_region}
        },
        'response': {
            'result': {
                'data': {'type': 'string'}
            }
        }
    }
}


def get_method_schema(method_name: str) -> Optional[Dict[str, Any]]:
    """
    Get validation schema for a WebDriver-BiDi method.

    Args:
        method_name: Name of the method

    Returns:
        Validation schema or None if not found
    """
    return METHOD_SCHEMAS.get(method_name)


def validate_log_level(level: str) -> str:
    """
    Validate console log level.

    Args:
        level: The log level to validate

    Returns:
        Validated log level

    Raises:
        BiDiTypeError: If the log level is invalid
    """
    try:
        return LogLevel(level).value
    except ValueError:
        valid_levels = [l.value for l in LogLevel]
        raise BiDiTypeError("Invalid log level '{}'. Valid levels: {}".format(level, valid_levels))


def validate_log_source(source: str) -> str:
    """
    Validate console log source.

    Args:
        source: The log source to validate

    Returns:
        Validated log source

    Raises:
        BiDiTypeError: If the log source is invalid
    """
    try:
        return LogSource(source).value
    except ValueError:
        valid_sources = [s.value for s in LogSource]
        raise BiDiTypeError("Invalid log source '{}'. Valid sources: {}".format(source, valid_sources))


class ConsoleLogEntry:
    """
    Represents a console log entry from WebDriver-BiDi log.entryAdded events.

    Based on the W3C WebDriver-BiDi specification section 7.8.2.1 (log.LogEntry).

    Attributes:
        level: Log level (debug, info, warn, error)
        source: Log source (console, javascript)
        text: The log message text
        timestamp: Unix timestamp in milliseconds
        context_id: Browsing context ID where the log originated
        stack_trace: Optional stack trace information
        args: Optional list of arguments passed to the console method
        method: The console method called (log, warn, error, etc.)
    """

    def __init__(self,
                 level: str,
                 source: str,
                 text: str,
                 timestamp: int,
                 context_id: str = None,
                 stack_trace: Optional[Dict[str, Any]] = None,
                 args: Optional[List[Any]] = None,
                 method: str = None):
        """
        Initialize a ConsoleLogEntry.

        Args:
            level: Log level (debug, info, warn, error)
            source: Log source (console, javascript)
            text: The log message text
            timestamp: Unix timestamp in milliseconds
            context_id: Browsing context ID where the log originated
            stack_trace: Optional stack trace information
            args: Optional list of arguments passed to the console method
            method: The console method called (log, warn, error, etc.)
        """
        self.level = level
        self.source = source
        self.text = text
        self.timestamp = timestamp
        self.context_id = context_id
        self.stack_trace = stack_trace
        self.args = args or []
        self.method = method

    @classmethod
    def from_bidi_event(cls, event: Dict[str, Any]) -> 'ConsoleLogEntry':
        """
        Create a ConsoleLogEntry from a WebDriver-BiDi log.entryAdded event.

        Args:
            event: The log.entryAdded event dictionary

        Returns:
            ConsoleLogEntry instance
        """
        params = event.get('params', {})

        # Extract required fields
        level = params.get('level', 'info')
        source = params.get('source', {}).get('type', 'console') if isinstance(params.get('source'), dict) else params.get('source', 'console')
        text = params.get('text', '')
        timestamp = params.get('timestamp', 0)

        # Extract optional fields
        context_id = params.get('source', {}).get('context') if isinstance(params.get('source'), dict) else None
        stack_trace = params.get('stackTrace')
        args = params.get('args', [])
        method = params.get('method')

        return cls(
            level=level,
            source=source,
            text=text,
            timestamp=timestamp,
            context_id=context_id,
            stack_trace=stack_trace,
            args=args,
            method=method
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ConsoleLogEntry to a dictionary.

        Returns:
            Dictionary representation of the log entry
        """
        result = {
            'level': self.level,
            'source': self.source,
            'text': self.text,
            'timestamp': self.timestamp
        }

        if self.context_id:
            result['context_id'] = self.context_id
        if self.stack_trace:
            result['stack_trace'] = self.stack_trace
        if self.args:
            result['args'] = self.args
        if self.method:
            result['method'] = self.method

        return result

    def __repr__(self) -> str:
        """String representation of the log entry."""
        return "ConsoleLogEntry(level='{}', source='{}', text='{}', timestamp={})".format(
            self.level, self.source, self.text[:50] + '...' if len(self.text) > 50 else self.text, self.timestamp
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return "[{}] [{}] {}".format(self.level.upper(), self.source, self.text)