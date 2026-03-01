#!/usr/bin/env python3

"""
Tests for Firefox profile lock (parent.lock) cleanup.

Firefox creates a 'parent.lock' file in the profile directory while running.
On Windows, if Firefox is killed forcefully (TerminateProcess), this lock file
is not cleaned up, preventing subsequent Firefox instances from using the
same profile. These tests verify that FirefoxController properly cleans up
the lock file when close() is called.
"""

import os
import tempfile
import shutil

import pytest
from unittest.mock import Mock, patch, MagicMock

from FirefoxController.execution_manager import FirefoxExecutionManager


@pytest.fixture
def profile_dir():
    """Create a temporary profile directory for testing."""
    tmpdir = tempfile.mkdtemp(prefix="firefox_test_profile_")
    yield tmpdir
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)


@pytest.fixture
def manager_with_mock_process(profile_dir):
    """Create a FirefoxExecutionManager with mocked internals so no real Firefox starts."""
    mgr = FirefoxExecutionManager.__new__(FirefoxExecutionManager)
    mgr.profile_dir = profile_dir
    mgr.temp_profile = None
    mgr.ws_connection = None
    mgr.process = None
    mgr.tabs = {}
    mgr.tab_id_map = {}
    mgr.browsing_context = None
    mgr.user_context = None
    mgr.log = MagicMock()
    return mgr


class TestProfileLockCleanup:
    """Tests for parent.lock cleanup in close()."""

    def test_close_removes_parent_lock(self, manager_with_mock_process, profile_dir):
        """close() should remove parent.lock from the profile directory."""
        lock_file = os.path.join(profile_dir, "parent.lock")
        # Simulate Firefox leaving a lock file
        with open(lock_file, "w") as f:
            f.write("")
        assert os.path.exists(lock_file)

        manager_with_mock_process.close()

        assert not os.path.exists(lock_file), "parent.lock should be removed after close()"

    def test_close_works_when_no_lock_exists(self, manager_with_mock_process, profile_dir):
        """close() should not fail when no parent.lock exists."""
        lock_file = os.path.join(profile_dir, "parent.lock")
        assert not os.path.exists(lock_file)

        # Should not raise
        manager_with_mock_process.close()

    def test_close_removes_lock_after_process_termination(self, manager_with_mock_process, profile_dir):
        """close() should remove the lock even when a process was running."""
        lock_file = os.path.join(profile_dir, "parent.lock")
        with open(lock_file, "w") as f:
            f.write("")

        # Simulate a running Firefox process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_process.wait.return_value = 0  # terminate succeeds
        manager_with_mock_process.process = mock_process

        manager_with_mock_process.close()

        assert not os.path.exists(lock_file), "parent.lock should be removed after process termination"

    def test_close_removes_lock_when_profile_dir_is_none(self, manager_with_mock_process):
        """close() should handle profile_dir=None gracefully."""
        manager_with_mock_process.profile_dir = None
        # Should not raise
        manager_with_mock_process.close()

    def test_context_manager_exit_removes_lock(self, manager_with_mock_process, profile_dir):
        """__exit__ calls close(), which should remove parent.lock."""
        lock_file = os.path.join(profile_dir, "parent.lock")
        with open(lock_file, "w") as f:
            f.write("")

        manager_with_mock_process.__exit__(None, None, None)

        assert not os.path.exists(lock_file), "parent.lock should be removed on context manager exit"

    def test_del_removes_lock_as_safety_net(self, profile_dir):
        """__del__ should remove parent.lock as a safety net."""
        lock_file = os.path.join(profile_dir, "parent.lock")
        with open(lock_file, "w") as f:
            f.write("")

        mgr = FirefoxExecutionManager.__new__(FirefoxExecutionManager)
        mgr.profile_dir = profile_dir
        mgr.__del__()

        assert not os.path.exists(lock_file), "parent.lock should be removed by __del__"

    def test_del_handles_missing_profile_dir_attr(self):
        """__del__ should not fail if profile_dir attribute doesn't exist."""
        mgr = object.__new__(FirefoxExecutionManager)
        # Don't set profile_dir at all
        # Should not raise
        mgr.__del__()

    def test_lock_removal_is_logged(self, manager_with_mock_process, profile_dir):
        """Removing the lock file should produce a debug log message."""
        lock_file = os.path.join(profile_dir, "parent.lock")
        with open(lock_file, "w") as f:
            f.write("")

        manager_with_mock_process.close()

        manager_with_mock_process.log.debug.assert_any_call(
            "Removed stale profile lock: {}".format(lock_file)
        )
