from importlib.metadata import version

assert __package__ is not None
__version__ = version(__package__)

__all__ = ["__version__"]
