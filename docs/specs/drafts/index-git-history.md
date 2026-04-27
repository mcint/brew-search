# index-git-history

Show the version history of a formula or cask as recorded in the
homebrew-core / homebrew-cask git log — what versions of a recipe the
brew index has carried, regardless of what this machine ever installed.

## Status

**Draft** — not yet implemented. Sibling to `features/history.md`
(install log on this machine). This feature reads the brew **index**'s
history; `-H` reads the local **install** log. Both can be useful for
the same triage question and the spec assumes they live side by side.

## Purpose

Answer: *"What versions of `python@3.13` were available in the brew
index over the last N months?"* Used when picking a rollback target,
debugging a regression, or auditing how fast a recipe churns.

`-H` already answers "what did *I* install"; this answers "what *could*
I have installed (or could install via `brew extract`)." The two
overlap on the rollback-target use case but neither subsumes the other:
`-H` is bounded by what this machine has touched, this is bounded only
by repository history.

## Input

- **flag**: `-G` / `--index-history`  *(new — not an extension of `-H`)*
- **query**: package name (required)
- **source filter**: `-f` / `--formulae`, `-c` / `--casks` to disambiguate
  when a name exists in both (default: try formula first, then cask)
- **scope**:
  - `--limit N` — last N commits (default: 20)
  - `--since DATE` — ISO date or relative (`6m`, `1y`, `2026-01-01`)
  - both compose: `--limit 50 --since 1y` = up to 50, but stop at 1y
- **data source**: `--source=local|api|auto` (default: `auto`)
- **verbosity**: `-q`, `-v`, `-vv`
- **format**: `-g`, `--json[=MODE]`, `--csv`, `--tsv`, `-T`/`--table`, `--sql`

### Why a new flag, not `-H --source=git`

Considered. Rejected because:

1. `-H` and `-G` answer different questions with different cardinality.
   `-H` is bounded by *my installs* (typically 1–10 rows for a given
   package). `-G` is bounded by *repo churn* (could be hundreds). A
   shared flag with mode-dependent output and column sets is the kind
   of overload that makes `--help` unreadable.
2. Composition wins: `bhs -H foo` and `bhs -G foo` can be diffed by the
   user. A future `-HG foo` (or `--with-index-history`) could
   interleave both, but that's a follow-up, not the v1 surface.
3. `-G` mirrors `-H` ergonomically (single uppercase letter, one
   positional arg, same format flags) so the *pattern* is shared even
   though the flags are distinct.

## Output

### Verbosity levels

| Level | Flag | Behavior |
|-------|------|----------|
| 0 | `-q` | Tab-separated rows, no headers, no footer. One row per version-change commit. |
| 1 | *default* | Header line, per-row indent, footer hint. |
| 2 | `-v` | Adds short commit subject column. |
| 3 | `-vv` | Adds author + full commit hash + the URL field from the recipe. |

Format flags bypass verbosity (same rule as `-O`, `-H`).

### Default (level 1)

```
  index history for python@3.13  (homebrew-core, last 20 commits)
  3.13.2  2026-04-09  abc1234
  3.13.1  2026-03-15  def5678
  3.13.0  2026-02-01  789abcd
  3.12.8  2026-01-04  fed3210
  ...

  -- brew extract python@3.13 <tap> • -H python@3.13 for local install log
```

- Newest first.
- Per-row: version, ISO date, short commit hash.
- Only **version-change** commits are shown by default; bottle rebuilds
  and revision bumps that don't change `version` are folded into the
  most recent row above them. `-vv` un-folds.
- Footer hints rollback path (`brew extract`) and cross-references
  `-H`.

### Quiet (`-q`)

```
3.13.2	2026-04-09	abc1234
3.13.1	2026-03-15	def5678
```

Columns: `version<TAB>date<TAB>commit`.

### Grep (`-g`)

Source-prefixed, matching `-O -g` convention:

```
f	python@3.13	3.13.2	2026-04-09	abc1234
f	python@3.13	3.13.1	2026-03-15	def5678
```

Columns: `source<TAB>name<TAB>version<TAB>date<TAB>commit`.

### JSON

```json
{
  "meta": { "mode": "index-history", "name": "python@3.13", "kind": "formula",
            "source": "local", "tap": "homebrew/core", "count": 4 },
  "data": [
    { "version": "3.13.2", "date": "2026-04-09T10:00:00Z",
      "commit": "abc1234def...", "url": "https://.../python-3.13.2.tar.gz" },
    { "version": "3.13.1", "date": "2026-03-15T14:30:00Z",
      "commit": "def5678abc...", "url": "..." }
  ]
}
```

`--json=short` flattens to `[{version, date, commit}]` only.

### CSV / TSV / Table / SQL

Same column set as `-g`. SQL emits:

```sql
CREATE TABLE IF NOT EXISTS index_history (
  name TEXT, kind TEXT, version TEXT, date TEXT, commit TEXT, url TEXT
);
INSERT INTO index_history VALUES ('python@3.13','formula','3.13.2',...);
```

## Data Sources

### Local mode (preferred default)

1. `brew --repository` → path to homebrew-core clone (also picks up
   tap repos for non-core formulae via `Library/Taps/<user>/<repo>`).
2. `git -C <repo> log --follow -- Formula/p/python@3.13.rb` for the
   commit list (formula path scheme uses first-letter shard).
3. For each commit: `git show <commit>:<path>` piped through the
   existing `parse_rb()` from `sources/taps.py`. We extract `version`
   and `url`.
4. Adjacent commits with the same `version` collapse (level 1) or
   stay distinct (`-vv`).

Casks: identical flow against `homebrew-cask` repo, path
`Casks/<first-letter>/<name>.rb`. `parse_rb` already handles the
`cask "name"` block and pulls `version`/`url`/`homepage` — same code
path, just a different repo and path scheme. No new parser needed.

### API mode (fallback / `--source=api`)

1. `GET https://api.github.com/repos/Homebrew/homebrew-core/commits?path=Formula/p/python@3.13.rb&per_page=N`
   for the commit list.
2. For each commit, `GET .../contents/<path>?ref=<sha>`, base64-decode,
   feed to `parse_rb` (same parser, in-memory bytes instead of file).
3. Authenticated with `GITHUB_TOKEN` env var if present (same env var
   conventions as the rest of the ecosystem); unauthenticated falls
   back to 60 req/hr.

### `auto` resolution

1. If `brew --repository` succeeds *and* the formula's `.rb` exists in
   that clone → `local`.
2. Else if network is reachable → `api`.
3. Else error with a hint to install brew or set `--source=api`.

`-vv` shows which source was used in the header.

## Cache Behavior

### Table layout

New SQLite table, populated on demand and TTL'd like other API caches:

```sql
CREATE TABLE IF NOT EXISTS index_history (
  name        TEXT NOT NULL,
  kind        TEXT NOT NULL,           -- 'formula' | 'cask'
  version     TEXT NOT NULL,
  date        TEXT NOT NULL,           -- ISO 8601
  commit_sha  TEXT NOT NULL,
  url         TEXT,
  source      TEXT NOT NULL,           -- 'local' | 'api'
  fetched_at  INTEGER NOT NULL,        -- epoch seconds
  PRIMARY KEY (name, kind, commit_sha)
);
CREATE INDEX IF NOT EXISTS idx_index_history_name ON index_history(name, kind, date DESC);
```

### TTL

`STALE_INDEX_HISTORY` (env: `BREW_HOP_SEARCH_STALE_INDEX_HISTORY`),
default `24h`. Reuses the `_from_env` helper in `defaults.py`, same
shape as `STALE_API` and `STALE_TAPS`.

Cache key is `(name, kind)`. On query: if any row for that key is
younger than the TTL, serve from cache (filtered by `--limit` /
`--since`); otherwise refresh.

Local-mode refresh is cheap (a few `git show`s); API mode benefits
most from caching. The same TTL applies regardless of source so users
don't see surprising freshness differences when `auto` flips modes.

### Refresh control

Standard `--refresh` / `--refresh=Nh` flag (already shared across
features) forces a re-read. `--no-cache` skips both read and write.

## Examples

```sh
bhs -G python@3.13                   # last 20 commits, default form
bhs -G python@3.13 --limit 5         # last 5 version-changes
bhs -G python@3.13 --since 6m        # last 6 months
bhs -G python@3.13 -vv               # full hash, author, url
bhs -G firefox -c                    # cask history (homebrew-cask)
bhs -G python@3.13 --json | jq '.data[].version'
bhs -G python@3.13 --source=api      # force GitHub API path

# Combine with the install log to see what *I* had vs what was *available*:
diff <(bhs -H python@3.13 -q | cut -f1) <(bhs -G python@3.13 -q | cut -f1)
```

## Tests

Per the project's TDD norm, snapshot tests precede implementation:

- `test_index_history_local_basic` — mock `git log` + `git show` output,
  assert default rendering.
- `test_index_history_collapses_revisions` — two commits, same
  `version`, second one a revision bump → one row at level 1, two at
  `-vv`.
- `test_index_history_cask` — `homebrew-cask` path scheme, `parse_rb`
  on a cask file, asserts `kind=cask` in JSON meta.
- `test_index_history_cache_hit` — second invocation within TTL serves
  from SQLite without invoking git.
- `test_index_history_api_fallback` — `--source=api` with a recorded
  HTTP fixture; assert same column set as local mode.
- `test_index_history_limit_and_since` — both flags compose; `--since`
  cuts off before `--limit` does.

Snapshot masking: the existing date masker (`YYYY-MM-DD`) covers `date`;
add a commit-hash masker (`[0-9a-f]{7,40}` → `COMMIT`) for stability.

## Related

- `docs/specs/features/history.md` — `-H` install log; cross-link in
  both directions when this ships.
- `docs/specs/features/outdated.md` — `-O` already nods toward
  `-H <name> for history`; add `-G <name> for index history` to the
  footer hint.
- `src/brew_hop_search/sources/taps.py` — `parse_rb()` is the reusable
  unit; this feature should not re-implement Ruby recipe parsing.
- `docs/specs/features/cache-status.md` — add `index_history` to the
  per-source listing once the table exists.
