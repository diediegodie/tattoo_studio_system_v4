"""
Shim package to allow imports like `from services.user_service import UserService`
to resolve to the actual implementation in `app/services`.

This keeps existing import statements working without changing many files.
"""

import os
import sys

# Append the app/services directory to this package's __path__ so Python
# can find submodules under `services.<module>` that actually live in
# backend/app/services.
_here = os.path.dirname(__file__)
_candidate = os.path.abspath(os.path.join(_here, "..", "app", "services"))
if os.path.isdir(_candidate) and _candidate not in __path__:
    __path__.insert(0, _candidate)
