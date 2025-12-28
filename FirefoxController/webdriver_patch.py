#!/usr/bin/env python3

"""
WebDriver detection patch for Firefox.

This module patches Firefox's libxul.so to replace 'webdriver' with 'webderper',
making WebDriver undetectable by websites that check for this string.

Usage:
    # Check and patch (run with sudo if needed):
    sudo python /path/to/FirefoxController/webdriver_patch.py

    # Or if installed as a package:
    sudo firefox-patch-webdriver
"""

import os
import sys
import shutil


class WebDriverPatchError(Exception):
    """Exception raised when WebDriver patching fails."""
    pass


def find_firefox_libxul():
    """
    Find the libxul.so file for Firefox.

    Returns:
        Path to libxul.so or None if not found
    """
    # Find Firefox binary
    firefox_binary = shutil.which("firefox")
    if not firefox_binary:
        return None

    # Resolve symlinks to get the real Firefox installation directory
    firefox_real = os.path.realpath(firefox_binary)
    firefox_dir = os.path.dirname(firefox_real)

    # libxul.so is typically in the same directory as the firefox binary
    libxul_path = os.path.join(firefox_dir, "libxul.so")
    if os.path.exists(libxul_path):
        return libxul_path

    # Also check common locations
    common_paths = [
        "/usr/lib/firefox/libxul.so",
        "/usr/lib64/firefox/libxul.so",
        "/usr/lib/firefox-esr/libxul.so",
        "/opt/firefox/libxul.so",
        "/snap/firefox/current/usr/lib/firefox/libxul.so",
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None


def check_needs_patching():
    """
    Check if Firefox's libxul.so needs to be patched.

    Returns:
        Tuple of (needs_patching: bool, libxul_path: str or None, message: str)
    """
    libxul_path = find_firefox_libxul()

    if libxul_path is None:
        return False, None, "Firefox libxul.so not found"

    try:
        with open(libxul_path, 'rb') as f:
            content = f.read()
    except Exception as e:
        return False, libxul_path, "Cannot read libxul.so: {}".format(e)

    if b'webdriver' in content:
        return True, libxul_path, "libxul.so contains 'webdriver' and needs patching"
    else:
        return False, libxul_path, "libxul.so is already patched or doesn't contain 'webdriver'"


def patch_libxul(libxul_path=None):
    """
    Patch Firefox's libxul.so to replace 'webdriver' with 'webderper'.

    Args:
        libxul_path: Path to libxul.so (auto-detected if None)

    Returns:
        True if patching was successful or not needed

    Raises:
        WebDriverPatchError: If patching fails
    """
    if libxul_path is None:
        libxul_path = find_firefox_libxul()

    if libxul_path is None:
        raise WebDriverPatchError(
            "Could not find Firefox's libxul.so. "
            "Please ensure Firefox is installed and in your PATH."
        )

    # Read the binary file
    try:
        with open(libxul_path, 'rb') as f:
            content = f.read()
    except PermissionError:
        raise WebDriverPatchError(
            "Permission denied reading libxul.so at {}".format(libxul_path)
        )
    except Exception as e:
        raise WebDriverPatchError(
            "Failed to read libxul.so at {}: {}".format(libxul_path, e)
        )

    # Check if "webdriver" exists in the binary
    webdriver_bytes = b'webdriver'
    webderper_bytes = b'webderper'

    if webdriver_bytes not in content:
        # Already patched or doesn't contain webdriver
        return True

    # Create backup if it doesn't exist
    backup_path = libxul_path + '.bak'
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(libxul_path, backup_path)
        except PermissionError:
            raise WebDriverPatchError(
                "Permission denied creating backup at {}. "
                "Try running with sudo.".format(backup_path)
            )
        except Exception as e:
            raise WebDriverPatchError(
                "Failed to create backup at {}: {}".format(backup_path, e)
            )

    # Replace all occurrences of 'webdriver' with 'webderper'
    patched_content = content.replace(webdriver_bytes, webderper_bytes)

    # Write the patched content back
    try:
        with open(libxul_path, 'wb') as f:
            f.write(patched_content)
    except PermissionError:
        raise WebDriverPatchError(
            "Permission denied writing to {}. "
            "Try running with sudo.".format(libxul_path)
        )
    except Exception as e:
        raise WebDriverPatchError(
            "Failed to write patched libxul.so at {}: {}".format(libxul_path, e)
        )

    return True


def check_and_raise_if_needed():
    """
    Check if patching is needed and raise an error with instructions if so.

    This is called on module import to ensure the user is aware that patching
    is required.

    Raises:
        WebDriverPatchError: If patching is needed but cannot be done
    """
    needs_patching, libxul_path, message = check_needs_patching()

    if not needs_patching:
        return

    # Check if we can write to the file
    if libxul_path and os.access(libxul_path, os.W_OK):
        # We have write access, try to patch
        try:
            patch_libxul(libxul_path)
            return
        except WebDriverPatchError:
            pass  # Fall through to error message

    # We need patching but can't do it - raise with instructions
    # Get the path to this script for the error message
    script_path = os.path.abspath(__file__)
    raise WebDriverPatchError(
        "Firefox's libxul.so contains 'webdriver' string which makes WebDriver detectable.\n"
        "To patch it, run one of the following commands:\n\n"
        "    sudo python {}\n\n"
        "Or if installed as a package:\n\n"
        "    sudo firefox-patch-webdriver\n\n"
        "libxul.so location: {}".format(script_path, libxul_path)
    )


def main():
    """CLI entry point for patching Firefox."""
    print("Firefox WebDriver Patch Utility")
    print("=" * 40)

    needs_patching, libxul_path, message = check_needs_patching()

    if libxul_path:
        print("libxul.so location: {}".format(libxul_path))
    else:
        print("ERROR: Could not find Firefox's libxul.so")
        print("Please ensure Firefox is installed and in your PATH.")
        sys.exit(1)

    print("Status: {}".format(message))

    if not needs_patching:
        print("\nNo patching needed.")
        sys.exit(0)

    print("\nAttempting to patch...")

    try:
        patch_libxul(libxul_path)
        print("SUCCESS: libxul.so has been patched.")
        print("Backup saved to: {}.bak".format(libxul_path))
        sys.exit(0)
    except WebDriverPatchError as e:
        print("\nERROR: {}".format(e))
        if "Permission denied" in str(e):
            script_path = os.path.abspath(__file__)
            print("\nTry running with sudo:")
            print("    sudo python {}".format(script_path))
        sys.exit(1)


if __name__ == "__main__":
    main()
