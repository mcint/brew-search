#!/usr/bin/env bash
# Generate README.md from template + live command output.
# Run: ./scripts/build-readme.sh > README.md
set -euo pipefail

BHS="uv run brew-hop-search"

# Capture live outputs (strip ANSI)
strip_ansi() { sed $'s/\033\\[[0-9;]*m//g'; }

DEFAULT_OUTPUT=$($BHS python -n 5 2>&1 | strip_ansi)
VERBOSE_OUTPUT=$($BHS -v python -n 5 2>&1 | strip_ansi)
QUIET_OUTPUT=$($BHS -q python -n 3 2>&1 | strip_ansi)
CSV_OUTPUT=$($BHS --csv python -n 3 2>&1 | strip_ansi)
TABLE_OUTPUT=$($BHS --table python -n 5 2>&1 | strip_ansi)
CACHE_OUTPUT=$($BHS -C 2>&1 | strip_ansi)
HELP_OUTPUT=$($BHS --help 2>&1 | strip_ansi)
VERSION_OUTPUT=$($BHS -V 2>&1 | strip_ansi)

cat <<TEMPLATE
# brew-hop-search

Fast offline-first search of Homebrew formulae, casks, taps, and installed packages.

Built on SQLite + FTS5 for instant local search with smart caching.

[GitHub](https://github.com/mcint/brew-hop-search) ·
[PyPI](https://pypi.org/project/brew-hop-search/) ·
[Brew Tap](https://github.com/mcint/homebrew-brew-hop-search/blob/main/Formula/brew-hop-search.rb)

## Install

\`\`\`sh
# PyPI (recommended)
uv tool install brew-hop-search     # or: pip install brew-hop-search
uvx brew-hop-search python          # one-shot without install

# Homebrew tap
brew tap mcint/brew-hop-search
brew install brew-hop-search
\`\`\`

## Example output

Default search — clean, human-optimal:
\`\`\`
$DEFAULT_OUTPUT
\`\`\`

With \`-v\` — source tags and cache info:
\`\`\`
$VERBOSE_OUTPUT
\`\`\`

Quiet mode (\`-q\`) for piping:
\`\`\`
\$ brew-hop-search -q python | fzf
$QUIET_OUTPUT
\`\`\`

## Output formats

### CSV (\`--csv\`)
\`\`\`csv
$CSV_OUTPUT
\`\`\`

### Table (\`--table\`)
\`\`\`
$TABLE_OUTPUT
\`\`\`

Also: \`--tsv\`, \`--json\`, \`--sql\`, \`-g\` (grep).

## Cache status (\`-C\`)

\`\`\`
$CACHE_OUTPUT
\`\`\`

## Usage

\`\`\`
$HELP_OUTPUT
\`\`\`

### Examples

\`\`\`sh
brew-hop-search python                 # search formulae + casks
brew-hop-search -f python build        # multi-word, formulae only
brew-hop-search -i                     # list all installed
brew-hop-search -i -c                  # installed casks only
brew-hop-search -q python | fzf        # pipe to fzf
brew-hop-search --csv python | qsv sort -s name  # sort CSV
brew-hop-search --sql python | sqlite3 results.db  # import to sqlite
brew-hop-search -O                     # show outdated (fast, local)
brew-hop-search -O --brew-verify       # diff: fast vs brew
brew-hop-search -H python@3.13         # version history for rollback
brew-hop-search --refresh python       # force re-fetch
\`\`\`

### Direct DB access

The SQLite database is at \`~/.cache/brew-hop-search/brew-hop-search.db\`:

\`\`\`sh
sqlite-utils tables ~/.cache/brew-hop-search/brew-hop-search.db
sqlite-utils search ~/.cache/brew-hop-search/brew-hop-search.db formula python
\`\`\`

## How it works

On first run, fetches Homebrew formula and cask indexes from \`formulae.brew.sh\` into SQLite with FTS5. Subsequent searches are instant (local DB). Stale caches trigger background refresh.

| Source | Flag | Data | Calls brew? |
|--------|------|------|-------------|
| Remote API | *(default)* | \`formulae.brew.sh\` | No |
| Installed | \`-i\` | \`brew info --json=v2 --installed\` | Yes |
| Taps | \`-t\` | \`.rb\` files in \`\$(brew --repo)/Library/Taps/\` | Yes |
| Local | \`-L\` | Brew's API cache at \`\$(brew --cache)/api/\` | Yes |
| Outdated | \`-O\` | Compares installed vs API index | No |
| Outdated | \`-O --brew-verify\` | Diff fast vs \`brew outdated\` | Yes |

## Docs

- [Design System](docs/DESIGN-SYSTEM.md) — cartesian spec architecture
- [Specs](docs/specs/) — INPUT, OUTPUT, ENVELOPE, SCHEMA, per-feature
- [Comparables](docs/COMPARABLES.md) — Python project references
- [Least Surprise](docs/LEAST-SURPRISE.md) — operational principles
- [Man page](docs/brew-hop-search.1.md) — full reference

## Version

\`\`\`
$VERSION_OUTPUT
\`\`\`

## License

MIT
TEMPLATE
