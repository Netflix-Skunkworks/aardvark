"""
description: Multi-Account AWS IAM Access Advisor API
author: Patrick Kelley, Travis McPeak, Patrick Sanders
contact: aardvark-maintainers@netflix.com
copyright: (c) 2021 by Netflix
"""
from setuptools import setup

setup(
    name="aardvark",
    python_requires="~=3.7",
    versioning="dev",
    setup_requires="setupmeta",
    extras_require={
        'tests': ["pytest", "pexpect"],
    },
    entry_points={"console_scripts": ["aardvark = aardvark.manage:cli"]},
)
