"""
Re-export of application domain interfaces to support legacy imports like
`from domain.interfaces import IUserRepository`.
"""

from app.domain.interfaces import *  # noqa: F401,F403

__all__ = [name for name in globals().keys() if not name.startswith("_")]
