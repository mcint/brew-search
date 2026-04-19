# `--man` / `--help=man` flag (draft)

## Purpose
Let users view the full man page from the CLI itself without needing a
correctly-configured MANPATH. `brew-hop-search --man` should Just Work on any
install path — `pip install`, `uv tool install`, Homebrew — regardless of
whether the shell has been set up to find the packaged `.1` file.

## Status
**Draft** — not yet implemented.

## Motivation

The man page (`docs/brew-hop-search.1.md`) is the canonical long-form
reference. Today it's reachable only if:

- Homebrew installed it *and* the user's shell has Homebrew's `MANPATH` wired
  up. Many users don't.
- `pip install` / `uv tool install` do not install man pages by default —
  there's no standard location for Python packages to drop one.
- Users who clone the repo can `man -l docs/brew-hop-search.1.md` (if they
  have `pandoc`-rendered `.1`), but that's not a production path.

Net effect: the man page exists but nobody reads it. A built-in flag fixes
that without requiring shell config.

## Surface

Two equivalent invocations:

```
brew-hop-search --man          # canonical
brew-hop-search --help=man     # alt spelling, if --help grows other modes
```

Start with `--man` alone; `--help=MODE` is a future extension.

Behavior:
- Loads the packaged man-page source.
- If `man` is available on PATH *and* a rendered `.1` file is shipped, runs
  `man -l <path>` (best rendering, respects user's pager + width).
- Else, prints the markdown source through `$PAGER` (default `less -R`) if
  stdout is a TTY, else to stdout raw.
- Exits after rendering.

## Design

### Packaging

Ship the man page *inside* the Python package so it's installable everywhere:

```
src/brew_hop_search/
├── cli.py
├── ...
└── data/
    ├── brew-hop-search.1        # groff (rendered)
    └── brew-hop-search.1.md     # markdown source (fallback)
```

`pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel.shared-data]
"src/brew_hop_search/data/brew-hop-search.1" = "share/man/man1/brew-hop-search.1"

[tool.hatch.build]
include = ["src/brew_hop_search/data/*"]
```

`shared-data` drops the `.1` into `{prefix}/share/man/man1/` at install time —
which Homebrew *does* pick up automatically for brews. For `pip` / `uv tool`,
`share/man/...` isn't in MANPATH by default; `--man` is the escape hatch.

### Rendering

`docs/brew-hop-search.1.md` is already written in a readable markdown that
approximates man-page structure. To ship a groff `.1`:

- Add a build step (`scripts/build-man.sh`) that runs `pandoc -s -t man` on
  the markdown. Run it from `scripts/release.sh` so the rendered file stays
  in sync. `pandoc` is a build-time dep, not a runtime one.
- If `pandoc` is not available at build, fall back to shipping the `.md` only
  and `--man` renders the markdown.

### Discovery at runtime

```python
from importlib.resources import files

def _man_paths():
    data = files("brew_hop_search").joinpath("data")
    groff = data.joinpath("brew-hop-search.1")
    md    = data.joinpath("brew-hop-search.1.md")
    return (groff if groff.is_file() else None,
            md    if md.is_file() else None)
```

### Pager

Respect `$PAGER`; default to `less -R` (ANSI) for markdown, plain `less` for
groff (via `man -l`). Respect `$MANPAGER` over `$PAGER` when rendering groff.

If stdout is not a TTY (`--man | grep ...`), skip the pager and print raw.

## Non-goals

- **No** re-implementing a markdown-to-groff converter at runtime. Either we
  shipped the rendered `.1` at build or we show the `.md`.
- **No** runtime dependency on `pandoc`. Build-time only.
- **No** competing with `--help`. `--help` stays the short reference;
  `--man` is the long form.

## Open questions

- Should `--help=man` be wired now, or wait until `--help` grows other modes
  (e.g. `--help=examples`)? Lean: add the alias now so `--help=man` can be
  documented alongside `--man` and users don't have to remember which is
  canonical.
- When both rendered `.1` and `.md` exist, prefer `.1` always? Or honor a
  `--man=md` escape for debugging? Lean: prefer `.1`; no escape until asked.
- On Windows / systems without `man`: fall back to printing the markdown.
  That's already the fallback path, so no extra logic needed.

## Rollout

1. Add `[tool.hatch.build]` + `data/` layout; copy the existing `.md` in.
2. Add `scripts/build-man.sh` (pandoc) + wire into `release.sh`.
3. Implement `--man` flag + discovery/pager logic.
4. Add `--help=man` alias.
5. README: one-line note under Usage ("offline reference: `brew-hop-search
   --man`"). Remove any "set MANPATH to..." suggestions.
