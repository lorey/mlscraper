#!/usr/bin/env python
"""The setup script."""
from setuptools import setup


setup(
    name="mlscraper",
    install_requires=[
        "beautifulsoup4",
        "lxml",
        "more-itertools>=8",
    ],
)
