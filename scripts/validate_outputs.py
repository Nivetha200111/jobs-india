#!/usr/bin/env python3
"""Validate production outputs and static site assets."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jobs_india.validate import main


if __name__ == "__main__":
    raise SystemExit(main())
