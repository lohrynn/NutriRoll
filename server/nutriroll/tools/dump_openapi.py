"""Dump the FastAPI app's OpenAPI schema to stdout. Used by `make gen-openapi`."""

from __future__ import annotations

import json
import sys

from nutriroll.api.app import create_app


def main() -> int:
    app = create_app()
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
