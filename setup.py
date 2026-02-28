#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="FirefoxController",
    version="0.0.7",
    author="FirefoxController",
    author_email="",
    description="Python interface for Firefox Remote Debugging Protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fake-name/FirefoxController",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
    ],
    python_requires=">=3.6",
    install_requires=[
        "websockets>=8.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "firefoxcontroller=FirefoxController.firefox_controller:main",
            "firefox-patch-webdriver=FirefoxController.webdriver_patch:main",
        ],
    },
)