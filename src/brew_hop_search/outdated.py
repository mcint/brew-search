"""Collect and report outdated Homebrew packages."""
from __future__ import annotations

import json
import subprocess
import sys

from brew_hop_search.display import (
    bold, dim, green, yellow, red, status_line, fmt_duration,
)


def _brew_outdated_json() -> list[dict]:
    """Run `brew outdated --json` and return parsed list."""
    result = subprocess.run(
        ["brew", "outdated", "--json=v2"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"brew outdated failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def collect_outdated(silent: bool = False) -> dict:
    """Collect outdated formulae and casks.

    Returns dict with 'formulae' and 'casks' lists.
    """
    if not silent:
        status_line(dim("  [outdated] checking for updates …"))
    data = _brew_outdated_json()
    formulae = data.get("formulae", [])
    casks = data.get("casks", [])
    if not silent:
        total = len(formulae) + len(casks)
        status_line(dim(f"  [outdated] ✓ found {total} outdated"), done=True)
    return {"formulae": formulae, "casks": casks}


def display_outdated(data: dict, as_json: bool = False) -> None:
    """Display outdated packages with upgrade/pin hints."""
    formulae = data.get("formulae", [])
    casks = data.get("casks", [])

    if as_json:
        print(json.dumps(data, indent=2))
        return

    if not formulae and not casks:
        print(dim("  all packages are up to date"))
        return

    if formulae:
        print(f"  {green('outdated formulae')}")
        for f in formulae:
            name = f.get("name", "")
            current = f.get("installed_versions", ["?"])
            if isinstance(current, list):
                current = current[0] if current else "?"
            latest = f.get("current_version", "?")
            pinned = f.get("pinned", False)
            pin_tag = f"  {yellow('[pinned]')}" if pinned else ""
            print(f"  {bold(green(name))}  {dim(str(current))} → {latest}{pin_tag}")
        print()

    if casks:
        print(f"  {yellow('outdated casks')}")
        for c in casks:
            name = c.get("name", "")
            current = c.get("installed_versions", "?")
            if isinstance(current, str):
                pass
            elif isinstance(current, list):
                current = current[0] if current else "?"
            latest = c.get("current_version", "?")
            print(f"  {bold(yellow(name))}  {dim(str(current))} → {latest}")
        print()

    total = len(formulae) + len(casks)
    print(dim(f"  {total} outdated  •  brew upgrade"))
    print(dim(f"  pin:      brew pin <name>"))
    print(dim(f"  rollback: brew install <name>@<version>"))
    print(dim(f"  history:  brew-hop-search -H <name>"))
