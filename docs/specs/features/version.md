# version

Show tool identity, build info, install source, and update status.

## Purpose

Quick version check (`-V`) and detailed diagnostic info (`-VV`). The output
varies by install source so local dev gets a reproducibility marker while
clean installs stay uncluttered.

## Input

- **flag**: `-V` / `--version` (stackable: `-VV`)

No query, no source flags.

## Install source

Detected at runtime:

| Source    | Detection                                                           |
|-----------|---------------------------------------------------------------------|
| `local`   | `git rev-parse --is-inside-work-tree` succeeds at the package dir   |
| `brew`    | Package path contains `/Cellar/` or `/linuxbrew/`                   |
| `pypi`    | Package path contains `site-packages` (covers `pip`/`uv tool`/venv) |
| `unknown` | None of the above                                                   |

## Output

### Short (`-V`)

Between releases (dev tree, `uv run` from the working copy):

```
brew-hop-search 0.3.7-dev+31
```

Between releases (built wheel that's ahead of the last tag):

```
brew-hop-search 0.3.7+31
```

At a release commit or from a release install:

```
brew-hop-search 0.3.7
```

`-V` prints `version_info()`, which is `__version__` (= the VERSION file
content) decorated with a commit-count suffix:

- `X.Y.Z-dev+N` — live working tree (the `-dev` marks "not built / not
  shipped"); N = commits since the last tag.
- `X.Y.Z+N` — built wheel between tags (the `-dev` is dropped because
  the artifact exists, "could ship"); N from `BUILD_COMMIT_COUNT`
  baked into `_build_info.py`.
- `X.Y.Z` — on a tagged commit, or when N == 0.

The `+N` is a PEP 440 *local version label*. `packaging.Version`
sorts `0.3.7-dev+31 < 0.3.7 < 0.3.7+5 < 0.3.7.post0 < 0.3.8.dev0`,
matching the natural reading. PyPI strips the local label on upload,
so tagged releases reach PyPI as plain `0.3.7`.

`__version__` itself stays the raw VERSION file content (one string,
one file). `version_info()` is the *displayed* version — used in `-V`,
`-VV`, and User-Agent.

### Detailed (`-VV`)

Same first line as `-V`; adds an `install` field and the rest of the
diagnostic card:

```
brew-hop-search 0.3.7-dev+31
  version     0.3.7-dev+31
  commit      8a8b6d0
  install     local
  user-agent  brew-hop-search/0.3.7-dev+31
  pypi        https://pypi.org/project/brew-hop-search/
  github      https://github.com/mcint/brew-hop-search

recent commits
  8a8b6d0 Draft specs: cli-vocabulary, output-readability
  ...

pypi  up to date (0.3.6)
```

Shows:
- Version, commit hash, install source, user-agent
- Project URLs (PyPI, GitHub, brew tap when available)
- Recent git commit log (10 entries, when a git dir is reachable)
- Live PyPI version check (update available / up to date)

## Identity Fields

| Field | Source |
|-------|--------|
| `version` | `version_info()` — `__version__` + commit-count suffix |
| `commit` | `git rev-parse --short HEAD`; falls back to baked `BUILD_COMMIT` on wheels |
| `commit count` | `git rev-list --count <last-tag>..HEAD`; falls back to baked `BUILD_COMMIT_COUNT` |
| `install` | `install_source()` in `__init__.py` |
| `user-agent` | `user_agent()` — env var > config > `brew-hop-search/{version_info()}` |
| `pypi` / `github` / `tap` | Hardcoded URL constants |

## User-Agent Configuration

Priority:
1. `BREW_HOP_SEARCH_UA` environment variable
2. `user_agent` key in `~/.config/brew-hop-search/config.toml`
3. Default: `brew-hop-search/{version}`

Used in all HTTP requests (API fetch, PyPI version check).

## Data Sources

- Local: git subprocess for commit hash, dirty flag, and log
- Network: PyPI JSON API for update check (only at `-VV`)

## Cache Behavior

None. Always live data.

## Testing

Snapshot tests in `tests/snapshots/` cover help/output formats; `-V` /
`-VV` are exercised via the `_VERSION_RE` mask in `tests/test_cli.py::run`
so commit hashes and version numbers don't churn snapshots. When
user-facing output changes, update with `UPDATE_SNAPSHOTS=1 make test` and
review the diff before committing.

## Examples

```sh
brew-hop-search -V        # quick version (dev marker on dev builds)
brew-hop-search -VV       # full diagnostic incl. install source
```

---

## Release versioning scheme

How the repo tracks version between releases — not a runtime feature, but
relevant to how `__version__` and wheel metadata get their values.

### Single source of truth

`src/brew_hop_search/VERSION` is the only file storing the version.
Hatch's `[tool.hatch.version] source = "regex"` reads it at build time;
`__init__.py` reads the same file at import time. No second copy in
`pyproject.toml` to drift out of sync.

### Between releases: the `-dev` suffix

After publishing a release, `bump-version.sh --dev` writes `X.Y.(Z+1)-dev`
to VERSION and commits it. The `-dev` marker is the dev-state invariant:
it's right there in the file, survives across checkouts, and makes it
impossible to accidentally produce a build that collides with the
released version — the suffix is already baked in. No git introspection,
no computed devN, no hash appendage. What you see in VERSION is what `-V`
prints.

### Release promotion

`release.sh` auto-detects `X.Y.Z-dev` in VERSION, runs
`bump-version.sh --release` to strip the suffix, commits the promotion as
`Promote to release vX.Y.Z`, and tags. Tags always land on plain release
versions, never `-dev`.

### Resolution table

| Context                            | `VERSION`     | `__version__` | `version_info()` |
|------------------------------------|---------------|---------------|------------------|
| Between releases (dev tree)        | `0.3.7-dev`   | `0.3.7-dev`   | `0.3.7-dev+31`   |
| Between releases (built wheel)     | `0.3.7-dev`   | `0.3.7-dev`   | `0.3.7+31`       |
| Release commit / tag (any install) | `0.3.7`       | `0.3.7`       | `0.3.7`          |

`__version__` is one string from one file. `version_info()` is the
*displayed* version, decorated with a commit-count suffix when there
are commits since the last tag. The "-dev" → "(no suffix)" promotion
on built wheels is what carries the "built / could ship" vs "live /
not built" distinction in the rendered string.

### Commands

```sh
make bump                # X.Y.Z → X.Y.(Z+1)  (release form)
./scripts/bump-version.sh --dev      # X.Y.Z → X.Y.(Z+1)-dev
./scripts/bump-version.sh --release  # X.Y.Z-dev → X.Y.Z (no-op otherwise)
make version             # print current VERSION
```
