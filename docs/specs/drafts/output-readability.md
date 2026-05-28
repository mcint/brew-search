# output-readability

A design-space audit of `bhs`'s output modes, the tradeoffs each
makes, and where an interactive viewer would slot in. Written so
future tools (downstream consumers, sibling projects, future
contributors) can make intentional choices instead of inheriting
defaults by accident.

## Status

**Draft** — exploratory. No implementation in this spec; the
output is the spec itself: tradeoffs surfaced, decisions named,
follow-up beads filed for the concrete pieces worth building.

## Purpose

User feedback (2026-05-28): cutoff URLs in `--table` mean you can't
click them — you have to re-query. Cutoff descriptions cost
context. But unconstrained widths blow the terminal. What's the
right answer?

The honest answer is "it depends on what you're using `bhs` *for*."
Different use cases want different tradeoffs. The current surface
has implicit answers for each; this spec makes them explicit and
flags the gaps.

## Use cases (and what they need)

| Use case | What the user is doing | What it needs |
|----------|------------------------|---------------|
| **Quick discovery** | "Does `bhs python` find what I expect?" | One screen, key fields visible, scan-friendly |
| **Pipe composition** | `bhs -q python \| fzf`, `bhs --json \| jq …` | Stable bare/structured output; no decoration |
| **Install-decision** | "Which `python@*` should I install?" | URLs clickable, descriptions readable, version visible together |
| **Audit / bulk-read** | "Show me every installed cask that hasn't been updated in 90d" | All rows visible, sortable, exportable |
| **Triage** | "What's outdated? What can I safely upgrade?" | Version delta clear, source/cask distinguished |
| **Exploration** | "I don't know what I'm looking for. Browse." | Interactive narrowing, preview pane, multi-select |
| **Scripting** | A shell script consumes `bhs` results | Stable contract: column order, escaping, exit codes |

## Output modes today

| Mode | Strength | Weakness | Best for |
|------|----------|----------|----------|
| **Default (level 1)** | Section headers; aligned-ish; install hint inline | Truncates descriptions for compactness, no URL truncation safety | Quick discovery |
| **`-q` / quiet** | Bare names, no chrome | No fields beyond name | Pipe to `fzf`/`grep` |
| **`-v` / `-vv`** | Source indicator + cache age; per-table stats at `-vv` | More vertical noise | Diagnosing why results look weird |
| **`-T` / `--table`** | Header + aligned columns + caps (`desc` ≤50, `homepage` ≤40) | **URL cutoff with `…`** — the visceral pain point. No color today. | Audit/bulk-read on wide terminal |
| **`--json`** | Full structure, jq-able | Verbose; needs `jq` for casual read | Scripting |
| **`--csv` / `--tsv`** | qsv-friendly, plain | Loses nesting | Bulk export to spreadsheets/databases |
| **`--sql`** | `sqlite3` direct ingest | Specialist tool | Loading bhs results into another DB |
| **`-g` / `--grep`** | Tab-separated, headerless | No type info | `cut -f`, `awk`, simple pipes |
| **`--multi` / `--long`** | One block per result, labeled fields | Long output, vertical scroll | Reading detailed records on a narrow terminal |

## The tradeoff space

Every mode picks a stance on five axes. Most pain comes from a mode
having to pick *one* answer per axis when the user wanted a
different one this time:

### Axis 1 — Width: fit to terminal vs preserve content

- **Fit**: cap columns, truncate with `…`, sacrifice URL/description
  completeness. Wins when terminal is narrow.
- **Preserve**: emit full content, accept horizontal scroll or
  reflow. Wins when content matters (URLs, long names).
- *Current:* `--table` fits, default fits (description capped),
  `--json`/`--csv` preserve, `--multi` preserves with per-field
  vertical layout.
- *Gap:* no "fit + don't truncate URLs" mode. URLs are anchor data
  for the install-decision use case; truncating them is the wrong
  default for that case.

### Axis 2 — Decoration: color vs plain

- **Decorate**: ANSI for scanning. Wins on TTY.
- **Plain**: no ANSI for parsing. Wins in pipes.
- *Current:* default + `--multi` decorate; `-T`/`--csv`/`-g`/`--json`
  plain regardless of TTY.
- *Gap:* `--table` is plain even on TTY — the user wants color.
  Tracked in [format-color](format-color.md) (Option A there).

### Axis 3 — Density: per-row vs multi-line-per-row

- **Per-row**: one line per result. Wins on count visibility.
- **Multi-line**: labeled fields, blank-line separator. Wins on
  readability per record.
- *Current:* every mode except `--multi` is per-row.
- *Gap:* none significant; `--multi` covers the "per-record
  readability" case.

### Axis 4 — Interactivity: render-and-exit vs render-and-stay

- **Exit**: stdout, command returns, shell prompt back. Wins on
  composability.
- **Stay**: viewer (`less`, fzf, custom TUI) that lets the user
  filter / select / scroll. Wins on exploration and bulk
  multi-select.
- *Current:* every mode exits.
- *Gap:* no stay-mode. `bhs python | fzf` is the workaround for the
  filter-and-select case; doesn't help with preview pane or
  width-fluid rendering.

### Axis 5 — Statefulness: stateless query vs stateful session

- **Stateless**: each invocation is a fresh query. The cache is the
  only state. Wins on simplicity.
- **Stateful**: track what the user has been looking at; offer
  multi-select that survives across commands; build a queue of
  packages to install.
- *Current:* fully stateless.
- *Gap:* the install-manager direction (the user mentioned
  "aptitude-like") would need state — selection queue, last
  search, etc. Aggressively out of scope for v1; named here as a
  marker.

## Where the URL-cutoff pain lives

It lives in the `--table` mode's "fit" stance combined with "URL is
just another text column." Two ways to fix without rewriting:

### Option A — different caps per column kind

`--table` caps `description` at 50 and `homepage` at 40 today. URL
caps could be smarter:

- If terminal width allows, never truncate URL columns. Truncate
  description first.
- If URL truncation is unavoidable, emit the path-prefix half
  (`https://github.com/`) and let the rest get `…` — at least the
  domain stays.
- Print full URLs on a separate trailing line per row when
  truncated (`--table --urls-full`).

### Option B — drop the URL column entirely; use OSC 8 hyperlinks

Wrap the *name* column in OSC 8 escape (`\033]8;;URL\007name\033]8;;\007`).
Modern terminals (iTerm2, Kitty, recent Terminal.app, Alacritty)
render that as a clickable name with no visible URL.

Pros: zero width cost, name *is* clickable.
Cons: non-OSC-8 terminals see the escape codes as noise — need to
detect (`TERM_PROGRAM`, `WT_SESSION`, etc.) and degrade
gracefully. `tmux` doesn't pass OSC 8 by default. Less / pagers
mostly do not.

### Option C — interactive viewer (`-I` / `--interactive`)

Launch a stay-mode reader (`less -S`, or a curses-based mini-TUI)
that handles width with side-scroll and shows the focused row's
full record below. Then the URL is always reachable — focus the
row, the URL appears in a preview panel.

Pros: solves URL-cutoff *and* the exploration/multi-select use
case in one move.
Cons: bigger build. New dependency (curses is stdlib; `urwid` /
`textual` is more). Stateful interaction model needs design.

## Interactive view — what would it look like?

Sketching enough to capture intent; not a build spec.

### Variant 1 — `less -S` invocation

`bhs -I python` pipes the default output into `less -S`
(side-scroll on). The user `←/→`s through wide rows. Zero new code;
shells out.

```
  python  3.13.2  Interpreted, interactive…  │ https://www.python.org/
  pyenv   2.4.0   Python version management…│ https://github.com/pyenv/pyenv
  …
                                           [colon prompt — less is running]
```

Pros: shipped tomorrow. Familiar UX (everyone knows `less`).
Cons: no preview pane; no multi-select; row-truncation still
happens, you just scroll past it.

### Variant 2 — fzf-style picker

Launch `fzf` (or our own equivalent) with our results as the input.
User narrows by typing; preview pane shows the focused row's full
record.

```
  > python                                          (typing filter)
  ▸ ● python@3.13   3.13.2  …                       (1 of 8)
    python-build    1.4.2   …
    python-argc…    3.6.3   …
                                                    ───
                                                    name:        python@3.13
                                                    version:     3.13.2
                                                    desc:        Interpreted, interactive…
                                                    homepage:    https://www.python.org/
                                                    installed:   yes (3.13.2)
                                                    tap:         homebrew/core
                                                    bottle:      arm64_sequoia
```

Pros: solves URL/desc visibility entirely (in preview pane). Adds
discovery via fuzzy-filter on the result set. Hooks naturally into
multi-select (tab to mark, enter to confirm).

Cons: depends on `fzf` being installed; or we write our own
narrow renderer. Multi-select implies state for "what do I do with
the selection?" → leads to install-manager territory.

### Variant 3 — curses TUI

Bespoke renderer. Same shape as fzf-mode but bundled.

Pros: no external dep. Full control.
Cons: build cost. Maintenance.

## Recommendation

Three slices, ordered by cost vs. impact:

1. **Now (zero new TUI work):**
   - [format-color](format-color.md) Option A for `--table`. Done in
     parallel.
   - Smart URL-cap rules in `--table`: never truncate URLs when
     room remains; truncate description first. Trailing
     `--urls-full` flag for the "give me the full URLs on their own
     lines" mode.
   - OSC 8 hyperlink wrapping in default output when
     `TERM_PROGRAM` ∈ {iTerm.app, WezTerm, Kitty, Alacritty, …}.
     Conservative allowlist; `BREW_HOP_SEARCH_NO_OSC8=1` opt-out.
2. **Next slice (interactive, lightweight):**
   - `bhs -I python` → pipe to `less -S` automatically when stdout
     is a TTY. No new dep.
   - Document `bhs python | fzf --preview 'bhs --json {1} | jq'` as
     the supported recipe for fuzzy-pick.
3. **Later (out of scope for this spec):**
   - Bespoke TUI / fzf-clone with preview pane and multi-select.
     Pulls in install-manager territory; needs its own spec.

## Cross-references

- [format-color](format-color.md): the color side of the same audit;
  this spec leans on its `--color=auto|always|never` precedence
  rules.
- [installed-indicator](installed-indicator.md): the `●`/`○` glyphs
  add a leading column to the same `--table` discussion; the
  width-budget math here has to include it.
- [cli-vocabulary](cli-vocabulary.md): `-I` / `--interactive` is a
  proposed new adverb; under that spec's lowercase-is-adverb rule
  it should be lowercase (`-i` is taken by `--installed`, so
  probably `-I` uppercase under the spec's "verbs-and-special-modes
  are uppercase" rule, with a long form `--interactive`).
- claude-collab seed:
  `~/dev-llm/claude-collab/cli-ux/cli-grammar.md` (use cases ↔
  parts-of-speech mapping).

## Open questions

- **OSC 8 detection allowlist** — empirical. Probably:
  `TERM_PROGRAM ∈ {iTerm.app, WezTerm, Kitty, vscode}` + `TERM
  startsWith alacritty`. Plus `BREW_HOP_SEARCH_FORCE_OSC8=1` for
  power users.
- **`-I` semantics inside a pipe** — does `bhs -I python | grep …`
  even make sense? Probably error or fall back to non-interactive.
- **Smart URL caps math** — how do we decide what's "URL-shaped"?
  `starts with http(s)://` is the obvious heuristic; covers
  homepages but not all formula `urls.stable`.
- **Multi-select interactive → what then?** Print the selected
  names? Pipe to `brew install`? `bhs install` subcommand
  (per [cli-vocabulary](cli-vocabulary.md))? Defer to that spec.

## Spec status

**Drafted:** use-case map, current-mode tradeoff table,
five-axis design space, URL-cutoff options (A/B/C), interactive
viewer variants (1/2/3), three-slice recommendation.

**Open until implementation:** OSC 8 allowlist; `-I` letter choice
(collides with `-i` installed); whether the lightweight slice
needs its own bead or rides along with [format-color](format-color.md).

**Beads to file:** smart URL caps in `--table`; OSC 8 hyperlinks
in default output; `bhs -I` `less -S` shim; install-manager /
multi-select TUI exploration (long-horizon).
