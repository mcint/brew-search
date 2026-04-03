# Security Policy

## Reporting Vulnerabilities

Reports are accepted via age-encrypted email.

**Email:** security@pkgs.mcint.io

**age public key:**
```
age1TODO_REPLACE_WITH_YOUR_AGE_PUBLIC_KEY
```

Encrypt your report with:
```sh
echo "report text" | age -r age1TODO... | mail -s "brew-search security" security@pkgs.mcint.io
```

Or attach a file:
```sh
age -r age1TODO... -o report.age report.txt
```

We will acknowledge receipt within 72 hours and aim to provide an initial assessment within 7 days.

## Threat Model & Risk Analysis

brew-search has a **low overall risk profile** due to its narrow scope: it fetches well-known public indexes, parses structured data, and writes to a local SQLite database. There is no authentication, no credential handling, and no outbound data beyond HTTP GETs.

### Network surface

| Endpoint | Purpose | Trust |
|----------|---------|-------|
| `formulae.brew.sh/api/formula.json` | Official Homebrew formula index | First-party, HTTPS |
| `formulae.brew.sh/api/cask.json` | Official Homebrew cask index | First-party, HTTPS |
| `pypi.org/pypi/brew-search/json` | Version check (read-only) | Well-known registry, HTTPS |

All URLs are hardcoded constants — no user-supplied URLs are fetched in the default code path.

### Local data sources

| Source | Access | Risk |
|--------|--------|------|
| `$(brew --cache)/api/*.json` | Read-only, brew-managed | Low — files written by brew itself |
| `$(brew --repo)/Library/Taps/**/*.rb` | Read-only, regex-parsed | **Medium** — see below |
| `brew info --json=v2 --installed` | Subprocess, stdout parsed | Low — first-party brew CLI |

### Tap .rb parsing (medium risk)

Tap formula files are Ruby source fetched from third-party git repositories. brew-search parses them with simple regexes (`desc`, `homepage`, `version`, `url` fields) — it does **not** execute Ruby or eval any content. The parsed strings are stored in SQLite via parameterized queries (sqlite-utils), so SQL injection via crafted `.rb` content is not feasible.

The residual risk is:
- A malicious tap could craft `.rb` content that produces misleading search results (e.g., a `desc` claiming to be a different tool). This is cosmetic, not exploitable.
- File paths are derived from directory traversal of `Library/Taps/`, not from `.rb` file content, so path traversal is not a vector.

### SQLite database

The FTS5 database at `~/.cache/brew-search/brew-search.db` is user-local, written with parameterized queries via sqlite-utils, and contains only public package metadata. It has no sensitive content and can be safely deleted at any time (`brew-search --refresh` rebuilds it).

### Subprocess calls

brew-search invokes:
- `brew --repository`, `brew --cache` — path discovery, no user input
- `brew info --json=v2 --installed` — installed package listing
- `sys.executable -m brew_search.cli` / `sys.executable -m brew_search._bg_installed` — background self-invocation

No user-supplied strings are interpolated into subprocess arguments.

## Supported Versions

Security fixes are applied to the latest release only.
