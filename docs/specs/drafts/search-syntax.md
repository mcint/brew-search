# Search Query Syntax — Comparables (draft)

> **Status**: initial syntax shipped. See
> [../features/search.md#query-syntax](../features/search.md#query-syntax) for
> the canonical spec. This doc is kept as the rationale / research record;
> future extensions (regex `/…/`, `OR`, case qualifier) live as Open Questions
> at the bottom.

## Purpose

Today `brew-hop-search foo bar` splits on whitespace into AND-matched terms,
each scored as substring/prefix/exact against `name` and `desc`. That's enough
for casual search but can't express:

- **Anchored matches**: `^python` (name starts with), `python$` (name ends with),
  `^python$` (exact name)
- **Field scoping**: "match only in name" vs "only in description"
- **Phrase matching**: a search term that itself contains whitespace
- **Negation**: exclude a term

This doc surveys well-known query mini-languages, picks the closest fit, and
proposes syntax for an implementation spec to follow. No code change yet.

## Comparables

### A. fzf extended-search syntax

`^foo` prefix, `foo$` suffix, `^foo$` exact, `'foo` exact-substring (no fuzzy),
`!foo` negate, `foo | bar` OR within a token group. Whitespace = AND.

**Pros**: purpose-built for terminal filtering; users who pipe `bhs -q | fzf`
already know it; no shell-escaping gotchas beyond the usual `^`/`$` quoting;
extremely compact (no `name:` needed — `^` implies "from the start").

**Cons**: no field scoping — fzf filters a single stream, we have two fields
(name, desc). Phrase handling via `'foo\ bar` is awkward.

**Link**: https://github.com/junegunn/fzf#search-syntax

### B. Lucene / GitHub code search qualifiers

`name:foo desc:"interactive language" name:/py.*/`. Field prefix plus
quoted phrases plus `/regex/`. Whitespace between tokens = implicit AND.

**Pros**: field scoping is explicit and obvious; quoted phrases are the one
universal convention for whitespace-bearing terms; millions of users know
it from GitHub search.

**Cons**: verbose (`name:^python$` is longer than `^python`); `/regex/` opens
a can of worms (anchoring, flavor — PCRE? RE2? Python `re`?).

**Link**: https://docs.github.com/en/search-github/searching-on-github

### C. SQLite FTS5 query syntax

Already what the backend speaks: `name:foo`, `"exact phrase"`, `foo*`,
`foo AND bar`, `foo OR bar`, `NOT foo`, `^foo` (token-at-start-of-column).

**Pros**: zero translation layer — pass the user's query straight to FTS5.
Column filter and phrase quoting are first-class.

**Cons**: FTS5's `^` means "first token in any indexed column" — not
"string starts with", which is what users typing `^python` expect. FTS5 has
no `$`. FTS5 is tokenized, so `^python$` ≠ "exact string python"; it means
"first token is python and that's the only token" — close but subtly different
from what non-FTS users expect. Leaky abstraction.

**Link**: https://www.sqlite.org/fts5.html#full_text_query_syntax

### D. grep / ripgrep (regex-first)

`-e '^python'`, `-e 'python$'`, full PCRE. Field scoping via separate flags
(`--name`, `--desc`).

**Pros**: maximum power; `^`/`$` work exactly as users expect from shell
experience; no new mini-language.

**Cons**: shell escaping is painful (`$` expansion, `|` pipes, `(` grouping);
regex is overkill for 95% of what users want; "search for `c++`" becomes a
surprise. Users would need to quote every query.

**Link**: https://github.com/BurntSushi/ripgrep

### E. brew search (status quo)

`brew search /regex/`, otherwise plain substring, no field control. Very
minimal, but the `/.../ = regex` convention is a precedent in the ecosystem.

**Link**: https://docs.brew.sh/Manpage#search-options-texttextregex-

## Comparison table

| Capability          | fzf (A) | Lucene (B) | FTS5 (C) | grep (D) | brew (E) |
|---------------------|---------|------------|----------|----------|----------|
| `^name` anchor      | ✓       | via regex  | ~token   | ✓        | via `/…/`|
| `name$` anchor      | ✓       | via regex  | ✗        | ✓        | via `/…/`|
| Field scoping       | ✗       | ✓          | ✓        | via flag | ✗        |
| Phrase w/ spaces    | awkward | `"…"`      | `"…"`    | quote    | via `/…/`|
| Negation            | `!foo`  | `-foo`     | `NOT`    | `-v`     | ✗        |
| Full regex          | ✗       | `/…/`      | ✗        | ✓        | `/…/`    |
| Shell-friendly      | ✓       | ✓          | ✓        | needs ✓  | ✓        |
| User familiarity    | high    | very high  | low      | high     | medium   |

## Recommendation — hybrid (fzf anchors + Lucene field prefix + quoted phrases)

Smallest surface that covers all three asks:

```
[field:]pattern
```

Where `pattern` is one of:

| Form         | Meaning                                |
|--------------|----------------------------------------|
| `foo`        | substring (current behavior)           |
| `^foo`       | starts with `foo`                      |
| `foo$`       | ends with `foo`                        |
| `^foo$`      | exact match                            |
| `"foo bar"`  | literal substring including whitespace |
| `!foo`       | negate (all matches must NOT contain)  |

And `field:` is optional, one of `name:`, `desc:` (alias: `description:`).
Bare tokens default to "name OR desc" (current behavior). Multiple tokens
are AND-joined, matching today's semantics.

**Examples**

```
bhs ^python                  # names starting with python
bhs '^python$'               # exact name "python"
bhs 'name:^py' desc:build    # name starts with py, desc contains build
bhs '"machine learning"'     # desc (or name) literal substring
bhs ^py !python@3.9          # starts with py, not the 3.9 variant
```

**Why this hybrid**:

- Anchors (`^`, `$`) are the most-asked feature and the fzf-style inline form
  is the shortest notation that's also familiar.
- `name:` / `desc:` prefixes are strictly opt-in; unqualified queries keep
  working exactly as today — zero migration cost.
- Quoted phrases are the one universal convention across every search UI
  the user has ever touched (Google, GitHub, email). Nothing to learn.
- No regex `/…/` in v1 — FTS5 can't power it and a Python-side fallback on
  200k rows is a slippery slope. Revisit once users actually ask.

## Implementation sketch (not a spec — just a feasibility note)

1. Tokenize the query into terms, respecting `"…"` quoting (shlex-style).
2. Per term, strip optional `name:` / `desc:` prefix, strip leading `!` for
   negation, strip leading `^` / trailing `$` for anchor flags.
3. FTS5 pre-filter: for unanchored substring terms, keep the existing
   `"term"*` prefix query (fast). For anchored/phrase/field-specific terms,
   widen the candidate pull or fall back to scan on the ~200-candidate pool.
4. Python-side post-filter: each candidate must satisfy every term's
   (field, anchor-mode, negate, literal) predicate.
5. Scoring stays additive; anchored-exact beats prefix beats substring (the
   existing scale already encodes this — reuse it).

## Open questions

- **Case**: keep today's case-insensitive default? Add `case:` qualifier
  later if asked.
- **Escaping `^`/`$` in a literal query**: users who actually want to find
  `foo^` (rare in brew names) can quote: `'foo^'`. Document it in `--help`.
- **Man page vs `--help`**: which surface owns the full syntax table? Current
  convention per [help.md](help.md) draft: `--help` shows examples, man page
  shows the full grammar. Same here.
- **Tap/installed sources**: syntax applies uniformly — `name:` on taps maps
  to the `name` column, on casks maps to `token OR name` (matches current
  scoring behavior).

## Related

- [docs/specs/features/search.md](../features/search.md) — current semantics
- [docs/specs/drafts/help.md](help.md) — where this syntax gets documented
- [docs/COMPARABLES.md](../../COMPARABLES.md) — fzf, ripgrep entries already
  there; this doc drills into their query syntaxes specifically.
