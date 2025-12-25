#!/usr/bin/env python3

"""
FirefoxController Utilities

This module contains utility functions for FirefoxController.
"""

import logging
import argparse


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
    parser.add_argument("--port", type=int, default=6000, help="Debug port")
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


if __name__ == "__main__":
    main()