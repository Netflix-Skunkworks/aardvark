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

about = {}
with open(os.path.join(ROOT, "aardvark", "__about__.py")) as f:
    exec(f.read(), about)


def read(*paths):
    """Read the contents of a text file safely."""
    rootpath = os.path.dirname(__file__)
    filepath = os.path.join(rootpath, *paths)
    with open(filepath, encoding="utf-8") as file_:
        return file_.read().strip()
    

def read_requirements(path):
    """Return a list of requirements from a text file"""
    return [
        line.strip()
        for line in read(path).split("\n")
        if not line.startswith(("#", "git+", '"', "-"))
    ]

tests_require = [
    'pexpect>=4.2.1'
]

docs_require = [
]

dev_requires = [
]


setup(
    name=about["__title__"],
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__email__"],
    url=about["__uri__"],
    description=about["__summary__"],
    long_description=open(os.path.join(ROOT, 'README.md')).read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[ read_requirements("requirements.txt") ],
    extras_require={
        'tests': tests_require,
        'docs': docs_require,
        'dev': dev_requires,
    },
    entry_points={
        'console_scripts': [
            'aardvark = aardvark.manage:main',
        ],
    }
)
