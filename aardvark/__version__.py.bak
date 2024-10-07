# this is a placeholder and will be overwritten at build time
try:
    from setuptools_scm import get_version
    __version__ = get_version(root="..", relative_to=__file__)
except (ImportError, OSError):
    # ImportError: setuptools_scm isn't installed
    # OSError: git isn't installed
    __version__ = "0.0.0.dev0+placeholder"
