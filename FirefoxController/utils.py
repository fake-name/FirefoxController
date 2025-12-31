#!/usr/bin/env python3

"""
FirefoxController Utilities

This module contains utility functions for FirefoxController.
"""

import logging
import argparse
import socket


def setup_logging(verbose: bool = False):
    """Setup logging for FirefoxController"""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("FirefoxController")
    return logger


# Main CLI interface similar to ChromeController
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="FirefoxController - Remote control Firefox")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--silent", "-s", action="store_true", help="Silent mode")
    parser.add_argument("--binary", default="firefox", help="Firefox binary path")
    parser.add_argument("--port", type=int, default=9222, help="Debug port")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch a URL")
    fetch_parser.add_argument("url", help="URL to fetch")
    fetch_parser.add_argument("--outfile", help="Output file")
    
    # Version command
    subparsers.add_parser("version", help="Show version")
    
    args = parser.parse_args()
    
    if args.command == "version":
        print("FirefoxController v0.1")
        return
    
    elif args.command == "fetch":
        setup_logging(args.verbose)
        
        from .interface import FirefoxRemoteDebugInterface
        
        with FirefoxRemoteDebugInterface(
            binary=args.binary,
            port=args.port,
            headless=args.headless
        ) as firefox:
            
            source = firefox.blocking_navigate_and_get_source(args.url)
            
            if args.outfile:
                with open(args.outfile, "w", encoding="utf-8") as f:
                    f.write(source)
            else:
                print(source)
    
    else:
        parser.print_help()


def find_available_port(start_port=9222, max_attempts=100):
    """
    Find an available port for Firefox remote debugging.

    Uses socket binding to test port availability. First tries to bind to
    port 0 to get an OS-assigned port, then falls back to sequential scanning
    if needed.

    Args:
        start_port: Port to start searching from (default 9222)
        max_attempts: Maximum number of ports to try (default 100)

    Returns:
        int: Available port number

    Raises:
        OSError: If no available port found after max_attempts
    """
    # Try to bind to port 0 to get an OS-assigned port (most reliable)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        port = sock.getsockname()[1]
        sock.close()

        # Verify it's in a reasonable range (avoid very low ports)
        if port >= 1024:
            return port
    except OSError:
        pass

    # Fallback: scan sequential ports starting from start_port
    for offset in range(max_attempts):
        try_port = start_port + offset
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("localhost", try_port))
            sock.close()
            return try_port
        except OSError:
            continue

    raise OSError("Could not find available port after {} attempts starting from {}".format(
        max_attempts, start_port))


if __name__ == "__main__":
    main()