# search

Search Homebrew formulae, casks, taps, and installed packages by keyword.

## Purpose

Find packages by name or description. Default mode — what runs when
you type `brew-hop-search python`.

## Input

- **query**: Space-separated terms (AND-matched, all must hit)
- **sources**: `-f`, `-c`, `-i`, `-t`, `-L` (composable)
- **paging**: `-n N[+OFF]` (default: 20)
- **cache control**: `--refresh[=DUR]`, `--stale DUR`
- **format**: `-q`, `-g`, `--json`, `--csv`, `--tsv`, `--table`, `--sql`, `-v`, `-vv`

## Output

### Default (verbosity 1)

```
  # formulae (3/8307)  • brew install python@3.13
    python@3.13  3.13.2  Interpreted, interactive, object-oriented programming language  │ https://www.python.org/
    python-build  1.4.2  Simple, correct PEP 517 build frontend  │ https://github.com/pypa/build
```

- Section header per source kind
- 4-space indent, no source tag
- Name (bold, colored by source), version (dim), description, homepage (dim, after `│`)

### Verbose (verbosity 2, `-v`)

```
  -- cache: 2h old   searching formula + cask
  # formulae (3/8307)  • brew install python@3.13
  f python@3.13  3.13.2  ...
```

- Cache age + source summary header
- Source indicator column: `f`/`c`/`t`/`i`

### Quiet (verbosity 0, `-q`)

```
python@3.13  3.13.2  Interpreted, interactive, object-oriented programming language  │ https://www.python.org/
```

- No headers, no indent, no source tags

### Grep (`-g`)

```
python@3.13	3.13.2	https://www.python.org/
  Interpreted, interactive, object-oriented programming language
```

- Tab-separated: slug, version, URL
- Description on next line, indented

### JSON (`--json`)

Raw JSON array (single source) or object keyed by source kind.
See [ENVELOPE.md](../ENVELOPE.md) for structure.

### CSV (`--csv`)

```csv
source,name,version,description,homepage
f,python@3.13,3.13.2,"Interpreted, interactive, object-oriented programming language",https://www.python.org/
```

Standard CSV with header row. Pipes to `qsv`, spreadsheets, pandas.

### TSV (`--tsv`)

```
source	name	version	description	homepage
f	python@3.13	3.13.2	Interpreted, interactive...	https://www.python.org/
```

Tab-separated with header row. Pipes to `awk`, `cut`, `sort`.

### Table (`--table`)

```
S  Name         Ver     Description                     Homepage
-  -----------  ------  ------------------------------  -------------------------
f  python@3.13  3.13.2  Interpreted, interactive, ob…   https://www.python.org/
```

Aligned columns like `sqlite3 -column`. Description capped at 50 chars, homepage at 40.

### SQL (`--sql`)

```sql
CREATE TABLE IF NOT EXISTS results (...);
INSERT INTO results VALUES ('f', 'python@3.13', '3.13.2', '...', '...');
```

SQLite INSERT statements. Pipe to `sqlite3` to build a queryable local table.

## Data Sources

| Source | Table | Primary Key | FTS Columns |
|--------|-------|-------------|-------------|
| Remote API | `formula` | `name` | `name`, `desc` |
| Remote API | `cask` | `token` | `token`, `name`, `desc` |
| Installed | `installed_formula` | `name` | `name`, `desc` |
| Installed | `installed_cask` | `token` | `token`, `name`, `desc` |
| Taps | `tap` | `slug` | `name`, `tap`, `desc` | + `added_at`, `modified_at` |
| Local | `local_formula` | `name` | `name`, `desc` |
| Local | `local_cask` | `token` | `token`, `name`, `desc` |

## Search Algorithm

1. **FTS pass**: Query FTS5 index with `"term1"* AND "term2"*` (prefix, porter stemmer), fetch up to 200 candidates
2. **Fallback**: If no FTS table, full table scan
3. **Scoring**: Per-term additive scoring:
   - Exact name match: +100
   - Name starts with term: +60
   - Substring in name: +30
   - Match in description: +10
   - Any term unmatched: score = 0 (disqualified)
4. **Sort**: Score descending, then name ascending
5. **Slice**: Apply offset and limit

## Cache Behavior

- **Default TTL**: Background refresh if older than 6h (`--stale`)
- **Force**: `--refresh` fetches synchronously
- **Conditional**: `--refresh=1h` fetches only if older than 1h
- **Background**: Spawns detached subprocess, non-blocking

## Examples

```sh
brew-hop-search python              # formulae + casks
brew-hop-search -f python build     # multi-word, formulae only
brew-hop-search -i                  # list all installed
brew-hop-search -i -c               # installed casks only
brew-hop-search -q python | fzf     # pipe to fzf
brew-hop-search -n 5+20 python      # 5 results starting at position 20
brew-hop-search --json python | jq  # structured output
brew-hop-search --csv python | qsv sort -s name  # sort by name
brew-hop-search --tsv python | sort -t$'\t' -k3  # sort by version
brew-hop-search --table python      # aligned columns
brew-hop-search --sql python | sqlite3 results.db  # import to sqlite
```
