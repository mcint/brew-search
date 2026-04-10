# Comparables

Python projects and CLI tools we learn from — what to adopt,
what to keep distance from, and where we're independently aligned.

## Adopting / Inspired By

### sqlite-utils (Simon Willison)
**What**: Our database layer. CLI + Python library for SQLite.
**Adopting**: FTS5 integration, `insert_all()` with pk, table introspection.
The "every dataset is a database" philosophy is core to how we cache.
**Link**: https://github.com/simonw/sqlite-utils

### click / typer
**What**: Python CLI frameworks.
**Observing**: typer's approach to composable commands and auto-generated help.
We use argparse directly — lighter dependency, full control over `--help`
formatting, and no magic. If we outgrow argparse, typer is the upgrade path.
**Link**: https://github.com/tiangolo/typer

### datasette (Simon Willison)
**What**: Instant JSON API for any SQLite database.
**Adopting the idea**: Our `--json`, `--csv`, `--table`, `--sql` output formats
follow the same principle — the cache is queryable data, not just an
implementation detail. `datasette` is what you'd point at our `.db` file
if you wanted a web UI.
**Link**: https://github.com/simonw/datasette

### qsv (jqnatividad)
**What**: Ultra-fast CSV toolkit. Successor to xsv.
**Adopting**: Column-oriented thinking. Our `--csv` output is designed to
pipe into `qsv select`, `qsv search`, `qsv sort`. The flat tabular
export makes our data a first-class input to the CSV ecosystem.
**Link**: https://github.com/jqnatividad/qsv

### ripgrep (BurntSushi)
**What**: Fast grep with smart defaults.
**Adopting**: Respect `.gitignore`, smart TTY detection, progressive
verbosity. ripgrep's "fast by default, configurable when needed"
is the template for our `-q` → default → `-v` → `-vv` ladder.
**Link**: https://github.com/BurntSushi/ripgrep

### fzf (junegunn)
**What**: Fuzzy finder for the terminal.
**Adopting**: Composition target. Our `-q` mode exists specifically
so `brew-hop-search -q python | fzf` works perfectly. No ANSI
in stdout when piped, clean one-per-line output.
**Link**: https://github.com/junegunn/fzf

### homebrew-cask (Homebrew)
**What**: The upstream cask system.
**Adopting**: Their JSON API schema is our data contract. We parse
their version/revision/installed structures exactly as brew does.
**Link**: https://github.com/Homebrew/homebrew-cask

## Intentionally Distant

### pip / pip-audit
**What**: Python package installer and security auditor.
**Distance**: pip's output is notoriously unstable for scripting —
format changes between versions, inconsistent exit codes, mixed
stdout/stderr. We commit to stable output via snapshot tests and
`--json` as a contract. pip-audit is excellent but solves a
different problem (security vs. search).
**Link**: https://github.com/pypa/pip

### brew (Homebrew CLI)
**What**: The package manager itself.
**Distance**: `brew search` calls the GitHub API (slow, rate-limited).
`brew outdated` spawns subprocesses and does network I/O by default.
We intentionally never call `brew` in default mode — HTTP to
formulae.brew.sh or pure local DB reads. When we do call brew
(`-i`, `-t`, `--brew-verify`), it's explicit and opt-in.
**Link**: https://github.com/Homebrew/brew

### nix-search / nix-env
**What**: Nix package search.
**Distance**: Nix search requires evaluating Nix expressions, which
can be slow and resource-intensive. We pre-index everything into
SQLite+FTS5 for instant queries. Different ecosystem, but the
"search should be instant" principle applies.

### rich (Will McGugan)
**What**: Rich text and beautiful formatting for the terminal.
**Distance**: Rich is excellent for TUI apps but is a heavy dependency
for a search tool. We use raw ANSI codes (7 color functions, <20 lines)
and stay dependency-minimal. If we add a TUI mode someday, rich or
textual would be the right choice then.
**Link**: https://github.com/Textualize/rich

## Independently Aligned

### bkt (dimo414)
**What**: CLI output caching tool.
**Alignment**: Same insight — cache expensive CLI output in SQLite,
serve stale while refreshing in background. We bake this in rather
than wrapping external commands, but the cache-first architecture
is the same.
**Link**: https://github.com/dimo414/bkt

### jq (stedolan)
**What**: JSON processor.
**Alignment**: Our `--json` output is designed to be jq-friendly.
`brew-hop-search --json python | jq '.[].name'` should always work.
We don't try to replicate jq's filtering — we produce clean data
for jq to consume.
**Link**: https://github.com/jqlang/jq

### lib-rs-search / crs (sibling project)
**What**: Rust crate search tool with the same design system.
**Alignment**: Shared author. Cartesian specs pattern (Feature × Input ×
Output × Envelope), verbosity ladder, snapshot testing, composable
output formats. Different ecosystem (crates.io vs Homebrew), same
design philosophy.
**Link**: ../lib-rs-search

### hyperfine (sharkdp)
**What**: CLI benchmarking tool.
**Alignment**: Clean defaults, `--export-json`/`--export-csv`,
progressive detail with `-v`. The "data tool that respects your
terminal" ethos is shared.
**Link**: https://github.com/sharkdp/hyperfine

### bat (sharkdp)
**What**: cat with syntax highlighting.
**Alignment**: Progressive enhancement — plain when piped, pretty
on TTY. Same auto-detection pattern we use for color output.
**Link**: https://github.com/sharkdp/bat

## Design Decisions by Reference

| Decision | Adopted From | Alternative We Rejected |
|----------|-------------|------------------------|
| SQLite + FTS5 for cache | sqlite-utils, datasette | Flat file grep, shelve, pickle |
| Raw ANSI over rich | ripgrep, bat | rich, blessed, curses |
| argparse over click/typer | stdlib simplicity | click (implicit dependency) |
| `--json` as contract | datasette, GitHub CLI | Unstructured text parsing |
| `-q` for pipe-friendliness | fzf, ripgrep | Always-decorated output |
| Background refresh | bkt | Blocking fetch on stale |
| No `brew` in default path | Original design | Shell out to brew search |
| Snapshot tests for output | ppx_expect, insta | Manual output inspection |
| Verbosity ladder | ripgrep, lib-rs-search | Single verbose flag |
| Multi-format export | qsv, datasette, hyperfine | JSON-only |
