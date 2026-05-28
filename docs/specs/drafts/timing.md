# timing

A compact one-line timing footer printed after every command, showing
what *the user felt* (foreground wall-clock) and, separately,
post-print work done in the background.

## Status

**Draft** — not yet implemented. Companion to
[cache-flow](../features/cache-flow.md), which already records bg
durations to `~/.cache/brew-hop-search/refresh.log` and prints a
trailing `# [cache] …` line. This spec extends that machinery to
*every* command and standardizes the packed-line format.

## Purpose

Make it easy to tell, at a glance, whether `bhs` was fast (cache hit,
sub-100ms) or doing real work (cold cache, brew subprocess, network
fetch). Caching is the whole product — the timing line is how we
*show* the cache earning its keep.

Two readings we want one line to support:

1. **Felt time** — how long the user waited before the shell came
   back. The headline number.
2. **Post-print work** — bg refresh / fetch that ran detached. Shown
   as a parenthetical delta because it didn't cost the user latency
   (post the 2026-05-28 grace-window change in cache-flow.md).

## Design

### Default format (compact, one line)

```
  # [time] 0.034s
  # [time] 0.034s (+5.723s refresh)
  # [time] 1.234s · brew:installed 5.723s (refresh failed)
```

Anatomy: `# [time] <felt> [· <breakdown> …] [(+<bg> <kind>) | (<note>)]`

- `# [time]` — same `# [...]` prefix as `# [cache]`; dim color on TTY.
- `<felt>` — total wall-clock from `main()` entry to just-before this
  line. Always present. `fmt_duration(s, sub_minute=True)`.
- `<breakdown>` — only the operations that actually ran in the
  foreground. Cache hits are *not* listed individually unless `-v`
  (caching is the goal — silent on the happy path).
- `(+<dur> refresh)` — appears when a bg refresh kicked off and we
  observed it complete inside the cache-flow grace window. If grace
  expired, surface `(refresh in bg)` instead.
- `(refresh failed)` — promotion of the cache-flow `✗` to the timing
  line when a bg refresh errored.

### Why a separate `# [time]` line and not folded into `# [cache]`

`# [cache]` is conditional (only when bg refresh fires) and *about*
refresh state. `# [time]` is unconditional and *about* the command as
a whole. Merging them would either drop timing on the happy path
(cache hit, no refresh → no line) or rename `# [cache]` into something
mushier. Keep them parallel:

- `# [cache] installed ✓ 0.123s` (or omitted when no bg refresh)
- `# [time] 1.234s`

When both fire, both print, two lines, lowest-info-loss.

### Format options considered

Alternatives we held against the chosen `# [time] <felt> · …` shape:

| Candidate | Pro | Con |
|-----------|-----|-----|
| `op:cache:formula=0.123s` | Greppable kv; namespaced | Loud per op; user has to count to find totals |
| `op(cache):formula=0.123s` | Parens visually group | Two delimiters where one would do |
| `[op]=1.251s (+5.723s refresh)` | Compact; total-first | `[op]` opaque — what op? |
| `# timing: search 1.234s, refresh 5.7s` | Prose-y, scan-friendly | Punctuation-heavy; mixes nouns and durations |
| Prom-style `bhs_time_seconds{…} 1.234` | Scrapeable | Overkill for a per-command CLI footer |

Chosen: `# [time] <felt> [· part part …] [(+bg)]`. Reasoning:

- Total first. Matches the "what did I wait for" question.
- `·` separator avoids comma/colon ambiguity with the `kind:name`
  notation we already use elsewhere (`installed:f`, etc.).
- Breakdown items follow the same `<kind>:<name> <dur>` form as `-C`
  already uses for cache rows. One vocabulary across the tool.

### Verbosity ladder

| Level | Flag | Behavior |
|-------|------|----------|
| 0 | `-q` / pipe | Suppressed entirely. |
| 1 | *default* | One line. Total + bg parenthetical when present. No per-op breakdown on cache-hit path. |
| 2 | `-v` | Adds per-source breakdown (`· cache:formula 0.012s · fts:formula 0.008s`). |
| 3 | `-vv` | Adds per-step (`fetch 0.4s · parse 0.2s · upsert 0.1s`). Subsumes the existing `# [cache] timing …` -v/-vv lines. |

### Where it prints

**stderr**, on its own line, after the trailing `# [cache]` line (if
any). Dim color when TTY.

`--json`, `--csv`, `--tsv`, `--sql`, `--grep` paths: still print
timing to stderr — stdout stays clean for downstream tools. (This is
the bit that felt "weird" in the discussion. The reason it's *not*
weird here: stdout is already a contract for those modes and timing
would corrupt it; stderr is for humans, and the line is dim, prefixed,
and easily filtered by `2>/dev/null`.)

Quiet (`-q`) suppresses entirely, both for human and pipe use.

Non-TTY (e.g. `bhs python | cat`): print to stderr unless `-q` /
isatty(stderr) is false. This matches `# [cache]`'s rule. If a user
genuinely wants no timing in a captured-stderr pipeline, `-q` is the
documented off switch.

### Suppression rules

| Case | `# [time]` printed? |
|------|---------------------|
| `-q` | no |
| `--no-timing` (new flag) | no |
| `BREW_HOP_SEARCH_NO_TIMING=1` env | no |
| stdout-only formats (`--json`, `--csv`, `--tsv`, `--sql`, `--grep`) | **yes** (to stderr) |
| stderr is not a TTY *and* default level | no (mirrors `# [cache]`) |
| `-v` or `-vv` | yes, even on non-TTY stderr |

Rationale for the non-TTY-default-off: `bhs foo 2>error.log` is a
common shape for scripted use; we don't want timing noise in those
logs unless the user opted in with `-v`.

### Instrumentation primitives

Re-use existing pieces:

- `fmt_duration` in `display.py` — already handles sub-second and
  multi-hour formats.
- `append_refresh_log` in `cache.py` — keeps writing the
  `refresh.log` row (no change). Timing footer is additional, not a
  replacement.
- Trailing-status sentinel mechanism — gives us bg refresh durations
  for the `(+…)` parenthetical without new IPC.

New piece: a `Timer` context manager in a new `timing.py` module:

```python
with timer("cache:formula") as t:
    ...
# t.elapsed (seconds), t.label (str)
```

A module-level `record(label, elapsed)` accumulates ops for the
footer. Cheap (list-append). Hot path adds <10µs.

### Naming alignment

Timing labels reuse the source vocabulary already in `-C`
(`installed:f`, `installed:c`, `local:f`, `local:c`, `taps`).
**Cache is implied** — every label is *a thing happening to or
around the cache*, so the `cache:` prefix the early sketch had is
redundant and dropped. Verbs (`stale`, `refresh`, `brew`, `http`,
`scan`) tell you what kind of work, and the source identifier tells
you which slice.

| Label | Meaning |
|-------|---------|
| `formula`, `cask` | SQLite/FTS read for a single source (foreground; no further qualifier needed at default verbosity) |
| `installed:f`, `installed:c` | SQLite/FTS read of the installed tables |
| `local:f`, `local:c` | SQLite/FTS read of the offline-API tables |
| `taps` | SQLite/FTS read of the taps table |
| `refresh:<source>` | Pre-query foreground refresh (sync; user waited) |
| `stale:<source>` | Post-print background refresh (user did not wait) |
| `brew:installed` | `brew info --json=v2 --installed` subprocess (inside a refresh) |
| `brew:outdated` | `brew outdated` subprocess (`--brew-verify`) |
| `http:formula`, `http:cask` | formulae.brew.sh fetches (inside a refresh) |

Two new verbs, on purpose:

- `refresh:` — *pre-query, foreground*. The user explicitly asked
  for fresh data and waited. Shows up in `<felt>` time.
- `stale:` — *post-print, background*. Cache was served stale, bg
  fired. Shows up in the `(+…)` parenthetical, never in `<felt>`.

That mirrors the cache-flow grammar: stale → cached results first,
refresh → fresh results first. The timing line surfaces the same
distinction so the user can tell *why* a command was slow at a
glance.

The source-vocabulary ordering (`installed:f` vs a compact `fi`
spelling, etc.) is not yet pinned down — see open question below
plus tracker bead.

## Examples

```
$ bhs python
  python  3.13.2  Interpreted, interactive, object-oriented programming language
  ... (16 more)
  # [time] 0.034s

$ bhs -i python                       # stale cache, bg refresh
  python  3.13.2  installed
  python@3.12  3.12.10  installed
  # [cache] installed still updating in background
  # [time] 0.041s (refresh in bg)

$ bhs -i python                       # 8 seconds later, bg finished
  python  3.13.2  installed
  python@3.12  3.12.10  installed
  # [time] 0.038s

$ bhs --refresh=installed -i python   # synchronous refresh
  python  3.13.2  installed
  # [cache] installed ✓ 6.2s
  # [time] 6.234s · brew:installed 6.213s

$ bhs -v python                       # -v: per-source breakdown
  ...
  # [time] 0.034s · cache:formula 0.012s · cache:cask 0.011s · fts:formula 0.008s · fts:cask 0.003s

$ bhs -q python                       # quiet: no timing
  python
  python@3.12
  ...
                                       (no # [time] line)

$ bhs --json python                    # json: stderr footer, stdout clean
  [{"name":"python", ...}]
  # [time] 0.034s                      (→ stderr)

$ bhs python --no-timing               # explicit off
  ...
                                       (no # [time] line)
```

## Open questions

- **Source-vocabulary spelling** — `installed:f` (current `-C`) vs
  compact `fi` vs verbose `installed:formula`. The user has flagged
  "I keep forgetting which order" as a real ergonomic problem.
  Whatever this spec picks, `-C`, timing, and the new installed
  indicator all need to use the same scheme. Tracked separately as
  a vocabulary spec — see [cli-vocabulary](cli-vocabulary.md) (TBD)
  / bead.
- **Stale-result diff detection** — to print `↻ updated, results may
  differ` the foreground has to remember what it printed and rerun
  the FTS query against the refreshed cache. Either snapshot the
  printed `(name, version)` tuples in memory, or hash the result
  envelope. Either works; see bead.
- **`-v` scoped sub-args** — the user proposed `-v=t`, `-v=tt`,
  `-v=ttcl` style verbosity where each character bumps one
  dimension's depth (`t`iming, `c`ache, `l`abels, …). Compelling for
  power users; not in scope for v1 of this spec. See bead.
- Do we want `--timing` as a flag that *forces* the line on (e.g. for
  `-q --timing`)? Probably yes, for benchmark scripts. Defer until
  someone asks.
- A `--timing=json` mode that emits a single JSON object instead of
  the prose line, for machine consumption? Defer — `refresh.log`
  already serves that need for cache ops.
- Should `# [time]` also appear on `bhs --refresh=KIND` standalone
  command (no query)? Yes — the per-kind line plus a total are both
  useful. Aligns with the existing `# [cache] total Xs` at `-v`.

## Implementation notes

- New module: `src/brew_hop_search/timing.py` (Timer + record + render).
- Hook point: a `try/finally` in `cli.main()` that records total
  wall-clock and calls `render_footer()` before exit.
- `--no-timing` is a new argparse flag in the existing verbosity group.
- Tests:
  - `test_timing_render.py` — pure render tests against captured
    record lists. Snapshot the format.
  - Integration: extend `test_cache_flow.py` to assert `# [time]`
    appears in stderr for a default `bhs` invocation and is absent
    under `-q`.

## Spec status

**v1 landed (2026-05-28, this session):**
- `# [time] <felt>` footer to stderr after every command.
- `--no-timing` flag + `BREW_HOP_SEARCH_NO_TIMING` env off-switches.
- Policy table implemented in `timing.should_emit` — `-q`, help,
  version, `--_bg-refresh` all suppress; non-TTY stderr suppresses
  at default verbosity but `-v` always shows.
- Prefix spelling resolved: `# [time]` (the `# [cache] timing …`
  `-vv` lines stay using "timing" in their *value*; the two
  prefixes don't collide).
- `Timer` context manager + module-level `record()` scaffolding
  in place; not used in the default footer yet.

**Deferred (separate beads / follow-up commits):**
- Per-source breakdown at `-v` (`· installed:f 0.012s · fts:formula
  0.008s`). Plumbing exists (Timer/record); needs callers
  instrumented in each source module + a render path that consumes
  `_records`.
- `(+<dur> refresh)` parenthetical from the bg-refresh sentinel.
  Coupling: when `display.trailing_refresh_status` reads a
  completion sentinel within its grace window, that duration
  should flow into the timing footer's parenthetical.
- `(refresh failed)` / `(refresh in bg)` variants per spec.
- `--timing=json` machine-readable mode.
- `-v=t`, `-v=tt` scoped sub-args (bead bhs-de8).
- Vocabulary unification for the label set (bead bhs-3g9).
