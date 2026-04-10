# Audiences

Who uses brew-hop-search and what they need.

## Casual Homebrew Users

Quick search, install the first thing that looks right.

**Want**: fast results, install hint, simple defaults.
**Don't need**: source tags, cache details, JSON output.
**Surface**: `brew-hop-search python` → copy the install command.

## Power Users / Sysadmins

Manage many machines, audit installed packages, track updates.

**Want**: `-O` outdated, `-i` installed listing, `-H` history,
`--brew-verify` for authoritative checks, `--json` for scripts.
**Surface**: `brew-hop-search -O --json | jq '.outdated_formulae[] | .name'`

## Script / Automation Authors

Integrate into shell scripts, CI, dotfiles.

**Want**: `-q` for clean piping, `-g` for tab-separated,
`--json` for structured data, stable output format,
non-zero exit on error (not on empty results).
**Avoid**: color codes in pipes (auto-detected via TTY),
interactive prompts (there are none).

## AI Assistants / LLM Tools

Programmatic access to Homebrew package metadata.

**Want**: `--json` with self-describing envelope,
stable schema, `--quiet` for minimal output,
predictable exit codes.
**Avoid**: ANSI colors, progress indicators on stderr,
any interactive behavior.

## Developers Contributing to brew-hop-search

Understanding the codebase, adding features.

**Want**: `docs/specs/` for behavior contracts,
snapshot tests for output stability,
`-VV` for diagnostic info,
`BREW_HOP_SEARCH_DB` for test isolation.
