# installed-indicator

A leading column on search results that shows whether each row is
*currently installed*, *previously installed* (per history), or
neither.

## Status

**Draft** — not yet implemented. Touches `search.md` output, the
`-v` source-indicator column, and the `history.md` data we already
collect.

## Purpose

Today, when `bhs python` returns 20 rows, the user has to remember
which they have installed or re-run `bhs -i python`. The installed
state is information we *already have* in `installed_formula` /
`installed_cask`. Surfacing it inline on the default search makes
"what's on this machine vs what's out there" answerable in one pass.

Past-installed (uninstalled-but-touched) is the same data shape from
`history.md` — if we have the row, we can mark it.

## Output

### Indicator vocabulary

| Char | Meaning |
|------|---------|
| `●` (or `*` on no-unicode) | currently installed |
| `○` (or `.` on no-unicode) | previously installed, not now (history-only) |
| `·` (or space) | never installed, or no history record |

`●` colored green on TTY, `○` dim. `·` is just a space-equivalent at
default verbosity; at `-v` it's rendered as a literal `·` (dim) so
columns line up consistently.

Rendering of the past-installed mark is *conditional on history
data*. If `history.md`'s tables don't exist or are empty for this
machine, the `○` indicator never appears and the column collapses
back to "installed or not".

### Verbosity ladder

| Level | Flag | Indicator column behavior |
|-------|------|---------------------------|
| 0 | `-q` / pipe | **Absent.** Quiet output is bare names + fields; no leading column. (Composability with `grep`/`fzf` — adding chars to leading position breaks naïve `cut -f1` use.) |
| 1 | *default* | **Present, two-state.** Either `●` (installed) or blank. No past-installed mark. Single-char width — does not affect alignment. |
| 2 | `-v` | **Present, three-state.** `●` / `○` / `·` (the dot is rendered). Combined with the existing source indicator: `●f python  3.13.2 …`. |
| 3 | `-vv` | **Present, three-state, plus version-delta hint.** When installed version differs from the API/index version (i.e. this row is outdated), suffix the version cell with `(↑3.13.2 → 3.13.3)`. |

`-v` already adds a one-char source column (`f`/`c`/`t`/`i`). The
installed indicator is a *separate* one-char column **to the left of
that**. Two adjacent narrow columns is intentional: each axis is
orthogonal (installed-state ⊥ source-kind), and putting them in one
combined glyph would lose info.

### Default (level 1) layout

```
  # formulae (3/8307)  • brew install python@3.13
  ● python@3.13           3.13.2  Interpreted, interactive, object-oriented programming language  │ https://www.python.org/
    python-build          1.4.2   Simple, correct PEP 517 build frontend  │ https://github.com/pypa/build
    python-argcomplete    3.6.3   Tab completion for Python argparse  │ https://kislyuk.github.io/argcomplete/

  # casks (2/7589)  • brew install --cask anaconda
    anaconda  2025.12  Distribution of Python and R for scientific computing  │ https://www.anaconda.com/
  ● pycharm   2025.1   IDE for Python  │ https://www.jetbrains.com/pycharm/
```

The first column is one character (the `●` or a space). Subsequent
columns shift right by one position. Rows for installed packages
gain the green dot; un-installed rows are visually identical to
today's output except for the one leading space.

### `-v` (level 2) layout

```
  -- cache: 2h old   searching formula + cask

  # formulae (3/8307)  • brew install python@3.13
  ● f python@3.13           3.13.2  Interpreted, interactive, object-oriented programming language  │ https://www.python.org/
  · f python-build          1.4.2   Simple, correct PEP 517 build frontend  │ https://github.com/pypa/build
  ○ f python-argcomplete    3.6.3   Tab completion for Python argparse  │ https://kislyuk.github.io/argcomplete/

  # casks (2/7589)  • brew install --cask anaconda
  · c anaconda  2025.12  Distribution of Python and R for scientific computing  │ https://www.anaconda.com/
  ● c pycharm   2025.1   IDE for Python  │ https://www.jetbrains.com/pycharm/
```

Two narrow columns: installed-state, then source-kind.

### `-vv` (level 3) layout

```
  ● f python@3.13           3.13.2 (↑3.13.2 → 3.13.3)  Interpreted, interactive …  │ https://www.python.org/
  · f python-build          1.4.2   …
```

`(↑old → new)` only appears when the installed version differs from
the searched-source version. Same data the `-O` outdated command
uses, just inline.

### Other formats

| Format | Behavior |
|--------|----------|
| `--json` | Add `"installed": true | false`, and `"previously_installed": true | false` when history exists. |
| `--csv` / `--tsv` | Add `installed` and `prev_installed` columns at position 0. `0`/`1` values. |
| `--table` (`-T`) | Add `Inst` column at position 0 (header `I`). `●` / `○` / blank. Colored per the [format-color](format-color.md) spec. |
| `--sql` | Add `installed`, `prev_installed` columns to the generated CREATE TABLE. |
| `--multi` / `--long` | Inline `installed: yes`, `previously_installed: <date>` lines in the per-row block. |
| `-g` / `--grep` | **No change.** Greppable mode stays bare; the user wanted a `cut`-able pipeline. |

### Color

- `●` — `green` on TTY; plain `*` if `NO_COLOR=1` or
  `BREW_HOP_SEARCH_PLAIN=1`.
- `○` — `dim` on TTY; plain `.` in no-color mode.
- See [format-color](format-color.md) for the cross-format color
  policy.

## Data sources

The indicator pulls from two existing tables:

| State | Source |
|-------|--------|
| Currently installed (`●`) | `installed_formula.name` / `installed_cask.token` |
| Previously installed (`○`) | `install_history` table (see `history.md`) where the latest event is `uninstall` |

Both lookups are single `IN (…)` queries against the result page —
20 rows by default. Negligible cost (<2ms on warm cache).

When `installed_*` is missing (cold cache, never refreshed), the
indicator gracefully degrades: search runs, indicator column is
blank for every row, no error. A `-v` would surface
`# [time] … (installed cache absent)` so the user knows why.

## Configuration

| Flag / env | Effect |
|-----------|--------|
| `--no-installed-indicator` | Suppresses the column at all verbosity levels except for explicit `-v`/`-vv` (which the user opted into). |
| `BREW_HOP_SEARCH_INSTALLED_INDICATOR=0` | Same, persistent. |
| `--prev-installed` / `--no-prev-installed` | Force the past-installed glyph on or off independent of verbosity. |

Default: indicator **on** at level 1+, past-installed **off** at
level 1 / **on** at level 2+.

## Examples

```
$ bhs python
  # formulae (3/8307)
  ● python@3.13   3.13.2  …
    python-build  1.4.2   …
    python-argc…  3.6.3   …

$ bhs -q python | head -3
python@3.13  3.13.2  …
python-build  1.4.2  …
python-argcomplete  3.6.3  …
                    (quiet: no indicator column — composable)

$ bhs -v python
  -- cache: 2h old   searching formula + cask
  # formulae (3/8307)
  ● f python@3.13   3.13.2  …
  ○ f python-build  1.4.2   …   (installed Dec 2024, removed Mar 2026)
  · f python-argc…  3.6.3   …

$ NO_COLOR=1 bhs python
  # formulae (3/8307)
  * python@3.13   3.13.2  …
    python-build  1.4.2   …
```

## Open questions

- **Glyph set.** `●` / `○` are unambiguous but Unicode. Fallback to
  `*` / `.` on `LANG=C` / `LC_ALL=C` is the obvious move; we already
  do similar fallbacks for the cache-flow `✓` / `✗`.
- **Indicator on `-i`?** When source is `-i`, *every* row is
  installed by definition. The indicator is redundant. Suppress at
  level 1, keep at `-v`+ for orthogonality (`-v` is for diagnosing,
  not for terseness). Probably the right call but worth confirming.
- **Indicator on `-t`?** A formula in a tap can also be installed.
  Show the indicator — same logic as core formulae.
- **Past-installed retention.** Do we ever GC history rows? If a
  user installed `foo` in 2022 and uninstalled it, we'd still show
  `○` in 2026. Probably correct (it's *historical* by definition),
  but if `history.md` grows a TTL, this spec inherits it.

## Implementation notes

- New module function: `search.annotate_installed(rows, db) ->
  rows` — adds `installed`, `prev_installed` keys to each row dict
  via a single batched query.
- Render: a tiny helper in `display.py` that converts the two bools
  into the glyph (with color + no-color fallbacks).
- Tests:
  - Snapshot: default output with one row installed, one prev-installed,
    one never-installed.
  - `--json` shape: `installed` / `previously_installed` keys present.
  - `-q` output: no indicator column at all (regression test).
  - `NO_COLOR=1`: `*` / `.` ASCII fallback.
- Coordinate with [format-color](format-color.md) for the table-mode
  rendering.

## Spec status

**Drafted:** indicator vocabulary, verbosity ladder, format
behaviors, data-source plan, off-switches.

**Open until implementation:** glyph-set fallback rules under
non-UTF8 locales; whether `-i` should suppress the indicator at
level 1. Both have a default in the spec (fallback to ASCII; yes
suppress on `-i`) but the call sites need verification.
