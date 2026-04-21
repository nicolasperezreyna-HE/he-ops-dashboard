"""
Data source adapters.

The app never imports a specific adapter directly. It always goes through
`get_active_source()`, which reads config.SOURCE and returns the matching
adapter. That's the seam that lets us swap Google Sheets for Airtable (or
anything else) without touching the rest of the app.
"""
from importlib import import_module

from config import SOURCE
from sources.base import BaseSource


def get_active_source() -> BaseSource:
    """Return the currently-configured data source.

    Raises ImportError if the adapter module or class cannot be found.
    """
    try:
        module = import_module(f"sources.{SOURCE}")
    except ImportError as exc:
        raise ImportError(
            f"Could not find data source adapter 'sources/{SOURCE}.py'. "
            f"Check config.SOURCE."
        ) from exc

    if not hasattr(module, "Source"):
        raise ImportError(
            f"Adapter 'sources/{SOURCE}.py' must define a class named 'Source' "
            f"that inherits from BaseSource."
        )

    instance = module.Source()
    if not isinstance(instance, BaseSource):
        raise TypeError(
            f"sources.{SOURCE}.Source must inherit from sources.base.BaseSource."
        )
    return instance
