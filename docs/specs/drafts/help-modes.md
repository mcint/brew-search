# Help modes: `-h` / `--help[=MODE]` / `--man` (draft)

## Purpose
Make `-h` ≠ `--help`, promote `--man` as a first-class flag (not hidden inside
`--help=…`), and let both help flags accept `=MODE` for man page + scoped
section help — no MANPATH wiring needed.

## Design

### Two levels of general help

| Flag       | Output                                                                |
|------------|-----------------------------------------------------------------------|
| `-h`       | Terse: usage line + 2-line hint (`--help`, `--man`). Fits small TTYs. |
| `--help`   | Full argparse help (current behavior).                                |
| `--man`    | Full man page via `$PAGER`. First-class flag; discoverable.           |

`-h` tail:

```
  --help        full options
  --man         offline man page (or: --help=man)
```

### `=MODE` on both help flags

`-h=MODE` and `--help=MODE` are equivalent:

| Mode        | Shows                                                              |
|-------------|--------------------------------------------------------------------|
| *(none)*    | terse (`-h`) or full (`--help`).                                   |
| `man`       | equivalent to `--man`.                                             |
| flag letter / name (`-f`, `cask`, `outdated`, …) | scoped to that flag: purpose, examples, related. |
| section (`sources`, `output`, `cache`, `info`) | scoped to an argparse group. |

Resolution: flag letter → flag long name → section name → error with
`did-you-mean`.

`--man` stays the canonical way to get the man page; `--help=man` is a
convenience for users already in the `--help=…` habit.

### Scoped help lives next to the code

Help text for each flag is a module-level dict keyed by section/flag, tested
via the same snapshot mechanism the doc-as-test work establishes:

```python
HELP = {
    "outdated": """\
-O / --outdated — detect packages where installed version != current.

  brew-hop-search -O                 # fast local comparison
  brew-hop-search -O -c              # casks only
  brew-hop-search -O --brew-verify   # diff vs brew's authoritative result

See also: -H (version history), --help=cache.
""",
    ...
}
```

Argparse's `help=` stays the one-liner; `HELP[...]` is the long form. Keeping
it declarative + colocated makes it observable at the CLI *and* testable
alongside other snapshots.

### Man page: packaging + rendering

Ship the man page inside the wheel so `--man` works from any install path:

```
src/brew_hop_search/data/
├── brew-hop-search.1        # groff, rendered at build from the .md via pandoc
└── brew-hop-search.1.md     # source, used when .1 is absent
```

`pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel.shared-data]
"src/brew_hop_search/data/brew-hop-search.1" = "share/man/man1/brew-hop-search.1"
```

`shared-data` also places the `.1` at `{prefix}/share/man/man1/` so Homebrew
picks it up automatically for users with MANPATH configured; `--man` is for
everyone else.

Runtime lookup:

```python
from importlib.resources import files

def _man_paths():
    data = files("brew_hop_search").joinpath("data")
    groff = data.joinpath("brew-hop-search.1")
    md    = data.joinpath("brew-hop-search.1.md")
    return (groff if groff.is_file() else None,
            md    if md.is_file() else None)
```

Rendering order:

1. If `man` on PATH and `.1` exists: `man -l <path>` (best).
2. Else pipe `.md` through `$MANPAGER` / `$PAGER` / `less -R` if TTY.
3. Not a TTY: raw to stdout.

Build: `scripts/build-man.sh` runs `pandoc -s -t man`, called from
`release.sh`. `pandoc` is a build-time dep only.

## Examples

```sh
brew-hop-search -h                 # terse usage + pointer to --help / --man
brew-hop-search --help             # full options
brew-hop-search --man              # man page (canonical)
brew-hop-search -h=man             # same
brew-hop-search --help=-c          # casks flag detail
brew-hop-search --help=cache       # everything under the cache group
brew-hop-search -h=outdated        # outdated mode detail
```

## Future

Per-flag `HELP[...]` blocks become the substrate for generating
`docs/specs/features/*.md` (or the reverse): spec and CLI stay in lockstep
instead of drifting. A doc-as-test check verifies the `HELP[k]` snapshot
matches the spec section so neither can edit without the other noticing.
