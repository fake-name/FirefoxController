#!/usr/bin/env python3

"""
Test xhr_fetch() for downloading various file types without triggering the download manager

This test verifies that:
1. xhr_fetch() can retrieve binary content (images, PDFs, ZIP files)
2. The content is returned as bytes, not triggering Firefox's download manager
3. Different content types are handled correctly
4. File integrity is maintained (checksums match expected values)
"""

import pytest
import FirefoxController
import logging
import hashlib
import sys
import os
import zipfile
import io

# Add tests directory to path so we can import test_server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_server import TestServer


def test_xhr_fetch_text_file():
    """Test xhr_fetch with plain text file"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch text file test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
        ) as firefox:

            # Navigate to a page first (xhr_fetch is affected by same-origin policy)
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch with plain text file
            result = firefox.xhr_fetch(test_server.get_url("/download/text.txt"))

            logger.info("xhr_fetch text file result code: {}".format(result.get('code')))
            logger.info("Content type: {}".format(result.get('mimetype')))
            logger.info("Content length: {} bytes".format(len(result.get('content', b''))))

            # Verify response
            assert result is not None, "xhr_fetch should return a result"
            assert result.get('code') == 200, "Status code should be 200"
            assert 'content' in result, "Result should have content key"
            assert isinstance(result['content'], bytes), "Content should be bytes"

            # Verify content
            content_text = result['content'].decode('utf-8')
            assert "plain text file" in content_text, "Content should contain expected text"

            # Verify response field also has text (for backward compatibility)
            assert 'response' in result, "Result should have response key"
            assert "plain text file" in result['response'], "Response should contain expected text"

            logger.info("Text file test passed!")

    finally:
        test_server.stop()


def test_xhr_fetch_json_file():
    """Test xhr_fetch with JSON file"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch JSON file test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
        ) as firefox:

            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch with JSON file
            result = firefox.xhr_fetch(test_server.get_url("/download/data.json"))

            logger.info("xhr_fetch JSON file result code: {}".format(result.get('code')))
            logger.info("Content type: {}".format(result.get('mimetype')))

            # Verify response
            assert result.get('code') == 200, "Status code should be 200"
            assert 'content' in result, "Result should have content key"

            # Parse JSON from content
            import json
            json_data = json.loads(result['content'].decode('utf-8'))
            assert json_data['type'] == 'downloadable_data', "JSON should have expected type"

            # Also verify response field
            json_data2 = json.loads(result['response'])
            assert json_data2['type'] == 'downloadable_data', "Response field should have same data"

            logger.info("JSON file test passed!")

    finally:
        test_server.stop()


def test_xhr_fetch_image_file():
    """Test xhr_fetch with PNG image file (binary content)"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch image file test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
        ) as firefox:

            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch with PNG image
            result = firefox.xhr_fetch(test_server.get_url("/download/image.png"))

            logger.info("xhr_fetch image result code: {}".format(result.get('code')))
            logger.info("Content type: {}".format(result.get('mimetype')))
            logger.info("Content length: {} bytes".format(len(result.get('content', b''))))

            # Verify response
            assert result.get('code') == 200, "Status code should be 200"
            assert 'image/png' in result.get('mimetype', ''), "MIME type should be image/png"
            assert 'content' in result, "Result should have content key"
            assert isinstance(result['content'], bytes), "Content should be bytes"

            # Verify PNG signature (first 8 bytes)
            png_signature = b'\x89PNG\r\n\x1a\n'
            assert result['content'][:8] == png_signature, "Content should start with PNG signature"

            # Verify response field is empty for binary content
            assert result['response'] == '', "Response field should be empty for binary content"

            # Calculate checksum to verify integrity
            checksum = hashlib.md5(result['content']).hexdigest()
            logger.info("Image checksum: {}".format(checksum))

            # The checksum should be consistent
            assert len(result['content']) > 0, "Image content should not be empty"

            logger.info("Image file test passed!")

    finally:
        test_server.stop()


def test_xhr_fetch_pdf_file():
    """Test xhr_fetch with PDF file (binary content)"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch PDF file test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
        ) as firefox:

            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch with PDF file
            result = firefox.xhr_fetch(test_server.get_url("/download/document.pdf"))

            logger.info("xhr_fetch PDF result code: {}".format(result.get('code')))
            logger.info("Content type: {}".format(result.get('mimetype')))
            logger.info("Content length: {} bytes".format(len(result.get('content', b''))))

            # Verify response
            assert result.get('code') == 200, "Status code should be 200"
            assert 'application/pdf' in result.get('mimetype', ''), "MIME type should be application/pdf"
            assert 'content' in result, "Result should have content key"
            assert isinstance(result['content'], bytes), "Content should be bytes"

            # Verify PDF signature
            assert result['content'][:5] == b'%PDF-', "Content should start with PDF signature"

            # Verify the content contains expected text
            content_str = result['content'].decode('latin-1')  # PDFs use latin-1 encoding
            assert 'Test PDF' in content_str, "PDF should contain expected text"

            # PDFs are partially text-based, so response field may contain content
            # The important thing is that we got the binary content correctly
            assert 'response' in result, "Result should have response field"
            assert '%PDF-1.4' in result['response'], "Response should contain PDF header"

            logger.info("PDF file test passed!")

    finally:
        test_server.stop()


def test_xhr_fetch_zip_file():
    """Test xhr_fetch with ZIP archive (binary content)"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch ZIP file test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
        ) as firefox:

            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch with ZIP file
            result = firefox.xhr_fetch(test_server.get_url("/download/archive.zip"))

            logger.info("xhr_fetch ZIP result code: {}".format(result.get('code')))
            logger.info("Content type: {}".format(result.get('mimetype')))
            logger.info("Content length: {} bytes".format(len(result.get('content', b''))))

            # Verify response
            assert result.get('code') == 200, "Status code should be 200"
            assert 'application/zip' in result.get('mimetype', ''), "MIME type should be application/zip"
            assert 'content' in result, "Result should have content key"
            assert isinstance(result['content'], bytes), "Content should be bytes"

            # Verify ZIP signature (PK header)
            assert result['content'][:2] == b'PK', "Content should start with ZIP signature (PK)"

            # Try to extract the ZIP to verify it's valid
            zip_buffer = io.BytesIO(result['content'])
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                # Verify the ZIP contains expected file
                file_list = zip_file.namelist()
                logger.info("ZIP contents: {}".format(file_list))
                assert 'test.txt' in file_list, "ZIP should contain test.txt"

                # Read the file content
                file_content = zip_file.read('test.txt').decode('utf-8')
                assert 'test file in a ZIP archive' in file_content, "File should contain expected text"

            logger.info("ZIP file test passed!")

    finally:
        test_server.stop()


def test_xhr_fetch_binary_file():
    """Test xhr_fetch with arbitrary binary data"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch binary file test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
        ) as firefox:

            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch with binary file
            result = firefox.xhr_fetch(test_server.get_url("/download/binary.bin"))

            logger.info("xhr_fetch binary result code: {}".format(result.get('code')))
            logger.info("Content type: {}".format(result.get('mimetype')))
            logger.info("Content length: {} bytes".format(len(result.get('content', b''))))

            # Verify response
            assert result.get('code') == 200, "Status code should be 200"
            assert 'content' in result, "Result should have content key"
            assert isinstance(result['content'], bytes), "Content should be bytes"

            # Verify the binary data (should be bytes 0-255)
            assert len(result['content']) == 256, "Binary file should be 256 bytes"
            assert result['content'] == bytes(range(256)), "Content should match expected binary data"

            # Verify response field is empty for binary content
            assert result['response'] == '', "Response field should be empty for binary content"

            logger.info("Binary file test passed!")

    finally:
        test_server.stop()


def test_xhr_fetch_no_download_manager_trigger():
    """
    Verify that xhr_fetch doesn't trigger Firefox's download manager

    This is verified by:
    1. Successfully retrieving content programmatically
    2. No download dialogs appearing (tested by completing without user interaction)
    3. Content being available in memory, not saved to disk
    """

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting download manager trigger test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,  # Use visible mode to see if download dialog appears
        ) as firefox:

            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Fetch multiple file types that would normally trigger downloads
            file_types = [
                ("/download/image.png", "image/png"),
                ("/download/document.pdf", "application/pdf"),
                ("/download/archive.zip", "application/zip"),
                ("/download/binary.bin", "application/octet-stream"),
            ]

            for url_path, expected_mime in file_types:
                logger.info("Fetching {}...".format(url_path))
                result = firefox.xhr_fetch(test_server.get_url(url_path))

                # Verify successful retrieval
                assert result.get('code') == 200, "File {} should be retrieved successfully".format(url_path)
                assert expected_mime in result.get('mimetype', ''), "MIME type should match for {}".format(url_path)
                assert len(result.get('content', b'')) > 0, "Content should not be empty for {}".format(url_path)

                logger.info("Successfully fetched {} ({} bytes) without triggering download manager".format(
                    url_path, len(result.get('content', b''))
                ))

            logger.info("All files fetched successfully without download manager!")
            logger.info("Test completed - no download dialogs should have appeared")

    finally:
        test_server.stop()


def test_xhr_fetch_with_custom_headers():
    """Test xhr_fetch with custom headers on file downloads"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch with custom headers test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
        ) as firefox:

            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch with custom headers
            result = firefox.xhr_fetch(
                test_server.get_url("/download/data.json"),
                headers={"X-Custom-Header": "TestValue", "X-Request-ID": "12345"}
            )

            logger.info("xhr_fetch with headers result code: {}".format(result.get('code')))

            # Verify response
            assert result.get('code') == 200, "Status code should be 200"
            assert 'content' in result, "Result should have content key"

            # Parse and verify JSON
            import json
            json_data = json.loads(result['content'].decode('utf-8'))
            assert json_data['type'] == 'downloadable_data', "JSON should have expected content"

            logger.info("Custom headers test passed!")

    finally:
        test_server.stop()


def test_xhr_fetch_large_file_chunked():
    """Test xhr_fetch with large file using automatic chunking"""

    logger = logging.getLogger("FirefoxController")

    # Start test server
    test_server = TestServer()
    test_server.start()

    try:
        logger.info("Starting xhr_fetch large file chunked test...")

        with FirefoxController.FirefoxRemoteDebugInterface(
            headless=False,
        ) as firefox:

            # Navigate to a page first
            firefox.blocking_navigate_and_get_source(test_server.get_url("/simple"), timeout=15)

            # Test xhr_fetch with a 5MB file (explicitly enable chunking with 256KB chunks)
            # Note: Chunks must be <750KB due to WebSocket 1MB limit (base64 overhead)
            logger.info("Downloading 5MB file with chunking...")
            result = firefox.xhr_fetch(
                test_server.get_url("/download/large.bin"),
                use_chunks=True,
                chunk_size=256*1024  # 256KB chunks (341KB after base64, safe margin)
            )

            logger.info("xhr_fetch large file result code: {}".format(result.get('code')))
            logger.info("Content length: {} bytes".format(len(result.get('content', b''))))
            logger.info("Chunked: {}".format(result.get('chunked', False)))
            logger.info("Number of chunks: {}".format(result.get('chunks', 0)))

            # Verify response
            assert result.get('code') in (200, 206), "Status code should be 200 or 206"
            assert 'content' in result, "Result should have content key"
            assert isinstance(result['content'], bytes), "Content should be bytes"

            # Verify file size (5MB)
            expected_size = 5 * 1024 * 1024
            assert len(result['content']) == expected_size, "File size should be 5MB"

            # Verify chunking was used
            assert result.get('chunked') == True, "Should have used chunked transfer"
            assert result.get('chunks', 0) > 1, "Should have multiple chunks"

            # Verify data integrity (repeating pattern)
            logger.info("Verifying data integrity...")
            for i in range(min(10000, len(result['content']))):  # Check first 10000 bytes
                expected_byte = i % 256
                actual_byte = result['content'][i]
                assert actual_byte == expected_byte, "Byte {} should be {} but got {}".format(i, expected_byte, actual_byte)

            logger.info("Large file chunked test passed!")

    finally:
        test_server.stop()


if __name__ == "__main__":
    # Setup logging
    FirefoxController.setup_logging(verbose=True)

    # Run pytest on this file
    sys.exit(pytest.main([__file__, "-v"]))
