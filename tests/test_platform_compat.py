#!/usr/bin/env python3

"""
Tests for cross-platform (Windows/Linux) compatibility changes.

These tests verify platform-specific code paths without requiring
a running Firefox instance (uses mocking where needed).
"""

import pytest
import sys
import os
import subprocess
import signal
from unittest import mock

from FirefoxController.execution_manager import (
    FirefoxExecutionManager, IS_WINDOWS, IS_LINUX
)
from FirefoxController.exceptions import (
    FirefoxStartupException,
    FirefoxConnectFailure,
)
from FirefoxController.webdriver_patch import (
    find_firefox_libxul,
    _get_xul_library_name,
    WebDriverPatchError,
)


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

class TestPlatformDetection:
    """Test that platform constants are set correctly."""

    def test_platform_constants_are_exclusive(self):
        """IS_WINDOWS and IS_LINUX should not both be True."""
        assert not (IS_WINDOWS and IS_LINUX)

    def test_platform_constant_matches_sys_platform(self):
        """Platform constants should match sys.platform."""
        if sys.platform == 'win32':
            assert IS_WINDOWS is True
            assert IS_LINUX is False
        elif sys.platform.startswith('linux'):
            assert IS_LINUX is True
            assert IS_WINDOWS is False

    def test_current_platform_is_supported(self):
        """Current platform should be one of the supported ones."""
        assert IS_WINDOWS or IS_LINUX, \
            "Current platform {} is not supported".format(sys.platform)


# ---------------------------------------------------------------------------
# Firefox binary detection
# ---------------------------------------------------------------------------

class TestFindFirefoxBinary:
    """Test _find_firefox_binary() platform-specific search."""

    def test_find_binary_in_path(self):
        """Should find Firefox when it's in PATH."""
        mgr = FirefoxExecutionManager()
        # On a machine with Firefox installed, this should succeed
        path = mgr._find_firefox_binary()
        assert path is not None
        assert os.path.isfile(path)

    def test_find_binary_raises_for_missing(self):
        """Should raise FirefoxStartupException for a nonexistent binary."""
        mgr = FirefoxExecutionManager(binary="nonexistent_browser_xyz")
        # Mock os.path.isfile to prevent Windows fallback paths from matching
        with mock.patch('os.path.isfile', return_value=False):
            with pytest.raises(FirefoxStartupException, match="not found"):
                mgr._find_firefox_binary()

    def test_find_binary_uses_custom_path(self):
        """Should use a directly-specified path if it exists."""
        mgr = FirefoxExecutionManager()
        real_path = mgr._find_firefox_binary()
        # Now create a manager with the full path as the binary
        mgr2 = FirefoxExecutionManager(binary=real_path)
        assert mgr2._find_firefox_binary() == real_path

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_find_binary_windows_program_files(self):
        """On Windows, should find Firefox in Program Files."""
        mgr = FirefoxExecutionManager(binary="firefox")
        path = mgr._find_firefox_binary()
        assert path.endswith("firefox.exe")

    @pytest.mark.skipif(not IS_LINUX, reason="Linux-only test")
    def test_find_binary_linux(self):
        """On Linux, should find firefox via PATH."""
        mgr = FirefoxExecutionManager(binary="firefox")
        path = mgr._find_firefox_binary()
        assert "firefox" in path.lower()


# ---------------------------------------------------------------------------
# Firefox version detection
# ---------------------------------------------------------------------------

class TestFirefoxVersionDetection:
    """Test _get_firefox_version() parsing."""

    def test_get_version_real(self):
        """Should detect version of the installed Firefox."""
        mgr = FirefoxExecutionManager()
        path = mgr._find_firefox_binary()
        version = mgr._get_firefox_version(path)
        assert version is not None
        assert isinstance(version, int)
        assert version >= 100  # Firefox has been above 100 for years

    def test_get_version_invalid_binary(self):
        """Should return None for a non-Firefox binary."""
        mgr = FirefoxExecutionManager()
        with mock.patch('subprocess.run') as mock_run:
            # Simulate a non-Firefox binary output
            mock_run.return_value = mock.Mock(stdout="Python 3.12.8")
            version = mgr._get_firefox_version("python")
        assert version is None

    def test_get_version_nonexistent_binary(self):
        """Should return None for a nonexistent binary."""
        mgr = FirefoxExecutionManager()
        version = mgr._get_firefox_version("/nonexistent/path/firefox")
        assert version is None

    def test_version_parsing_standard(self):
        """Should parse standard version string like 'Mozilla Firefox 148.0'."""
        mgr = FirefoxExecutionManager()
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(stdout="Mozilla Firefox 148.0")
            version = mgr._get_firefox_version("firefox")
        assert version == 148

    def test_version_parsing_esr(self):
        """Should parse ESR version string like 'Mozilla Firefox 140.7.1esr'."""
        mgr = FirefoxExecutionManager()
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(stdout="Mozilla Firefox 140.7.1esr")
            version = mgr._get_firefox_version("firefox")
        assert version == 140

    def test_version_parsing_nightly(self):
        """Should parse nightly version string like 'Mozilla Firefox 150.0a1'."""
        mgr = FirefoxExecutionManager()
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(stdout="Mozilla Firefox 150.0a1")
            version = mgr._get_firefox_version("firefox")
        assert version == 150

    def test_version_parsing_garbage(self):
        """Should return None for unparseable output."""
        mgr = FirefoxExecutionManager()
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(stdout="not a version string")
            version = mgr._get_firefox_version("firefox")
        assert version is None


# ---------------------------------------------------------------------------
# Version enforcement
# ---------------------------------------------------------------------------

class TestVersionEnforcement:
    """Test that start_firefox() enforces the minimum version."""

    def test_minimum_version_constant(self):
        """Minimum version should be 143 (network.addDataCollector)."""
        assert FirefoxExecutionManager.MINIMUM_FIREFOX_VERSION == 143

    def test_old_version_raises(self):
        """start_firefox() should raise for Firefox versions below minimum."""
        mgr = FirefoxExecutionManager()
        with mock.patch.object(mgr, '_find_firefox_binary', return_value="firefox"):
            with mock.patch.object(mgr, '_get_firefox_version', return_value=120):
                with pytest.raises(FirefoxStartupException, match="too old"):
                    mgr.start_firefox()

    def test_new_enough_version_proceeds(self):
        """start_firefox() should not raise a version error for version >= minimum."""
        mgr = FirefoxExecutionManager()
        with mock.patch.object(mgr, '_find_firefox_binary', return_value="firefox"):
            with mock.patch.object(mgr, '_get_firefox_version', return_value=148):
                with mock.patch.object(mgr, '_create_profile', return_value="/tmp/profile"):
                    with mock.patch('subprocess.Popen') as mock_popen:
                        mock_proc = mock.Mock()
                        mock_proc.poll.return_value = None
                        mock_popen.return_value = mock_proc
                        with mock.patch('time.sleep'):
                            mgr.start_firefox()
                        # Should have gotten past the version check
                        assert mgr.process is not None

    def test_unknown_version_warns_but_proceeds(self):
        """start_firefox() should warn but proceed if version can't be determined."""
        mgr = FirefoxExecutionManager()
        with mock.patch.object(mgr, '_find_firefox_binary', return_value="firefox"):
            with mock.patch.object(mgr, '_get_firefox_version', return_value=None):
                with mock.patch.object(mgr, '_create_profile', return_value="/tmp/profile"):
                    with mock.patch('subprocess.Popen') as mock_popen:
                        mock_proc = mock.Mock()
                        mock_proc.poll.return_value = None
                        mock_popen.return_value = mock_proc
                        with mock.patch('time.sleep'):
                            mgr.start_firefox()
                        assert mgr.process is not None


# ---------------------------------------------------------------------------
# Process startup platform kwargs
# ---------------------------------------------------------------------------

class TestStartFirefoxPlatformKwargs:
    """Test that start_firefox() uses correct platform-specific Popen args."""

    def _start_with_mocks(self, mgr):
        """Helper: call start_firefox with everything mocked except Popen kwargs."""
        with mock.patch.object(mgr, '_find_firefox_binary', return_value="firefox"):
            with mock.patch.object(mgr, '_get_firefox_version', return_value=148):
                with mock.patch.object(mgr, '_create_profile', return_value="/tmp/profile"):
                    with mock.patch('subprocess.Popen') as mock_popen:
                        mock_proc = mock.Mock()
                        mock_proc.poll.return_value = None
                        mock_popen.return_value = mock_proc
                        with mock.patch('time.sleep'):
                            mgr.start_firefox()
                        return mock_popen

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_windows_uses_creation_flags(self):
        """On Windows, should pass CREATE_NEW_PROCESS_GROUP."""
        mgr = FirefoxExecutionManager()
        mock_popen = self._start_with_mocks(mgr)
        _, kwargs = mock_popen.call_args
        assert 'creationflags' in kwargs
        assert kwargs['creationflags'] == subprocess.CREATE_NEW_PROCESS_GROUP
        assert 'preexec_fn' not in kwargs

    @pytest.mark.skipif(not IS_LINUX, reason="Linux-only test")
    def test_linux_uses_preexec_fn(self):
        """On Linux, should pass preexec_fn."""
        mgr = FirefoxExecutionManager()
        mock_popen = self._start_with_mocks(mgr)
        _, kwargs = mock_popen.call_args
        assert 'preexec_fn' in kwargs
        assert kwargs['preexec_fn'] is not None
        assert 'creationflags' not in kwargs


# ---------------------------------------------------------------------------
# Context manager cleanup on connect failure
# ---------------------------------------------------------------------------

class TestEnterCleanup:
    """Test that __enter__ cleans up Firefox if connect() fails."""

    def test_enter_cleans_up_on_connect_failure(self):
        """If connect() fails, __enter__ should call close() so Firefox doesn't dangle."""
        mgr = FirefoxExecutionManager()
        with mock.patch.object(mgr, 'start_firefox') as mock_start:
            with mock.patch.object(mgr, 'connect', side_effect=FirefoxConnectFailure("test")):
                with mock.patch.object(mgr, 'close') as mock_close:
                    with pytest.raises(FirefoxConnectFailure):
                        mgr.__enter__()
                    mock_start.assert_called_once()
                    mock_close.assert_called_once()

    def test_enter_succeeds_normally(self):
        """Normal __enter__ should not call close()."""
        mgr = FirefoxExecutionManager()
        with mock.patch.object(mgr, 'start_firefox'):
            with mock.patch.object(mgr, 'connect'):
                with mock.patch.object(mgr, 'close') as mock_close:
                    result = mgr.__enter__()
                    assert result is mgr
                    mock_close.assert_not_called()


# ---------------------------------------------------------------------------
# close() platform branching
# ---------------------------------------------------------------------------

class TestClosePlatformBranching:
    """Test that close() uses the correct shutdown method per platform."""

    def _make_mgr_with_process(self):
        """Create a manager with a mock process."""
        mgr = FirefoxExecutionManager()
        mock_proc = mock.Mock()
        mock_proc.poll.return_value = None  # Process is "running"
        mock_proc.pid = 12345
        mock_proc.wait.return_value = 0
        mgr.process = mock_proc
        mgr.ws_connection = None
        return mgr, mock_proc

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_close_windows_uses_terminate(self):
        """On Windows, close() should use process.terminate()."""
        mgr, mock_proc = self._make_mgr_with_process()
        mgr.close()
        mock_proc.terminate.assert_called_once()

    @pytest.mark.skipif(not IS_LINUX, reason="Linux-only test")
    def test_close_linux_uses_sigint(self):
        """On Linux, close() should use os.kill with SIGINT."""
        mgr, mock_proc = self._make_mgr_with_process()
        with mock.patch('os.kill') as mock_kill:
            mgr.close()
            mock_kill.assert_called_once_with(12345, signal.SIGINT)

    def test_close_already_dead_process(self):
        """close() should handle an already-dead process gracefully."""
        mgr, mock_proc = self._make_mgr_with_process()
        mock_proc.poll.return_value = 0  # Already exited
        mgr.close()
        # Should not attempt to terminate/kill
        mock_proc.terminate.assert_not_called()
        mock_proc.kill.assert_not_called()

    def test_close_no_process(self):
        """close() should handle no process at all."""
        mgr = FirefoxExecutionManager()
        mgr.process = None
        mgr.ws_connection = None
        # Should not raise
        mgr.close()


# ---------------------------------------------------------------------------
# connect() retry logic
# ---------------------------------------------------------------------------

class TestConnectRetryLogic:
    """Test that connect() retries on failure."""

    def test_connect_retries_on_failure(self):
        """connect() should retry up to max_retries times."""
        mgr = FirefoxExecutionManager()
        mock_proc = mock.Mock()
        mock_proc.poll.return_value = None
        mgr.process = mock_proc

        call_count = [0]

        def mock_connect(url, **kwargs):
            call_count[0] += 1
            raise ConnectionRefusedError("Connection refused")

        with mock.patch('FirefoxController.execution_manager.connect', mock_connect):
            with mock.patch('time.sleep'):
                with pytest.raises(FirefoxConnectFailure, match="10 attempts"):
                    mgr.connect()

        assert call_count[0] == 10

    def test_connect_succeeds_on_second_attempt(self):
        """connect() should succeed if a retry works."""
        mgr = FirefoxExecutionManager()
        mock_proc = mock.Mock()
        mock_proc.poll.return_value = None
        mgr.process = mock_proc

        call_count = [0]
        mock_ws = mock.Mock()

        def mock_connect_fn(url, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionRefusedError("Connection refused")
            return mock_ws

        with mock.patch('FirefoxController.execution_manager.connect', mock_connect_fn):
            with mock.patch.object(mgr, '_initialize_bidi_connection'):
                with mock.patch('time.sleep'):
                    mgr.connect()

        assert call_count[0] == 2
        assert mgr.ws_connection is mock_ws

    def test_connect_fails_if_process_dies(self):
        """connect() should fail immediately if Firefox process dies."""
        mgr = FirefoxExecutionManager()
        mock_proc = mock.Mock()
        mock_proc.poll.return_value = 1  # Process exited
        mock_proc.stderr = mock.Mock()
        mock_proc.stderr.read.return_value = b"crash"
        mgr.process = mock_proc

        with pytest.raises(FirefoxConnectFailure, match="not running"):
            mgr.connect()


# ---------------------------------------------------------------------------
# webdriver_patch.py platform awareness
# ---------------------------------------------------------------------------

class TestWebDriverPatchPlatform:
    """Test webdriver_patch.py platform-specific XUL library detection."""

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_xul_library_name_windows(self):
        """On Windows, XUL library should be xul.dll."""
        assert _get_xul_library_name() == "xul.dll"

    @pytest.mark.skipif(not IS_LINUX, reason="Linux-only test")
    def test_xul_library_name_linux(self):
        """On Linux, XUL library should be libxul.so."""
        assert _get_xul_library_name() == "libxul.so"

    def test_find_firefox_libxul_returns_existing_file(self):
        """find_firefox_libxul() should return a path that exists (if Firefox installed)."""
        result = find_firefox_libxul()
        if result is not None:
            assert os.path.isfile(result)
            expected_name = _get_xul_library_name()
            assert result.endswith(expected_name)


# ---------------------------------------------------------------------------
# _initialize_bidi_connection fallback strategies
# ---------------------------------------------------------------------------

class TestBidiConnectionFallbacks:
    """Test that _initialize_bidi_connection handles different response formats."""

    def _make_connected_mgr(self):
        """Create a manager with a mock ws_connection."""
        mgr = FirefoxExecutionManager()
        mgr.ws_connection = mock.Mock()
        mgr.ws_lock = mock.MagicMock()
        return mgr

    def test_context_from_success_response(self):
        """Should extract context from a standard success response."""
        mgr = self._make_connected_mgr()

        responses = [
            # session.new response
            {'id': 1, 'type': 'success', 'result': {'sessionId': 'test-session'}},
            # session.subscribe response
            {'id': 2, 'type': 'success', 'result': {}},
            # browsingContext.create response - success format
            {'id': 3, 'type': 'success', 'result': {'context': 'ctx-123'}},
            # browsingContext.getTree response
            {'id': 4, 'type': 'success', 'result': {'contexts': [
                {'context': 'ctx-123', 'url': 'about:blank', 'title': ''}
            ]}},
        ]
        response_iter = iter(responses)

        import json
        def mock_recv(timeout=None):
            return json.dumps(next(response_iter))

        mgr.ws_connection.recv = mock_recv

        mgr._initialize_bidi_connection()
        assert mgr.browsing_context == 'ctx-123'

    def test_context_from_event_response(self):
        """Should extract context from a domContentLoaded event response."""
        mgr = self._make_connected_mgr()

        responses = [
            # session.new response
            {'id': 1, 'type': 'success', 'result': {'sessionId': 'test-session'}},
            # session.subscribe response
            {'id': 2, 'type': 'success', 'result': {}},
            # browsingContext.create - returns event instead of success
            {'id': 3, 'type': 'event', 'method': 'browsingContext.domContentLoaded',
             'params': {'context': 'ctx-456'}},
            # browsingContext.getTree response
            {'id': 4, 'type': 'success', 'result': {'contexts': [
                {'context': 'ctx-456', 'url': 'about:blank', 'title': ''}
            ]}},
        ]
        response_iter = iter(responses)

        import json
        def mock_recv(timeout=None):
            return json.dumps(next(response_iter))

        mgr.ws_connection.recv = mock_recv

        mgr._initialize_bidi_connection()
        assert mgr.browsing_context == 'ctx-456'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
