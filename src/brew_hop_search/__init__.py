# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""brew-hop-search: fast offline-first Homebrew search."""
import os

from brew_hop_search._version_resolve import resolve_version

__version__ = resolve_version()

PYPI_URL = "https://pypi.org/project/brew-hop-search/"
GITHUB_URL = "https://github.com/mcint/brew-hop-search"
BREW_TAP_URL = ""  # set when a tap is published

_DEFAULT_USER_AGENT = f"brew-hop-search/{__version__}"


def user_agent() -> str:
    """User-Agent string. Override via BREW_HOP_SEARCH_UA env var or config."""
    ua = os.environ.get("BREW_HOP_SEARCH_UA")
    if ua:
        return ua
    try:
        from brew_hop_search._config import load_config
        cfg = load_config()
        if cfg.get("user_agent"):
            return cfg["user_agent"]
    except Exception:
        pass
    return _DEFAULT_USER_AGENT


def commit_hash() -> str:
    """Short git commit hash, or empty string.

    Dev-tree installs resolve via `git rev-parse`. Wheel installs fall back
    to BUILD_COMMIT baked in at build time by hatch_build.py.
    """
    try:
        import subprocess
        from pathlib import Path
        pkg_dir = Path(__file__).resolve().parent
        result = subprocess.run(
            ["git", "-C", str(pkg_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    try:
        from brew_hop_search import _build_info
        return _build_info.BUILD_COMMIT
    except ImportError:
        return ""


def build_info() -> dict:
    """Static build metadata from _build_info.py (empty for dev-tree installs)."""
    try:
        from brew_hop_search import _build_info
        return {
            "commit": _build_info.BUILD_COMMIT,
            "commit_full": _build_info.BUILD_COMMIT_FULL,
            "branch": _build_info.BUILD_BRANCH,
            "tag": _build_info.BUILD_TAG,
            "dirty": _build_info.BUILD_DIRTY,
            "timestamp": _build_info.BUILD_TIMESTAMP,
        }
    except ImportError:
        return {}


def _live_dirty() -> bool:
    """Live `git status --porcelain` check (for dev-tree installs)."""
    try:
        import subprocess
        from pathlib import Path
        pkg_dir = Path(__file__).resolve().parent
        result = subprocess.run(
            ["git", "-C", str(pkg_dir), "status", "--porcelain", "-uno"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def version_info() -> str:
    """Full PEP 440 version string (alias for __version__)."""
    return __version__


def base_version() -> str:
    """Release-form base of __version__, stripping `.devN` and local labels."""
    v = __version__
    v = v.split("+", 1)[0]
    if ".dev" in v:
        v = v.split(".dev", 1)[0]
    return v


def dev_marker() -> str:
    """`(dev+N: hash[+dirty])` display marker for dev builds, `""` otherwise.

    Parses __version__ (already PEP 440 of form `base.devN+hash[.dirty]` for
    dev builds). `N` (commits since last release tag) is part of the label;
    hash and optional `+dirty` follow the colon as the specific identifier.
    """
    v = __version__
    if ".dev" not in v:
        return ""
    _, _, rest = v.partition(".dev")
    n, _, local = rest.partition("+")
    if not local:
        return f"(dev+{n})"
    h, _, extra = local.partition(".")
    inner = h + ("+dirty" if extra == "dirty" else "")
    return f"(dev+{n}: {inner})"


def install_source() -> str:
    """Where the running package came from: 'local', 'brew', 'pypi', 'unknown'.

    Local = a git work tree at the package location (uv run / editable install).
    Brew / pypi inferred from the package path.
    """
    try:
        import subprocess
        from pathlib import Path
        pkg_dir = Path(__file__).resolve().parent
        result = subprocess.run(
            ["git", "-C", str(pkg_dir), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip() == "true":
            return "local"
    except Exception:
        pass
    from pathlib import Path
    path = str(Path(__file__).resolve().parent)
    if "/Cellar/" in path or "/linuxbrew/" in path:
        return "brew"
    if "site-packages" in path:
        return "pypi"
    return "unknown"
