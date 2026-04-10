# version

Show tool identity, build info, and update status.

## Purpose

Quick version check (`-V`) and detailed diagnostic info (`-VV`).

## Input

- **flag**: `-V` / `--version` (stackable: `-VV`)

No query, no source flags.

## Output

### Short (`-V`)

```
brew-hop-search 0.3.0+6ac2584
```

Version string with git commit hash (when available).

### Detailed (`-VV`)

```
brew-hop-search 0.3.0+6ac2584
  version     0.3.0
  commit      6ac2584
  user-agent  brew-hop-search/0.3.0
  pypi        https://pypi.org/project/brew-hop-search/
  github      https://github.com/mcint/brew-hop-search

recent commits
  6ac2584 Proper outdated comparison using raw JSON, add man page
  45dfaae Cache status behind -v, compact sections, default help hints
  ...

pypi  up to date (0.3.0)
```

Card format showing:
- Version, commit hash, user-agent string
- Project URLs (PyPI, GitHub, brew tap when available)
- Recent git commit log (10 entries)
- Live PyPI version check (update available or up to date)

## Identity Fields

| Field | Source |
|-------|--------|
| `version` | `__version__` in `__init__.py` |
| `commit` | `git rev-parse --short HEAD` at runtime |
| `user-agent` | `user_agent()` — env var > config > default |
| `pypi` | Hardcoded URL constant |
| `github` | Hardcoded URL constant |
| `tap` | Hardcoded URL constant (empty until published) |

## User-Agent Configuration

Priority:
1. `BREW_HOP_SEARCH_UA` environment variable
2. `user_agent` key in `~/.config/brew-hop-search/config.toml`
3. Default: `brew-hop-search/{version}`

Used in all HTTP requests (API fetch, PyPI version check).

## Data Sources

- Local: git subprocess for commit hash and log
- Network: PyPI JSON API for update check (only at `-VV`)

## Cache Behavior

None. Always live data.

## Examples

```sh
brew-hop-search -V        # quick version
brew-hop-search -VV       # full diagnostic
```
