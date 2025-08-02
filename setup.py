#!/usr/bin/env python3
"""
GraphShift OSS - AI-Augmented Java Migration Assistant
Setup script for package installation - JAR-based Architecture
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="graphshift-oss",
    version="1.0.0",
    description="AI-Augmented Java Migration Assistant - Open Source Edition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="GraphShift Team",
    author_email="contact@graphshift.dev",
    url="https://github.com/graphshift-dev/discovery",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.jar"],
        "config": ["*.yaml", "*.yml"],
        "gs-analyzer": ["**/*.jar"],
    },
    install_requires=[
        # Minimal dependencies for JAR-based architecture
        "pyyaml>=6.0",           # Configuration files
        "pathlib>=1.0.0",        # Path handling (built-in Python 3.4+)
        "aiohttp>=3.8.0",        # GitHub API client
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.991",
        ],
    },
    entry_points={
        "console_scripts": [
            "graphshift=cli.main:cli_entry_point",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Java",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: System :: Software Distribution",
    ],
    keywords="java migration refactoring analysis ast deprecation",
    project_urls={
        "Bug Reports": "https://github.com/graphshift-dev/discovery/issues",
        "Source": "https://github.com/graphshift-dev/discovery",
        "Documentation": "https://docs.graphshift.dev",
    },
) 