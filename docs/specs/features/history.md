# history

Show version history for a package from the install log.

## Purpose

Track which versions of a package have been installed over time.
Useful for rollback decisions: "What version was I on before this
upgrade broke things?"

## Input

- **flag**: `-H` / `--history`
- **query**: Package name (required)
- **format**: `--json`

## Output

### Default

```
  version history for python@3.13
  3.13.2  [formula]  2026-04-09 10:00  commit abc1234
  3.13.1  [formula]  2026-03-15 14:30  commit def5678
  3.13.0  [formula]  2026-02-01 09:00  commit 789abcd

  rollback: brew install <name>@<version>
  pin:      brew pin <name>
```

- Versions newest first
- Per-row: version, kind tag, timestamp, brew core commit hash
- Footer: rollback and pin hints

### JSON

```json
[
  {
    "name": "python@3.13",
    "kind": "formula",
    "version": "3.13.2",
    "brew_commit": "abc1234",
    "recorded_at": "2026-04-09T10:00:00"
  }
]
```

## Data Sources

- `install_log` table in the local database
- Populated when `-i` (installed) flag is used — each installed version
  is recorded with timestamp and brew core git commit hash
- If no history exists, suggests running with `-i` first to build the log

## Cache Behavior

Read-only from local database. No network access.
History is append-only — old entries are never deleted.

## Examples

```sh
brew-hop-search -H python@3.13         # show version history
brew-hop-search -H python@3.13 --json  # for scripts
brew-hop-search -H node                # check node version trail
```
