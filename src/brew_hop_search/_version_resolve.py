# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Version resolution: VERSION file → PEP 440 string.

Called at build time by hatchling (via [tool.hatch.version] source = "code")
and at runtime by __init__.py. A VERSION value ending in `-dev` is resolved
against git to produce `{base}.dev{N}+{hash}[.dirty]` where N is the commit
count since the last release tag.

On installed wheels (no git reachable from the package dir), resolution
falls back to `importlib.metadata` so the wheel's baked metadata wins.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _git(args: list[str], cwd: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _commits_since_last_tag(cwd: Path) -> int:
    tag = _git(["describe", "--tags", "--abbrev=0", "--match", "v*"], cwd)
    if tag:
        out = _git(["rev-list", f"{tag}..HEAD", "--count"], cwd)
    else:
        out = _git(["rev-list", "HEAD", "--count"], cwd)
    try:
        return int(out)
    except (ValueError, TypeError):
        return 0


def _resolve_live(base: str, cwd: Path) -> str | None:
    h = _git(["rev-parse", "--short", "HEAD"], cwd)
    if not h:
        return None
    n = _commits_since_last_tag(cwd)
    dirty = bool(_git(["status", "--porcelain", "-uno"], cwd))
    suffix = f".dev{n}+{h}"
    if dirty:
        suffix += ".dirty"
    return f"{base}{suffix}"


def resolve_version() -> str:
    pkg_dir = Path(__file__).parent
    raw = (pkg_dir / "VERSION").read_text().strip()
    if not raw.endswith("-dev"):
        return raw
    base = raw[:-4]
    live = _resolve_live(base, pkg_dir)
    if live:
        return live
    # Installed wheel without git: prefer the baked metadata version.
    try:
        from importlib.metadata import version, PackageNotFoundError
        try:
            return version("brew-hop-search")
        except PackageNotFoundError:
            pass
    except ImportError:
        pass
    return f"{base}.dev0"
