"""Local configuration loading (Slice 1 development).

Reads `.env.local` then `.env` from the project root when present, without
overriding real environment variables. Values are never logged here.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_local_env(root: Path | None = None) -> None:
    root = root or Path.cwd()
    for name in (".env.local", ".env"):
        path = root / name
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
