#!/usr/bin/env python3

"""
Automatic Test Runner for FirefoxController

This script runs all tests in the tests/ directory automatically.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_test(test_file: str, timeout: int = 360) -> bool:
    """Run a single test file with timeout"""
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print('='*60)
    
    try:
        # Set PYTHONPATH to include the current directory
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)
        
        # Run the test with timeout
        result = subprocess.run(
            [sys.executable, test_file],
            timeout=timeout,
            capture_output=True,
            text=True,
            env=env
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⚠️  Test timed out after {timeout} seconds")
        return False
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def main():
    """Main test runner function"""
    print("🚀 FirefoxController Automatic Test Runner")
    print("="*60)
    
    # Find all test files
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("❌ Tests directory not found!")
        return 1
    
    test_files = list(tests_dir.glob("test_*.py"))
    
    if not test_files:
        print("❌ No test files found in tests/ directory!")
        return 1
    
    print(f"Found {len(test_files)} test files:")
    for i, test_file in enumerate(test_files, 1):
        print(f"  {i}. {test_file.name}")
    
    # Run tests
    results = []
    start_time = time.time()
    
    for test_file in test_files:
        success = run_test(str(test_file))
        results.append((test_file.name, success))
    
    # Summary
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    print(f"⏱️  Total time: {total_time:.1f} seconds")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())