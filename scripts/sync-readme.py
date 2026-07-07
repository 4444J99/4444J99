#!/usr/bin/env python3
"""
sync-readme — inject the single-source ecosystem stats into README.md markers.

Reads data/ecosystem.yml and replaces the content between each
`<!-- v:KEY -->...<!-- /v -->` pair in README.md with the matching value.

Usage:
  python3 scripts/sync-readme.py            # rewrite README.md in place
  python3 scripts/sync-readme.py --check    # exit 1 if README is out of sync

Environment overrides:
  ECOSYSTEM_DATA  — path to the data file (default: data/ecosystem.yml)
  README_PATH     — path to the README   (default: README.md)
"""

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
# Keys are snake_case identifiers; DOTALL lets a marker body span lines if the
# README is ever reflowed.
MARKER = re.compile(r"(<!-- v:([A-Za-z0-9_]+) -->)(.*?)(<!-- /v -->)", re.DOTALL)


def _disp(path: Path) -> str:
    """Path relative to the repo root for messages; absolute if outside it."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def render(readme_text: str, data: dict) -> tuple[str, list[str]]:
    """Return (new_text, warnings). Replaces each marker's body with data[KEY]."""
    warnings: list[str] = []
    seen_keys: set[str] = set()

    def repl(m: re.Match) -> str:
        key = m.group(2)
        seen_keys.add(key)
        if key not in data:
            warnings.append(f"marker '{key}' has no entry in the data file")
            return m.group(0)
        return f"{m.group(1)}{data[key]}{m.group(4)}"

    new_text = MARKER.sub(repl, readme_text)
    for key in data:
        if key not in seen_keys:
            warnings.append(f"data key '{key}' has no matching marker in the README")
    return new_text, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="verify README is in sync; exit 1 on drift (no write)")
    args = parser.parse_args()

    data_path = Path(os.environ.get("ECOSYSTEM_DATA") or REPO_ROOT / "data/ecosystem.yml")
    readme_path = Path(os.environ.get("README_PATH") or REPO_ROOT / "README.md")

    raw = yaml.safe_load(data_path.read_text(encoding="utf-8")) or {}
    data = {k: ("" if v is None else str(v)) for k, v in raw.items()}

    original = readme_path.read_text(encoding="utf-8")
    new_text, warnings = render(original, data)
    for w in warnings:
        print(f"warn: {w}", file=sys.stderr)

    if args.check:
        # Warnings (e.g. a deleted marker leaving a value with nowhere to render)
        # are drift too, even when the text happens to be unchanged.
        if warnings or new_text != original:
            print(f"error: {_disp(readme_path)} is out of sync with {_disp(data_path)} — "
                  f"run `python3 scripts/sync-readme.py`", file=sys.stderr)
            return 1
        print(f"{_disp(readme_path)} is in sync.")
        return 0

    if new_text != original:
        readme_path.write_text(new_text, encoding="utf-8")
        print(f"updated {_disp(readme_path)}")
    else:
        print(f"{_disp(readme_path)} already in sync — no change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
