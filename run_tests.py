#!/usr/bin/env python3

"""
Automatic Test Runner for FirefoxController using pytest

This script runs all tests in the tests/ directory using pytest.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_pytest_tests(test_files: list) -> tuple:
    """Run pytest on the specified test files"""
    print(f"\n{'='*60}")
    print("Running pytest on all test files")
    print('='*60)
    
    try:
        # Set PYTHONPATH to include the current directory
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)
        
        # Convert test files to pytest format
        test_args = [str(f) for f in test_files]
        
        # Run pytest without timeout
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v"] + test_args,
            capture_output=True,
            text=True,
            env=env
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except Exception as e:
        print(f"Tests failed with exception: {e}")
        return False, "", str(e)

def main():
    """Main test runner function"""
    print("FirefoxController Automatic Test Runner (using pytest)")
    print("="*60)
    
    # Find all test files
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("Tests directory not found!")
        return 1
    
    # Look for both old and new test files
    test_files = list(tests_dir.glob("test_*.py"))
    
    if not test_files:
        print("No test files found in tests/ directory!")
        return 1
    
    print(f"Found {len(test_files)} test files:")
    for i, test_file in enumerate(test_files, 1):
        print(f"  {i}. {test_file.name}")
    
    # Run tests using pytest
    start_time = time.time()
    
    success, stdout, stderr = run_pytest_tests(test_files)
    
    # Summary
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    if success:
        print("All pytest tests passed!")
        print(f"Total time: {total_time:.1f} seconds")
        return 0
    else:
        print("Some pytest tests failed")
        print(f"Total time: {total_time:.1f} seconds")
        return 1

if __name__ == "__main__":
    sys.exit(main())