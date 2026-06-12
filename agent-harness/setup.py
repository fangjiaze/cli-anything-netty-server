"""Setup for the Netty Server CLI harness - cli-anything-netty-server."""

from setuptools import find_namespace_packages, setup

with open("cli_anything/netty_server/README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cli-anything-netty-server",
    version="0.1.0",
    description="CLI-Anything harness for the Netty-based IoT device server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HKUDS/CLI-Anything",
    author="CLI-Anything Contributors",
    license="MIT",
    python_requires=">=3.8",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    include_package_data=True,
    package_data={
        "cli_anything.netty_server": ["skills/SKILL.md"],
    },
    install_requires=[
        "click>=8.1",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-netty-server=cli_anything.netty_server.netty_server_cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet of Things",
        "Topic :: System :: Monitoring",
    ],
)
