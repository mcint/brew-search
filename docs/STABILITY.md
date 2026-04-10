# Stability

Upstream dependencies, schema risks, and graceful degradation.

## Upstream API Stability

| Source | Risk | Notes |
|--------|------|-------|
| formulae.brew.sh JSON | **Low** | Official Homebrew API. Stable, versioned, used by brew itself. |
| `brew info --json=v2` | **Low** | Stable JSON schema, versioned (`v2`). Used by many tools. |
| `brew outdated --json=v2` | **Low** | Same as above. |
| `brew --cache` / `brew --repository` | **Low** | Simple path output, unlikely to change. |
| Local `.rb` formula files | **Medium** | Ruby DSL parsed with regex. New DSL features could break parser. |
| PyPI JSON API | **Low** | Standard, documented, stable. |

## Schema Evolution

### Remote API Data

All fields from formulae.brew.sh are stored as raw JSON (`raw` column).
Parsed fields (`name`, `desc`, `homepage`, `version`) are extracted
at index time. If upstream adds/removes fields:

- **New fields**: Available in `raw`, ignored by display until code updated
- **Removed fields**: Display falls back to empty string, no crash
- **Changed types**: JSON parsing is lenient (`str()` wrappers)

### Local Database

- Tables created with `insert_all(..., pk=...)` — schema-flexible
- FTS5 indexes rebuilt on each refresh cycle
- `_meta` table tracks per-source timestamps and counts
- `install_log` table is append-only (never deleted)

### Adding New Sources

1. Add source module in `sources/`
2. Add CLI flag in `cli.py`
3. Add table name to cache status display
4. Add source indicator in `display.py._SOURCE_CHARS`
5. Add feature spec in `docs/specs/features/`

## Subprocess Dependencies

| Command | Used By | Failure Mode |
|---------|---------|--------------|
| `brew info --json=v2 --installed` | `-i` flag | Error message, skip source |
| `brew outdated --json=v2` | `--brew-verify` | Error message, suggest fast mode |
| `brew --repository` | `-t` flag | Error message, skip source |
| `brew --cache` | `-L` flag | Error message, skip source |
| `git rev-parse --short HEAD` | `-V` flag | Omit commit hash |
| `git log --oneline` | `-VV` flag | Omit commit log |

No subprocess failure should crash the tool.
Default search (no flags) calls zero subprocesses.

## Security

- **No credentials stored**: No tokens, no auth.
- **No upstream writes**: Read-only tool.
- **User-Agent**: Configurable via env var or config file. Default: `brew-hop-search/{version}`.
- **Cache directory**: User-owned, standard XDG location.
- **Network requests**: Only to formulae.brew.sh and pypi.org. No third-party telemetry.

## Known Limitations

- `.rb` parser uses regex, not a Ruby AST — exotic DSL patterns may not parse
- Outdated fast mode doesn't check bottle rebuild numbers
- Casks with `version "latest"` excluded from outdated comparison
- Tap-only formulae not in the main API index are invisible to default search
- FTS5 porter stemmer may over-match (e.g., "test" matches "testing")
