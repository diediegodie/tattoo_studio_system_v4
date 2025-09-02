"""
Re-export of application domain entities to support legacy imports like
`from domain.entities import User`.

This module imports from `app.domain.entities` (the actual package in this repo)
and re-exports the symbols.
"""

from app.domain.entities import *  # noqa: F401,F403

__all__ = [name for name in globals().keys() if not name.startswith("_")]
