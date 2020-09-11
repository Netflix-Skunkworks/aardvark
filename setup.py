"""
name: aardvark
description: Multi-Account AWS IAM Access Advisor API
author: Patrick Kelley, Travis McPeak, Patrick Sanders
maintainer: Patrick Sanders
contact: aardvark-maintainers@netflix.com
"""
from setuptools import setup

setup(
    name="aardvark",
    python_requires="~=3.8",
    versioning="dev",
    setup_requires="setupmeta",
    entry_points={"console_scripts": ["aardvark = aardvark.manage:main"]},
)
