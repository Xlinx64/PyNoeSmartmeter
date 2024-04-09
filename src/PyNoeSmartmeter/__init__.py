"""Unofficial Python wrapper for the Netz Noe Smart Meter private API."""

from importlib.metadata import version

from .client import Smartmeter

try:
    __version__ = version(__name__)
except Exception:
    pass

__all__ = ["Smartmeter"]
