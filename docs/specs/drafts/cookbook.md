# Cookbook & Usage Examples (draft)

## Purpose
Curated, composition-focused examples that show bhs as a *data source* feeding other
unix tools — especially `sqlite-utils memory` for ad-hoc analysis — without growing
the CLI surface area.

## Status
**Draft** — not yet implemented.

## Motivation

The README's `### Examples` section is a flat list of one-liners. It doesn't show
the interesting compositions: piping JSON into `jq` + `sqlite-utils memory` to
slice outdated casks by `auto_updates`, joining installed versions back to API
versions, cross-referencing taps, etc. These are the "aha" moments that sell bhs
as a unix citizen rather than a monolithic search tool.

Two real examples from a recent session (2026-04):

```sh
# Which outdated casks auto-update (and are therefore noise) vs. actually stale?
brew-hop-search -O -c --json \
  | jq '.data.outdated_casks' \
  | sqlite-utils memory - "select token, installed, current, auto_updates from stdin" --table

# Installed versions list (brew keeps multiple) joined to current API version
brew-hop-search -i -f --json \
  | jq '.data' \
  | sqlite-utils memory - "select name, installed_versions, current_version from stdin where json_array_length(installed_versions) > 1" --table
```

Neither of these needs new bhs flags — they need discoverability.

## Non-goals

- **No** built-in SQL engine wrapper. `sqlite-utils memory` already exists; bhs
  should not re-invent it or vendor it behind a flag.
- **No** automatic piping / subprocess spawning. Users compose.
- **No** growth of the JSON schema to "help" downstream tools. The existing
  meta envelope + `--json=short` are already the right shape.

## Options considered

### A. Cookbook doc only (lowest surface area)

Add `docs/COOKBOOK.md` with titled recipes. Link from README and man page.
Zero CLI changes. Each recipe is a tiny scenario + one command block + one
sentence on *why* it's non-obvious.

### B. `--examples` flag

`brew-hop-search --examples` prints the cookbook to stdout. Optional positional
filter (e.g. `--examples outdated` greps recipe titles). One new flag, no
behavior change elsewhere.

### C. `--examples` + embedded markdown

Same as B, but the cookbook *file* is the source of truth and the flag prints
it. Ship the file as package data so `uv tool install` users get it too.

### Recommendation

**A + C**: ship `docs/COOKBOOK.md`, include it as package data, expose
`--examples [TOPIC]` that prints it. Single new flag, single new file, no
behavior coupling.

## Content buckets (initial)

1. **Piping to fzf** — already in README, promote the subtleties (`-q` vs `-g`).
2. **SQLite-utils memory recipes** — the two above, plus:
   - Outdated formulae grouped by tap
   - Casks whose homepage matches a regex
   - Installed packages with no current API entry (orphans)
3. **jq filters** — extracting names-only, versions-only, homepage-only.
4. **Combining with `brew`** — `bhs -q pkg | xargs brew info`, etc.
5. **Cron / daily refresh** — `--refresh=24h` in a launchd plist.

## CLI spec (option B/C)

```
--examples [TOPIC]    print cookbook recipes (optional title filter)
```

- Respects `--json`: with `--json`, emits recipes as structured objects
  (`[{title, scenario, command, why}]`) for LLM / tooling consumption.
- Respects `-q`: command-only (one recipe per line, no prose) for grep/fzf.
- Exits after printing. No network, no cache touch.

## Open questions

- Should recipes be tagged with required flags (e.g. `requires: jq, sqlite-utils`)
  so `--examples --installed` only shows what the user can actually run? Probably
  over-engineered for v1; document required tools in prose.
- Man page inclusion? Recipes inflate `man bhs` quickly. Prefer a `SEE ALSO`
  pointer to the cookbook file.
