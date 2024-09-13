"""
Aardvark
=====
Multi-Account AWS IAM Access Advisor API
:copyright: (c) 2017 by Netflix
:license: Apache, see LICENSE for more details.
"""
from __future__ import absolute_import

from pathlib import Path

from setuptools import setup, find_packages

from aardvark import __about__

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

install_requires = [
    'requests',
    'better_exceptions',
    'blinker',
    'Bunch',
    'Flask-SQLAlchemy>=2.5',
    'cloudaux>=1.8.0',
    'Flask',
    'Jinja2',
    'Flask-RESTful',
    'Flask-Script',
    'flasgger',
    'gunicorn',
    'itsdangerous',
    'psycopg2-binary',
    'pytz',
    'swag-client',
    'tqdm',
]

tests_require = [
    'pexpect>=4.2.1'
]


setup(
    name=__about__.__title__,
    version=__about__.__version__,
    author=__about__.__author__,
    author_email=__about__.__email__,
    url=__about__.__uri__,
    description=__about__.__summary__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        'tests': tests_require,
    },
    entry_points={
        'console_scripts': [
            'aardvark = aardvark.manage:main',
        ],
    },
    python_requires=">=3.8,<3.10",
)
