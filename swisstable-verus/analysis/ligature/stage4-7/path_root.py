#!/usr/bin/env python3
"""Shared ROOT resolution for the chainlink #29 scripts.

Do NOT count `os.path.dirname` levels: this file tree has been nested at two different
depths during P2 (`analysis/ligature/` and `analysis/ligature/stage4-7/`), and a
mis-counted level silently resolves ROOT to a sibling directory -- which either raises
FileNotFoundError or, worse, writes to the wrong tree. Walk up until the pilot root is
actually found instead.

    from path_root import pilot_root
    ROOT = pilot_root()
"""
from __future__ import annotations

import os
import sys

MARKER = "project-descriptor.json"


def pilot_root() -> str:
    """The nearest ancestor directory (inclusive) holding project-descriptor.json."""
    cand = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isfile(os.path.join(cand, MARKER)):
            return cand
        parent = os.path.dirname(cand)
        if parent == cand:  # filesystem root, no MARKER anywhere above us
            sys.exit(f"could not find {MARKER} in any ancestor of {cand}")
        cand = parent
