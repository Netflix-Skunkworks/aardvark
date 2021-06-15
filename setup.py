"""
Aardvark
=====
Multi-Account AWS IAM Access Advisor API
:copyright: (c) 2017 by Netflix
:license: Apache, see LICENSE for more details.
"""
from __future__ import absolute_import

import sys
import os.path

from setuptools import setup, find_packages


ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__)))

# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src/ directory to the sys.path.
sys.path.insert(0, ROOT)

setup(
    name="aardvark",
    versioning="distance",
    setup_requires="setupmeta",
    entry_points={
        'console_scripts': [
            'aardvark = aardvark.manage:main',
        ],
    }
)
