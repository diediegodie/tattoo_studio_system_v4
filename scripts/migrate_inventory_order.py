"""
Compatibility shim so tests that expect a top-level scripts/ migrate file can run.

This simply imports and executes the real migration script living under
backend/scripts/migrate_inventory_order.py when executed.
"""

import runpy
from pathlib import Path

# Determine backend script path relative to repository root and execute it.
ROOT = Path(__file__).resolve().parent.parent
BACKEND_SCRIPT = ROOT / "backend" / "scripts" / "migrate_inventory_order.py"

if not BACKEND_SCRIPT.exists():
    raise FileNotFoundError(f"Expected backend script at {BACKEND_SCRIPT}")

runpy.run_path(str(BACKEND_SCRIPT), run_name="__main__")
