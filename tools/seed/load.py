"""Seed loader entry point.

The real loader lands in Phase 1.2 (Component domain seed). For now this is
a stub that exits cleanly with a message — it does NOT invent any data.
"""

from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write(
        "seed loader not implemented yet — see PROJECT_VISION.md "
        "MVP scoping step 2 (Phase 1.2).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
