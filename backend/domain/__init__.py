"""
Compatibility shim package to expose app.domain as top-level 'domain'.

This file allows existing code/tests to import `domain.entities` and
`domain.interfaces` without changing all import sites.
"""

__all__ = ["entities", "interfaces"]
