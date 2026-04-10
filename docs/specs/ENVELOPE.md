# JSON Envelope Specification

How `--json` output is structured for machine consumption.

## Current State

### Search Results

When searching multiple sources, JSON groups results by source kind:

```json
{
  "formula": [
    { "name": "python@3.13", "desc": "...", "homepage": "...", "versions": { "stable": "3.13.2" }, ... }
  ],
  "cask": [
    { "token": "anaconda", "desc": "...", "homepage": "...", "version": "2025.12", ... }
  ]
}
```

Single-source searches emit a flat array (no wrapping object).

### Outdated

```json
{
  "outdated_formulae": [
    { "name": "python@3.13", "installed": "3.13.1", "current": "3.13.2", "pinned": false, "keg_only": false }
  ],
  "outdated_casks": [
    { "token": "firefox", "installed": "121.0", "current": "122.0", "auto_updates": false }
  ]
}
```

### Cache Status

```json
{
  "cache_dir": "~/.cache/brew-hop-search/",
  "db_path": "~/.cache/brew-hop-search/brew-hop-search.db",
  "db_exists": true,
  "db_size_bytes": 52428800,
  "sources": {
    "formula": { "count": 8307, "age_seconds": 3600.0, "updated_at": 1712000000, "fts": true },
    "cask": { "count": 7589, "age_seconds": 3600.0, "updated_at": 1712000000, "fts": true }
  }
}
```

### History

```json
[
  { "name": "python@3.13", "kind": "formula", "version": "3.13.2", "brew_commit": "abc1234", "recorded_at": "2026-04-09T10:00:00" }
]
```

## Future: Meta Envelope

Target structure for search results, matching the self-describing
pattern from lib-rs-search:

```json
{
  "meta": {
    "command": "search",
    "query": "python",
    "sources": ["formula", "cask"],
    "limit": 20,
    "offset": 0,
    "total": 42,
    "count": 20,
    "date": "2026-04-09T14:30:00-0700"
  },
  "results": {
    "formula": [...],
    "cask": [...]
  }
}
```

### Meta Fields

| Field | When Present | Description |
|-------|-------------|-------------|
| `command` | always | Which mode produced this (`search`, `outdated`, `cache-status`, `history`) |
| `query` | search | The search query terms |
| `sources` | search | Data sources searched |
| `limit` | search | Results per section |
| `offset` | search | Starting position |
| `total` | search | Total matches available |
| `count` | always | Results in this response |
| `date` | always | ISO 8601 timestamp |

Fields are **omitted** (not null) when they don't apply.

## Design Rule

JSON output alone should reveal: what command ran, what was queried,
how many results exist vs shown, and when the data was fetched.
