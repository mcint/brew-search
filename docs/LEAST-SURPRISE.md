# Least Surprise

Principles for predictable, low-maintenance operation on end-user machines.

## Core Principle

**The user should never need to think about brew-hop-search's internals.**
Search should just work. Cache should be invisible. Errors should be
recoverable without user intervention.

## Self-Healing Cache

### No manual cache management required

- First search auto-builds the index (no `init` command)
- Stale cache auto-refreshes in background (no `update` command)
- Corrupted database? Delete it. Next search rebuilds from scratch.
- `--refresh` exists for power users, but the default handles everything.

### Cache dates communicate freshness

Every output mode implicitly signals data age:

- **Default**: No age shown. If you see results, they're fresh enough.
- **`-v`**: Cache age header: `-- cache: 2h old`. User can judge.
- **`-C`**: Per-source age and entry counts.
- **`--json`**: Timestamps available for scripts to check.

The **absence** of cache info at default verbosity is intentional —
it means "trust the data." Showing age only when asked prevents
users from second-guessing every search result.

### Dates imply their own limitations

- `(2h ago)` means "this was true 2 hours ago"
- `(3d ago)` means "probably fine for search, maybe stale for versions"
- The tool never claims data is live unless it was just fetched

## Zero-Config Operation

### No setup, no config file, no environment variables needed

- Works immediately after `pip install`
- Database location follows XDG (`~/.cache/`)
- Config file is optional (only for user-agent override)
- Environment variables are for testing and CI, not daily use

### Defaults are the right answer for 95% of use

| Default | Value | Why |
|---------|-------|-----|
| Search source | Remote API | Most common, no subprocess needed |
| Result limit | 20 | Fits one terminal screen |
| Stale threshold | 6 hours | Fresh enough for search, rare enough to not waste bandwidth |
| Verbosity | Level 1 | Headers + results, no noise |
| Color | Auto (TTY) | Pretty on terminal, clean in pipes |

## No Surprises in Output

### Piped output is different from terminal output

- Terminal: color, section headers, install hints
- Piped: no ANSI codes, same content
- `-q`: guaranteed pipe-safe (no headers, no color, one per line)

### Format stability is a contract

- Snapshot tests lock down the default output format
- `--json` schema changes are versioned (SCHEMA.md)
- New fields are added, old fields are never removed
- `--csv`/`--tsv` column order is fixed

### Exit codes are predictable

- 0: success (including zero results)
- 1: error (cache failure, subprocess failure)
- Never: non-zero for "no results found" (that's valid output)

## Graceful Degradation

### Every failure mode has a fallback

| Failure | Fallback |
|---------|----------|
| Network down | Serve stale cache |
| No cache at all | Error message with clear fix: "run a search first" |
| FTS5 missing | Fall back to full table scan |
| `brew` not found | Only affects `-i`, `-t`, `-L`. Default search works. |
| Database corrupted | Delete and rebuild on next search |
| New upstream fields | Ignored (stored in `raw`, extracted when code updates) |
| Removed upstream fields | Display falls back to empty string |

### No subprocess in the default path

Default search (`brew-hop-search python`) calls zero subprocesses.
Only HTTP to `formulae.brew.sh` or local SQLite reads.

Subprocesses are opt-in:
- `-i` → `brew info`
- `-t` → `brew --repository`
- `-L` → `brew --cache`
- `--brew-verify` → `brew outdated`

## History as Insurance

### Version history records automatically

The `install_log` table records every version seen during `-i` refreshes.
This is append-only — old entries are never deleted.

**Goal**: Hook into `brew upgrade` to automatically record versions.
See [brew-update hook](#brew-update-hook) below.

### Rollback info is always available

`-H <name>` shows version history with:
- Exact version strings
- Brew core commit hashes (for `git checkout` rollback)
- Timestamps

## Brew-Update Hook

### The Problem

History indexing currently requires the user to run `brew-hop-search -i`
periodically. If they upgrade a package without running `-i` first,
the old version is never recorded.

### The Solution (planned)

A post-upgrade hook that automatically records installed state:

```sh
# In ~/.config/brew-hop-search/config.toml:
# brew_hook = true

# Or as a brew post-install hook:
# ~/.homebrew/Hooks/post-install/brew-hop-search-record.sh
brew-hop-search --_record-installed "$@"
```

This would:
1. Run after every `brew install` / `brew upgrade`
2. Record the new version to `install_log`
3. Be fast (< 100ms, just a sqlite insert)
4. Be optional (off by default, opt-in via config)

### Implementation Path

1. Add `--_record-installed` hidden CLI flag
2. Add config option `brew_hook: true`
3. Document the hook setup in man page
4. Consider a `brew-hop-search hook install` command to set it up

## Principle Summary

| Principle | Implementation |
|-----------|---------------|
| Works out of the box | Auto-build index on first search |
| Cache is invisible | Background refresh, no update command |
| Dates imply limitations | Age strings, not "guaranteed fresh" |
| Output is stable | Snapshot tests, versioned schema |
| Failures are recoverable | Delete-and-rebuild, fallback chains |
| No surprises in pipes | Auto TTY detection, `-q` for safety |
| History is insurance | Append-only log, automatic recording |
