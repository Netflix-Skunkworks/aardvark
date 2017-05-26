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


install_requires = [
    'better_exceptions==0.1.7',
    'Bunch==1.0.1',
    'Flask-SQLAlchemy==2.2',
    'cloudaux>=1.2.0',
    'Flask==0.12.1',
    'Flask-RESTful==0.3.5',
    'Flask-Script==2.0.5',
    'flasgger==0.6.3',
    'gunicorn==19.7.1',
    'psycopg2==2.7.1',
    'pytz==2017.2',
    'subprocess32==3.2.7',
    'swag-client==0.1.0.dev3',
    'tqdm==4.11.2'
]

tests_require = [
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
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
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
