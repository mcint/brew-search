# Taste

Design philosophy expressed through choices and direction.

## Core Asks (chronological)

1. Fast offline Homebrew search — no `brew search` subprocess
2. SQLite + FTS5 for instant local queries
3. Background cache refresh — never block the user
4. Composable source flags — `-i -t -L` are additive
5. Verbosity as progressive disclosure — clean default, `-v` for context
6. `-q` for pipes, `-g` for awk, `--json` for jq
7. Section headers with counts and install hints
8. Paging with offset: `-n 20+40`
9. Outdated detection without calling `brew outdated`
10. Version history for rollback awareness
11. Snapshot tests — output format is a contract
12. Spec alongside code — version intent with implementation

## Coherent Desire

A **search tool that respects your terminal**.

- **Default is human-optimal**: No noise, no spinners, no progress bars in stdout.
  Status updates go to stderr. Results go to stdout.
- **Cache is invisible**: You don't need to know about cache.
  It just works. `-v` if you're curious. `-C` if you're debugging.
- **No brew dependency at default**: `brew` is only called when you
  ask for installed (`-i`), taps (`-t`), or local (`-L`) data.
- **Output is data**: Every mode supports `--json`. Quiet mode
  strips decoration. Grep mode adds structure. The tool is a
  data source for other tools.

## Reference Projects

### CLI Design
- **ripgrep**: Smart defaults, regex power, respects `.gitignore`
- **fd**: Simpler find, sensible defaults, colorful
- **fzf**: Composition target — everything pipes to fzf
- **bat**: Progressive enhancement of cat

### Package Search
- **lib-rs-search (crs)**: Sibling project. Cartesian design system,
  multi-format output, self-describing JSON envelope.
- **homebrew/brew**: The upstream. `brew search` is correct but slow
  (subprocess + GitHub API). We cache its data.

### Data & Caching
- **sqlite-utils**: The database layer. Simon Willison's toolkit.
- **bkt**: CLI output caching. Similar spirit, different scope.

### Testing
- **ppx_expect / cram**: Inline expected output. Our `expect()` tests
  put the expected output right in the test file.
- **insta**: Rust snapshot testing. Our `snap.assert_match()` pattern.

## Taste Gradient (What's Next)

Near term:
- Meta envelope on `--json` search results
- `--select col1,col2` column projection
- Shell completions (zsh, fish, bash)

Medium term:
- `--markdown` output format (for pasting into docs/PRs)
- `--plain` tab-separated (like `-g` but with headers)
- `brew-hop-search diff <name>` — version delta between installed and current
- Color theme support (config file)

Far term:
- TUI mode (fzf-style interactive search)
- Homebrew tap as install method
- Plugin system for custom sources
