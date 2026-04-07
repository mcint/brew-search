"""brew-hop-search: fast offline-first Homebrew search."""
__version__ = "0.3.0"


def version_info() -> str:
    """Version string with git commit hash for local/dev builds."""
    try:
        import subprocess
        from pathlib import Path
        pkg_dir = Path(__file__).resolve().parent
        result = subprocess.run(
            ["git", "-C", str(pkg_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            return f"{__version__}+{commit}"
    except Exception:
        pass
    return __version__
