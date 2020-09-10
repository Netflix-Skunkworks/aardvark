"""
Aardvark
=====
Multi-Account AWS IAM Access Advisor API
:copyright: (c) 2020 by Netflix
:license: Apache, see LICENSE for more details.
"""
from __future__ import absolute_import

import os.path
import sys

from setuptools import find_packages, setup

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__)))

# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src/ directory to the sys.path.
sys.path.insert(0, ROOT)

about = {}
with open(os.path.join(ROOT, "aardvark", "__about__.py")) as f:
    exec(f.read(), about)


install_requires = [
    "SQLAlchemy",
    "Flask",
    "blinker",
    "cloudaux",
    "confuse",
    "bunch",
    "flasgger",
]

tests_require = []

docs_require = []

dev_requires = []


setup(
    name=about["__title__"],
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__email__"],
    url=about["__uri__"],
    description=about["__summary__"],
    python_requires="~=3.8",
    long_description=open(os.path.join(ROOT, "README.md")).read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={"tests": tests_require, "docs": docs_require, "dev": dev_requires},
    entry_points={"console_scripts": ["aardvark = aardvark.manage:main"]},
)
