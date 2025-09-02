import os

_here = os.path.dirname(__file__)
_candidate = os.path.abspath(os.path.join(_here, "..", "app", "schemas"))
if os.path.isdir(_candidate) and _candidate not in __path__:
    __path__.insert(0, _candidate)

__all__ = []
