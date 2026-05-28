# format-color

Color policy for the special output formats — `--table`, `--csv`,
`--tsv`, `--sql`, `--json`, `-g`/`--grep`, `--multi` / `--long` —
so that the table mode in particular is colorized by default
(better pitch to new users, easier to scan), while still respecting
`NO_COLOR`, `FORCE_COLOR`, and pipe detection.

## Status

**Draft** — not yet implemented. Touches `display.py` color
detection and each format renderer. Pairs with
[installed-indicator](installed-indicator.md) which depends on the
table indicator-column colorization.

## Purpose

Today, `--table` and the other format outputs render plain ASCII
even on a TTY. The default `level 1` search output uses color (green
names, yellow versions, dim homepages) — so users who switch to
`-T` for "let me see the whole row aligned" *lose* the visual
scanning aid. Goal: keep color on by default for these formats too,
gated by the same rules as the default output.

## Design

### What gets colored, by format

| Format | Default color? | What gets color |
|--------|----------------|-----------------|
| `--table` (`-T`) | **yes** | header row (bold), `Inst` indicator column (per [installed-indicator](installed-indicator.md)), source column (`f`/`c`/`t`/`i` per source). Cell values uncolored to keep alignment math simple. |
| `--csv` | **no** (default), opt-in via `--color` | CSV is a data contract; ANSI breaks parsers. Opt-in via `--color` for human-eyeballed CSVs. |
| `--tsv` | **no** (default), opt-in | Same reasoning as CSV. |
| `--sql` | **no** (default), opt-in | SQL output is meant to be fed back into `sqlite3`; ANSI would break it. |
| `--json` | **no** (default), opt-in via `--color` (and we use compact ANSI only on top-level key=value rendering, not inside string values) | Matches `gh`, `jq` defaults — JSON output stays parseable. |
| `--multi` / `--long` | **yes** | Same color rules as default level-1 output. |
| `-g` / `--grep` | **no** | Grep mode is bare by definition. |

The split is: *human-readable* formats (`--table`, `--multi`) get
color by default; *machine-readable* formats (`--csv`, `--tsv`,
`--sql`, `--json`, `-g`) stay plain and require explicit opt-in.

### Color decision rule

The same rule applies to every format that defaults-color:

```
color_on = (
    not NO_COLOR_set
    and not BREW_HOP_SEARCH_PLAIN_set
    and (FORCE_COLOR_set or sys.stdout.isatty())
)
```

Order of precedence (highest wins):

1. **`NO_COLOR=1`** — universal kill switch. [no-color.org](https://no-color.org/).
   Applies to every format and every flag.
2. **`BREW_HOP_SEARCH_PLAIN=1`** — project-scoped kill switch (for
   "I like color in `ls` but not here").
3. **Explicit `--color=auto|always|never`** — flag override. `auto`
   is the table above; `always` forces on; `never` forces off.
4. **`FORCE_COLOR=1`** — forces on regardless of TTY detection
   (matches Node ecosystem convention).
5. **`isatty(stdout)`** — auto-detection. Off when piped.

`auto` is the default. `always` ≈ `FORCE_COLOR=1` scoped to one
invocation. `never` ≈ `NO_COLOR=1` scoped to one invocation.

### Why TTY detection on *stdout* (not stderr)

Format output goes to stdout. The decision "should this string be
colored?" tracks where the string lands. `# [cache] …` / `# [time]
…` go to stderr and check `isatty(stderr)` separately (existing
behavior).

### `--color` flag

New flag, single argument:

```
--color=auto      # default; per the rule above
--color=always    # color on, even when piped (good for `bhs … | less -R`)
--color=never     # color off, even on TTY (good for capturing to a log)
--color           # bare form == --color=always
```

Long-form only; no short alias. Matches `git`, `ls`, `grep`.

### Pipe-detection edge cases

| Invocation | TTY(stdout)? | `auto` resolves to |
|-----------|---------------|--------------------|
| `bhs -T python` | yes | color on |
| `bhs -T python \| less` | no | color off |
| `bhs -T python \| less -R` (user wants color through pager) | no | color off by auto; user passes `--color=always` |
| `bhs -T python > out.txt` | no | color off |
| `bhs -T python --color=always > out.txt` | no | color on (ANSI in file) |
| `FORCE_COLOR=1 bhs -T python \| cat` | no | color on |
| `NO_COLOR=1 bhs -T python` | yes | color off |

Matches `git --color=auto` semantics so muscle memory carries over.

### Interaction with existing default-output color

The default (level-1, non-format) output already colors. This spec
doesn't change that path — it just adds color to the format paths
that were plain. Same env vars, same `--color` flag govern both.

The current implementation has two module-level flags (`USE_COLOR`,
`USE_COLOR_STDERR`) computed at import time. To honor `--color`,
those become *resolved at startup* from a single function that
takes the parsed args + env into account, then both `display.py`
and the format renderers consult the resolved value.

## Examples

```
$ bhs -T python                    # TTY: colored table by default
  I  S  Name           Ver     Description
  -- -- -------------- ------- -----------
  ●  f  python@3.13    3.13.2  Interpreted, interactive, …
     f  python-build   1.4.2   Simple, correct PEP 517 …

$ bhs -T python | less -R --color=always
                                    # color preserved through pager

$ bhs -T python > out.txt          # auto: color off, file is plain

$ bhs --csv python                  # CSV stays plain (machine-readable)
source,name,version,description,homepage
formula,python@3.13,3.13.2,"Interpreted, interactive, …",https://www.python.org/

$ bhs --csv --color=always python   # opt-in: ANSI in CSV (human eyeballing)
formula,python@3.13,…  ← colored

$ NO_COLOR=1 bhs -T python          # universal kill
  I  S  Name           Ver     Description
  -- -- -------------- ------- -----------
  *  f  python@3.13    3.13.2  Interpreted, …
```

## Open questions

- **Header row coloring in `--table`** — bold? underlined? both?
  Choose at implementation; bold matches `comfy-table` default and
  `column -t` users' expectations.
- **`--json` pretty mode** — `jq`-style colorized JSON when
  `--color=always` is requested. Defer until someone asks; the
  `gh`/`jq` precedent is "you pipe through `jq -C` for that."
- **Pager auto-detect** — should we detect `PAGER` env / `less`
  ancestor and force color on by default? Probably not — pager
  configs vary too much. Document `--color=always` as the answer
  and move on.

## Implementation notes

- New `display.resolve_color(args, env) -> (bool, bool)` returning
  `(stdout_color, stderr_color)`. Called once at start of `main()`,
  mutates `USE_COLOR` / `USE_COLOR_STDERR`.
- Add `--color` to argparse with `nargs='?'`, `const='always'`,
  `default='auto'`, choices `[auto, always, never]`.
- Each format renderer that opted into default-color (`--table`,
  `--multi`) takes color decisions from `USE_COLOR`.
- Tests:
  - `--table` with TTY-mock → ANSI present.
  - `--table` piped (TTY-mock-false) → no ANSI.
  - `--csv` always plain at default; `--csv --color=always` → ANSI present.
  - `NO_COLOR=1 --color=always` → still plain (universal kill wins).
  - `FORCE_COLOR=1` piped → ANSI present.

## Spec status

**Drafted:** per-format color defaults, precedence rules,
`--color` flag, pipe-detection matrix.

**Open until implementation:** header-row style in `--table` (bold
vs underline), `--json` pretty-color behavior. Both have safe
defaults in the spec; pin during code review.
