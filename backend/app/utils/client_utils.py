"""Utilities for client name normalization and formatting.

Keep a single, testable place that defines how client display names are
normalized across the app so dropdowns and the /clients/ page always show
the same values.
"""

import unicodedata
from typing import Optional


def normalize_display_name(name: Optional[str]) -> str:
    """Normalize a client display name for consistent UI rendering.

    - Trims whitespace
    - Collapses multiple spaces
    - Preserves accents while normalizing unicode composition
    - Applies title-case (keeps small words capitalized) for nicer display

    Args:
        name: raw name string (may be None)

    Returns:
        Normalized display name (empty string if input falsy)
    """
    if not name:
        return ""

    # Normalize unicode (NFC) to preserve composed characters (accents)
    n = unicodedata.normalize("NFC", str(name))

    # Collapse whitespace
    parts = [p for p in n.split() if p]
    if not parts:
        return ""

    cleaned = " ".join(parts)

    # Use title() which respects accents; it may lowercase certain particles
    # but it's acceptable for display consistency here.
    return cleaned.title()
