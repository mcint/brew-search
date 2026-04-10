# outdated

Detect packages where the installed version differs from the current index version.

## Purpose

Quick local outdated check without calling `brew outdated` (which is
slow and requires network). Optional `--brew-verify` for authoritative results.

## Input

- **flag**: `-O` / `--outdated`
- **format**: `--json`
- **authority**: `--brew-verify` (use brew subprocess instead of local comparison)

No query, no paging, no source flags.

## Output

### Default

```
  # outdated formulae (3)
    python@3.13  3.13.1 → 3.13.2
    node  21.6.0 → 21.6.1  [pinned]

  # outdated casks (1)
    firefox  121.0 → 122.0
```

- Section headers for formulae and casks
- Per-item: name, installed version → current version
- Tags: `[pinned]`, `[keg-only]` (formulae), `[auto-updates]` (casks, `--brew-verify` only)
- Footer hints: `brew upgrade`, `brew pin`, `-H` for history

### JSON

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

## Comparison Logic

### Fast Mode (default)

Compares installed index (`-i` cache) against API index:

- **Formulae**: Compare `version` + `_revision` from raw JSON
- **Casks**: Compare `version` string directly
- **Excluded**: Casks with `version "latest"`
- **Invisible**: Tap-only formulae not in the main API index

### Authoritative Mode / Diff (`--brew-verify`)

When `--brew-verify` is used, **both** fast and brew are run, and the
output is a package-matched diff showing where they agree and disagree.

```
  # outdated formulae (5)  ~3 +1 -1
  ~ python@3.13  3.13.1 → 3.13.2
  ~ node  21.6.0 → 21.6.1  [pinned]
  ~ wget  1.24.4 → 1.24.5_1|1.24.5  [keg-only]
  + tap-only-pkg  1.0 → 1.1  [brew-only]
  - false-positive  2.0 → 2.1  [bhs-only]
```

**Diff prefixes**:
- `~` both agree the package is outdated (version may differ in detail)
- `+` only brew found it outdated (bhs missed — tap-only, bottle rebuild, etc.)
- `-` only bhs found it outdated (brew disagrees — likely a false positive)

**Version word-diff**: When both report a package as outdated but with
different target versions, both are shown: `bhs_ver|brew_ver`

### JSON with diff

```json
{
  "bhs": { "formulae": [...], "casks": [...] },
  "brew": { "formulae": [...], "casks": [...] }
}
```

## Data Sources

- Installed index: `installed_formula`, `installed_cask` tables
- API index: `formula`, `cask` tables (raw JSON for version comparison)
- Brew subprocess: `brew outdated --json=v2` (only with `--brew-verify`)

## Cache Behavior

Ensures both installed and API caches exist before comparing.
No dedicated cache — piggybacks on existing source caches.

## Examples

```sh
brew-hop-search -O                     # fast local outdated
brew-hop-search -O --brew-verify       # diff: fast vs brew
brew-hop-search -O --json              # for scripts
brew-hop-search -O --brew-verify --json  # both results as JSON
brew-hop-search -O --json | jq '.outdated_formulae | length'
```
