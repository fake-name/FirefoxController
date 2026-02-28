#!/usr/bin/env python3

"""
Stress test for chunked XHR fetch downloads.

This test aggressively exercises the chunked download path to reproduce
a transient DiscardedBrowsingContextError that occurs when Firefox's
browsing context gets garbage-collected mid-download.

The theory: each chunk in _xhr_fetch_chunked() is a separate bidi_call_function()
call. Between chunks, Firefox can GC the browsing context, causing subsequent
chunk fetches to fail with "BrowsingContext does no longer exist".

We try to reproduce this by:
1. Running many sequential chunked downloads in a single session
2. Varying chunk sizes (smaller = more round trips = more chances to fail)
3. Running downloads while navigating (forces context churn)
4. Running downloads with concurrent JS activity
5. Downloading very large files with tiny chunks (maximum round trips)

Large-file tests use the /download/sized.bin endpoint with seeded random data
(SHA-512 based, deterministic but incompressible).  Every download — small or
large — is verified against the expected byte sequence.  For files too large to
hold in RAM, a chunk_callback verifies each chunk inline then discards it.
"""

import pytest
import FirefoxController
import logging
import sys
import os
import time
import traceback

# Add tests directory to path so we can import test_server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_server import TestServer, _generate_random_bytes


# File sizes served by the stress test server endpoints
LARGE_FILE_SIZE = 5 * 1024 * 1024  # 5MB (existing /download/large.bin endpoint)

MB = 1024 * 1024
GB = 1024 * MB


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def _verify_large_bin_content(data: bytes, expected_size: int):
    """Verify the repeating-byte pattern from /download/large.bin"""
    assert len(data) == expected_size, \
        "Expected {} bytes, got {}".format(expected_size, len(data))
    # Spot-check bytes at several offsets (full check is too slow for stress)
    for offset in [0, 1, 255, 256, 1000, expected_size // 2, expected_size - 1]:
        expected = offset % 256
        actual = data[offset]
        assert actual == expected, \
            "Byte at offset {} should be {} but got {}".format(offset, expected, actual)


def _verify_random_content(data: bytes, expected_size: int, seed: int):
    """Verify seeded random data byte-for-byte against _generate_random_bytes."""
    assert len(data) == expected_size, \
        "Expected {} bytes, got {}".format(expected_size, len(data))
    expected = _generate_random_bytes(seed, 0, expected_size)
    assert data == expected, "Content mismatch (first diff within {} bytes)".format(expected_size)


class _ChunkVerifier:
    """Callable that verifies each chunk against the expected random sequence.

    Pass an instance as chunk_callback to xhr_fetch().  After the download,
    check .errors and .total_bytes.
    """

    def __init__(self, seed):
        self.seed = seed
        self.offset = 0
        self.total_bytes = 0
        self.errors = []

    def __call__(self, data, offset):
        if offset != self.offset:
            self.errors.append("Expected offset {} but got {}".format(self.offset, offset))

        expected = _generate_random_bytes(self.seed, offset, len(data))
        if data != expected:
            # Find first differing byte for a useful error message
            for i in range(len(data)):
                if data[i] != expected[i]:
                    self.errors.append(
                        "Byte mismatch at offset {}: expected 0x{:02x} got 0x{:02x}".format(
                            offset + i, expected[i], data[i]))
                    break

        self.offset = offset + len(data)
        self.total_bytes += len(data)


# ---------------------------------------------------------------------------
# Original stress tests (5MB /download/large.bin)
# ---------------------------------------------------------------------------

def test_stress_repeated_chunked_downloads():
    """
    Download the 5MB file repeatedly with default chunk size.
    Goal: accumulate enough downloads to trigger context GC.
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()

    iterations = 10
    failures = []

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            for i in range(iterations):
                logger.info("=== Iteration {}/{} (256KB chunks) ===".format(i + 1, iterations))
                start = time.time()
                try:
                    result = firefox.xhr_fetch(
                        test_server.get_url("/download/large.bin"),
                        use_chunks=True,
                        chunk_size=256 * 1024
                    )
                    elapsed = time.time() - start
                    logger.info("Download {} completed in {:.2f}s - code={}, chunks={}, size={}".format(
                        i + 1, elapsed, result.get('code'), result.get('chunks'),
                        len(result.get('content', b''))))

                    assert result.get('code') in (200, 206), \
                        "Iter {}: bad status {}".format(i + 1, result.get('code'))
                    _verify_large_bin_content(result['content'], LARGE_FILE_SIZE)

                except Exception as e:
                    elapsed = time.time() - start
                    tb = traceback.format_exc()
                    logger.error("Download {} FAILED after {:.2f}s: {}\n{}".format(
                        i + 1, elapsed, e, tb))
                    failures.append({
                        'iteration': i + 1,
                        'error': str(e),
                        'traceback': tb,
                        'elapsed': elapsed,
                    })

        if failures:
            msg = "{}/{} downloads failed:\n".format(len(failures), iterations)
            for f in failures:
                msg += "  Iter {}: {} ({:.2f}s)\n".format(
                    f['iteration'], f['error'], f['elapsed'])
            pytest.fail(msg)

    finally:
        test_server.stop()


def test_stress_tiny_chunks():
    """
    Download with very small chunks (32KB) to maximize round trips.
    5MB / 32KB = 160 chunks = 160 bidi_call_function calls.
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()

    iterations = 5
    chunk_size = 32 * 1024  # 32KB → ~160 chunks for 5MB
    failures = []

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            for i in range(iterations):
                expected_chunks = LARGE_FILE_SIZE // chunk_size
                logger.info("=== Iteration {}/{} ({}KB chunks, ~{} chunks) ===".format(
                    i + 1, iterations, chunk_size // 1024, expected_chunks))
                start = time.time()
                try:
                    result = firefox.xhr_fetch(
                        test_server.get_url("/download/large.bin"),
                        use_chunks=True,
                        chunk_size=chunk_size
                    )
                    elapsed = time.time() - start
                    logger.info("Download {} completed in {:.2f}s - chunks={}".format(
                        i + 1, elapsed, result.get('chunks')))

                    assert result.get('code') in (200, 206)
                    _verify_large_bin_content(result['content'], LARGE_FILE_SIZE)

                except Exception as e:
                    elapsed = time.time() - start
                    tb = traceback.format_exc()
                    logger.error("Download {} FAILED after {:.2f}s: {}\n{}".format(
                        i + 1, elapsed, e, tb))
                    failures.append({
                        'iteration': i + 1,
                        'error': str(e),
                        'traceback': tb,
                        'elapsed': elapsed,
                        'chunk_size': chunk_size,
                    })

        if failures:
            msg = "{}/{} tiny-chunk downloads failed:\n".format(len(failures), iterations)
            for f in failures:
                msg += "  Iter {}: {} ({:.2f}s)\n".format(
                    f['iteration'], f['error'], f['elapsed'])
            pytest.fail(msg)

    finally:
        test_server.stop()


def test_stress_varying_chunk_sizes():
    """
    Download with progressively smaller chunk sizes to find the threshold
    where failures start occurring.
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()

    # From large to small — more likely to fail with smaller chunks
    chunk_sizes = [
        512 * 1024,  # 512KB → ~10 chunks
        256 * 1024,  # 256KB → ~20 chunks
        128 * 1024,  # 128KB → ~40 chunks
        64 * 1024,   # 64KB  → ~80 chunks
        32 * 1024,   # 32KB  → ~160 chunks
    ]
    failures = []

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            for chunk_size in chunk_sizes:
                expected_chunks = LARGE_FILE_SIZE // chunk_size
                logger.info("=== Testing {}KB chunks (~{} chunks) ===".format(
                    chunk_size // 1024, expected_chunks))
                start = time.time()
                try:
                    result = firefox.xhr_fetch(
                        test_server.get_url("/download/large.bin"),
                        use_chunks=True,
                        chunk_size=chunk_size
                    )
                    elapsed = time.time() - start
                    logger.info("{}KB chunks: OK in {:.2f}s, {} chunks".format(
                        chunk_size // 1024, elapsed, result.get('chunks')))

                    assert result.get('code') in (200, 206)
                    _verify_large_bin_content(result['content'], LARGE_FILE_SIZE)

                except Exception as e:
                    elapsed = time.time() - start
                    tb = traceback.format_exc()
                    logger.error("{}KB chunks FAILED after {:.2f}s: {}\n{}".format(
                        chunk_size // 1024, elapsed, e, tb))
                    failures.append({
                        'chunk_size': chunk_size,
                        'error': str(e),
                        'traceback': tb,
                        'elapsed': elapsed,
                    })

        if failures:
            msg = "{}/{} chunk sizes failed:\n".format(len(failures), len(chunk_sizes))
            for f in failures:
                msg += "  {}KB: {} ({:.2f}s)\n".format(
                    f['chunk_size'] // 1024, f['error'], f['elapsed'])
            pytest.fail(msg)

    finally:
        test_server.stop()


def test_stress_download_after_navigation():
    """
    Navigate to a new page between each download.
    Navigation creates a new browsing context, which may cause the old
    context to be discarded — potentially mid-download if there's a race.
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()

    iterations = 8
    failures = []
    pages = ["/simple", "/javascript", "/dom", "/form", "/cookies"]

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            for i in range(iterations):
                page = pages[i % len(pages)]
                logger.info("=== Iteration {}/{}: navigate to {} then download ===".format(
                    i + 1, iterations, page))

                # Navigate to a page (changes browsing context state)
                firefox.blocking_navigate_and_get_source(
                    test_server.get_url(page), timeout=15)

                start = time.time()
                try:
                    result = firefox.xhr_fetch(
                        test_server.get_url("/download/large.bin"),
                        use_chunks=True,
                        chunk_size=128 * 1024  # 128KB → ~40 chunks
                    )
                    elapsed = time.time() - start
                    logger.info("Download {} completed in {:.2f}s".format(i + 1, elapsed))

                    assert result.get('code') in (200, 206)
                    _verify_large_bin_content(result['content'], LARGE_FILE_SIZE)

                except Exception as e:
                    elapsed = time.time() - start
                    tb = traceback.format_exc()
                    logger.error("Download {} FAILED after {:.2f}s: {}\n{}".format(
                        i + 1, elapsed, e, tb))
                    failures.append({
                        'iteration': i + 1,
                        'page': page,
                        'error': str(e),
                        'traceback': tb,
                        'elapsed': elapsed,
                    })

        if failures:
            msg = "{}/{} navigate+download cycles failed:\n".format(
                len(failures), iterations)
            for f in failures:
                msg += "  Iter {} ({}): {} ({:.2f}s)\n".format(
                    f['iteration'], f['page'], f['error'], f['elapsed'])
            pytest.fail(msg)

    finally:
        test_server.stop()


def test_stress_download_with_gc_pressure():
    """
    Trigger JavaScript garbage collection between chunk fetches by running
    heavy JS before each download. This tries to force context invalidation.
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()

    iterations = 5
    failures = []

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            for i in range(iterations):
                logger.info("=== Iteration {}/{}: GC pressure + download ===".format(
                    i + 1, iterations))

                # Create memory pressure by allocating and discarding large arrays
                gc_script = """
                    (function() {
                        var arrays = [];
                        for (var j = 0; j < 100; j++) {
                            arrays.push(new ArrayBuffer(1024 * 1024));
                        }
                        arrays = null;
                        return 'gc_pressure_applied';
                    })()
                """
                try:
                    firefox.execute_javascript_statement(gc_script, timeout=10)
                except Exception as e:
                    logger.warning("GC pressure script failed (non-fatal): {}".format(e))

                start = time.time()
                try:
                    result = firefox.xhr_fetch(
                        test_server.get_url("/download/large.bin"),
                        use_chunks=True,
                        chunk_size=64 * 1024  # 64KB → ~80 chunks (more bidi calls)
                    )
                    elapsed = time.time() - start
                    logger.info("Download {} completed in {:.2f}s".format(i + 1, elapsed))

                    assert result.get('code') in (200, 206)
                    _verify_large_bin_content(result['content'], LARGE_FILE_SIZE)

                except Exception as e:
                    elapsed = time.time() - start
                    tb = traceback.format_exc()
                    logger.error("Download {} FAILED after {:.2f}s: {}\n{}".format(
                        i + 1, elapsed, e, tb))
                    failures.append({
                        'iteration': i + 1,
                        'error': str(e),
                        'traceback': tb,
                        'elapsed': elapsed,
                    })

        if failures:
            msg = "{}/{} GC-pressure downloads failed:\n".format(len(failures), iterations)
            for f in failures:
                msg += "  Iter {}: {} ({:.2f}s)\n".format(
                    f['iteration'], f['error'], f['elapsed'])
            pytest.fail(msg)

    finally:
        test_server.stop()


def test_stress_rapid_sequential_downloads():
    """
    Fire downloads as fast as possible with no delay between them.
    No sleep, no navigation — just back-to-back chunk downloads.
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()

    iterations = 15
    failures = []
    total_bytes = 0
    total_time = 0.0

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            overall_start = time.time()

            for i in range(iterations):
                start = time.time()
                try:
                    result = firefox.xhr_fetch(
                        test_server.get_url("/download/large.bin"),
                        use_chunks=True,
                        chunk_size=256 * 1024
                    )
                    elapsed = time.time() - start
                    total_time += elapsed
                    size = len(result.get('content', b''))
                    total_bytes += size

                    if (i + 1) % 5 == 0 or i == 0:
                        logger.info("Download {}/{} - {:.2f}s, {} bytes".format(
                            i + 1, iterations, elapsed, size))

                    assert result.get('code') in (200, 206)
                    _verify_large_bin_content(result['content'], LARGE_FILE_SIZE)

                except Exception as e:
                    elapsed = time.time() - start
                    tb = traceback.format_exc()
                    logger.error("Download {} FAILED after {:.2f}s: {}".format(
                        i + 1, elapsed, e))
                    failures.append({
                        'iteration': i + 1,
                        'error': str(e),
                        'traceback': tb,
                        'elapsed': elapsed,
                    })

            overall_elapsed = time.time() - overall_start
            logger.info("=== Rapid download summary ===")
            logger.info("  {} downloads, {} failures".format(iterations, len(failures)))
            logger.info("  Total: {:.1f}MB in {:.1f}s ({:.2f} MB/s)".format(
                total_bytes / (1024 * 1024), overall_elapsed,
                total_bytes / (1024 * 1024) / overall_elapsed if overall_elapsed > 0 else 0))

        if failures:
            msg = "{}/{} rapid downloads failed:\n".format(len(failures), iterations)
            for f in failures:
                msg += "  Iter {}: {} ({:.2f}s)\n".format(
                    f['iteration'], f['error'], f['elapsed'])
            pytest.fail(msg)

    finally:
        test_server.stop()


def test_stress_download_with_concurrent_js():
    """
    Run JS that modifies the DOM during chunked downloads.
    This simulates a more realistic scenario where the page is active
    while a background download is happening via XHR.
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()

    iterations = 5
    failures = []

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            for i in range(iterations):
                logger.info("=== Iteration {}/{}: concurrent JS + download ===".format(
                    i + 1, iterations))

                # Inject a setInterval that continuously modifies the DOM
                setup_script = """
                    (function() {
                        if (window._stressInterval) clearInterval(window._stressInterval);
                        var counter = 0;
                        window._stressInterval = setInterval(function() {
                            counter++;
                            document.title = 'Stress ' + counter;
                            var el = document.createElement('div');
                            el.textContent = 'Dynamic content ' + counter;
                            el.id = 'stress-' + counter;
                            document.body.appendChild(el);
                            // Remove old elements to prevent DOM bloat
                            if (counter > 50) {
                                var old = document.getElementById('stress-' + (counter - 50));
                                if (old) old.remove();
                            }
                        }, 10);  // Every 10ms
                        return 'interval_started';
                    })()
                """
                try:
                    firefox.execute_javascript_statement(setup_script, timeout=5)
                except Exception as e:
                    logger.warning("Setup script failed (non-fatal): {}".format(e))

                start = time.time()
                try:
                    result = firefox.xhr_fetch(
                        test_server.get_url("/download/large.bin"),
                        use_chunks=True,
                        chunk_size=64 * 1024  # 64KB → lots of chunks while DOM is churning
                    )
                    elapsed = time.time() - start
                    logger.info("Download {} completed in {:.2f}s".format(i + 1, elapsed))

                    assert result.get('code') in (200, 206)
                    _verify_large_bin_content(result['content'], LARGE_FILE_SIZE)

                except Exception as e:
                    elapsed = time.time() - start
                    tb = traceback.format_exc()
                    logger.error("Download {} FAILED after {:.2f}s: {}\n{}".format(
                        i + 1, elapsed, e, tb))
                    failures.append({
                        'iteration': i + 1,
                        'error': str(e),
                        'traceback': tb,
                        'elapsed': elapsed,
                    })

                # Clean up the interval
                try:
                    firefox.execute_javascript_statement(
                        "(function() { clearInterval(window._stressInterval); return 'cleared'; })()",
                        timeout=5)
                except Exception:
                    pass

        if failures:
            msg = "{}/{} concurrent-JS downloads failed:\n".format(len(failures), iterations)
            for f in failures:
                msg += "  Iter {}: {} ({:.2f}s)\n".format(
                    f['iteration'], f['error'], f['elapsed'])
            pytest.fail(msg)

    finally:
        test_server.stop()


def test_stress_multiple_sessions():
    """
    Open and close Firefox multiple times, doing a chunked download each time.
    Tests whether context management across sessions contributes to the issue.
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()

    sessions = 5
    failures = []

    try:
        for i in range(sessions):
            logger.info("=== Session {}/{} ===".format(i + 1, sessions))
            start = time.time()
            try:
                with FirefoxController.FirefoxRemoteDebugInterface(
                    headless=False,
                    additional_options=["--width=800", "--height=600"]
                ) as firefox:

                    firefox.blocking_navigate_and_get_source(
                        test_server.get_url("/simple"), timeout=15)

                    result = firefox.xhr_fetch(
                        test_server.get_url("/download/large.bin"),
                        use_chunks=True,
                        chunk_size=128 * 1024
                    )
                    elapsed = time.time() - start
                    logger.info("Session {} download completed in {:.2f}s".format(
                        i + 1, elapsed))

                    assert result.get('code') in (200, 206)
                    _verify_large_bin_content(result['content'], LARGE_FILE_SIZE)

            except Exception as e:
                elapsed = time.time() - start
                tb = traceback.format_exc()
                logger.error("Session {} FAILED after {:.2f}s: {}\n{}".format(
                    i + 1, elapsed, e, tb))
                failures.append({
                    'session': i + 1,
                    'error': str(e),
                    'traceback': tb,
                    'elapsed': elapsed,
                })

        if failures:
            msg = "{}/{} sessions failed:\n".format(len(failures), sessions)
            for f in failures:
                msg += "  Session {}: {} ({:.2f}s)\n".format(
                    f['session'], f['error'], f['elapsed'])
            pytest.fail(msg)

    finally:
        test_server.stop()


# ---------------------------------------------------------------------------
# Large-file tests using /download/sized.bin with seeded random data
#
# All data is verified byte-for-byte against the deterministic SHA-512
# sequence then immediately discarded — nothing touches disk.
# ---------------------------------------------------------------------------

def test_large_download_50mb():
    """Download 50MB in-memory with random data, verify full content."""
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()
    file_size = 50 * MB
    seed = 50

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            start = time.time()
            result = firefox.xhr_fetch(
                test_server.get_url("/download/sized.bin?size={}&seed={}".format(file_size, seed)),
                use_chunks=True,
                chunk_size=4 * MB,
            )
            elapsed = time.time() - start

            logger.info("50MB download: {:.2f}s, {} chunks, code={}".format(
                elapsed, result.get('chunks'), result.get('code')))

            assert result.get('code') in (200, 206), \
                "Bad status: {}".format(result.get('code'))
            _verify_random_content(result['content'], file_size, seed)

    finally:
        test_server.stop()


def test_large_download_100mb():
    """Download 100MB in-memory with random data, verify full content."""
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()
    file_size = 100 * MB
    seed = 100

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            start = time.time()
            result = firefox.xhr_fetch(
                test_server.get_url("/download/sized.bin?size={}&seed={}".format(file_size, seed)),
                use_chunks=True,
                chunk_size=4 * MB,
            )
            elapsed = time.time() - start

            logger.info("100MB download: {:.2f}s, {} chunks, code={}".format(
                elapsed, result.get('chunks'), result.get('code')))

            assert result.get('code') in (200, 206), \
                "Bad status: {}".format(result.get('code'))
            _verify_random_content(result['content'], file_size, seed)

    finally:
        test_server.stop()


def test_large_download_500mb():
    """Download 500MB via chunk_callback — verify each chunk then discard."""
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()
    file_size = 500 * MB
    seed = 500

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            verifier = _ChunkVerifier(seed)
            start = time.time()
            result = firefox.xhr_fetch(
                test_server.get_url("/download/sized.bin?size={}&seed={}".format(file_size, seed)),
                use_chunks=True,
                chunk_size=4 * MB,
                chunk_callback=verifier,
            )
            elapsed = time.time() - start

            logger.info("500MB streaming download: {:.2f}s, {} chunks, code={}, verified={}".format(
                elapsed, result.get('chunks'), result.get('code'), verifier.total_bytes))

            assert result.get('code') in (200, 206), \
                "Bad status: {}".format(result.get('code'))
            assert result.get('size') == file_size, \
                "Expected size {} but got {}".format(file_size, result.get('size'))
            assert verifier.total_bytes == file_size, \
                "Verifier saw {} bytes, expected {}".format(verifier.total_bytes, file_size)
            assert not verifier.errors, \
                "Verification errors:\n  " + "\n  ".join(verifier.errors)

    finally:
        test_server.stop()


def test_large_download_1gb():
    """Download 1GB via chunk_callback — verify each chunk then discard."""
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()
    file_size = 1 * GB
    seed = 1024

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            verifier = _ChunkVerifier(seed)
            start = time.time()
            result = firefox.xhr_fetch(
                test_server.get_url("/download/sized.bin?size={}&seed={}".format(file_size, seed)),
                use_chunks=True,
                chunk_size=4 * MB,
                chunk_callback=verifier,
            )
            elapsed = time.time() - start

            logger.info("1GB streaming download: {:.2f}s, {} chunks, code={}, verified={}".format(
                elapsed, result.get('chunks'), result.get('code'), verifier.total_bytes))

            assert result.get('code') in (200, 206), \
                "Bad status: {}".format(result.get('code'))
            assert result.get('size') == file_size, \
                "Expected size {} but got {}".format(file_size, result.get('size'))
            assert verifier.total_bytes == file_size, \
                "Verifier saw {} bytes, expected {}".format(verifier.total_bytes, file_size)
            assert not verifier.errors, \
                "Verification errors:\n  " + "\n  ".join(verifier.errors)

    finally:
        test_server.stop()


def test_large_download_streaming_integrity():
    """
    Download 20MB via chunk_callback and verify every single byte matches
    the expected SHA-512-based sequence.  Exercises the verify-then-discard
    path more thoroughly than the larger tests (which also verify, but
    where a failure is harder to debug).
    """
    logger = logging.getLogger("FirefoxController")

    test_server = TestServer()
    test_server.start()
    file_size = 20 * MB
    seed = 9999

    try:
        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
            additional_options=["--width=800", "--height=600"]
        ) as firefox:

            firefox.blocking_navigate_and_get_source(
                test_server.get_url("/simple"), timeout=15)

            verifier = _ChunkVerifier(seed)
            result = firefox.xhr_fetch(
                test_server.get_url("/download/sized.bin?size={}&seed={}".format(file_size, seed)),
                use_chunks=True,
                chunk_size=4 * MB,
                chunk_callback=verifier,
            )

            assert result.get('code') in (200, 206)
            assert result.get('size') == file_size
            assert verifier.total_bytes == file_size
            assert not verifier.errors, \
                "Verification errors:\n  " + "\n  ".join(verifier.errors)
            logger.info("Streaming integrity: {} bytes verified byte-for-byte".format(
                verifier.total_bytes))

    finally:
        test_server.stop()


if __name__ == "__main__":
    # Setup logging
    FirefoxController.setup_logging(verbose=True)

    # Run pytest on this file
    sys.exit(pytest.main([__file__, "-v", "--tb=long", "-x"]))
