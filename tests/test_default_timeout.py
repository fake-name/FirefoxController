#!/usr/bin/env python3
"""
Test script for default timeout functionality
"""

import pytest
from FirefoxController import FirefoxRemoteDebugInterface


@pytest.fixture(scope="module")
def firefox():
    """Shared Firefox instance for all timeout tests."""
    with FirefoxRemoteDebugInterface(headless=True) as ff:
        yield ff


class TestDefaultTimeout:

    def test_default_timeout_initialization(self, firefox):
        """Default timeout should be 30 seconds."""
        assert firefox.default_timeout == 30, "Default should be 30 seconds"

    def test_change_default_timeout(self, firefox):
        """set_default_timeout should update the default."""
        original = firefox.default_timeout
        firefox.set_default_timeout(60)
        assert firefox.default_timeout == 60, "Default should be 60 seconds after change"
        # Restore
        firefox.set_default_timeout(original)

    def test_navigation_uses_default_timeout(self, firefox):
        """Navigation should work with the default timeout."""
        firefox.set_default_timeout(15)
        result = firefox.blocking_navigate("https://example.com")
        assert result is not None
        # Restore
        firefox.set_default_timeout(30)

    def test_explicit_timeout_overrides_default(self, firefox):
        """Explicit timeout parameter should override the default."""
        firefox.set_default_timeout(5)
        result = firefox.blocking_navigate("https://example.com", timeout=30)
        assert result is not None
        # Restore
        firefox.set_default_timeout(30)

    def test_get_page_source_uses_default_timeout(self, firefox):
        """get_page_source should work with the default timeout."""
        firefox.set_default_timeout(20)
        firefox.blocking_navigate("https://example.com")
        source = firefox.get_page_source()
        assert len(source) > 0
        # Restore
        firefox.set_default_timeout(30)
