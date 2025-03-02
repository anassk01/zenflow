"""
Setup configuration for ZenFlow application.
"""

from setuptools import setup, find_packages
from src.config.constants import APP_NAME, APP_VERSION, APP_AUTHOR

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zenflow",
    version=APP_VERSION,
    author=APP_AUTHOR,
    author_email="anasskgithub@gmail.com",
    description="A powerful productivity suite that helps you achieve your optimal flow state",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/anassk01/zenflow",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Office/Business :: Time Tracking",
        "Topic :: Security",
        "Topic :: Desktop Environment",
    ],
    python_requires=">=3.8",
    install_requires=[
        "ttkthemes>=3.2.2",
        "python-dateutil>=2.8.2",
        "selenium>=4.15.0",
        "webdriver-manager>=4.0.1",
        "netfilterqueue>=1.0.0",
        "scapy>=2.5.0"
    ],
    entry_points={
        "console_scripts": [
            "zenflow=main:main",
        ],
    },
    package_data={
        "zenflow": [
            "resources/*",
        ],
    },
    data_files=[
        ("share/applications", ["resources/zenflow.desktop"]),
        ("share/icons/hicolor/128x128/apps", ["resources/zenflow.png"]),
    ],
)