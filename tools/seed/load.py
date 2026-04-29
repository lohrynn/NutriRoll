"""Seed loader — thin wrapper that delegates to `nutriroll.tools.seed`.

Run from the server venv::

    cd server && uv run python -m nutriroll.tools.seed
"""

from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write(
        "Run from the server package: "
        "`cd server && uv run python -m nutriroll.tools.seed`\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
