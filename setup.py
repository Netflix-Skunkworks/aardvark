from setuptools import setup


setup(
    name="aardvark",
    author="Patrick Kelley, Travis McPeak, Patrick Sanders",
    author_email="aardvark-maintainers@netflix.com",
    url="https://github.com/Netflix-Skunkworks/aardvark",
    setup_requires="setupmeta",
    versioning="dev",
    extras_require={
        'tests': ['pexpect>=4.2.1'],
    },
    entry_points={
        'console_scripts': [
            'aardvark = aardvark.manage:main',
        ],
    },
    python_requires=">=3.8,<3.10",
)
