# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Query syntax: anchors, field prefixes, phrases, negation.

Grammar per docs/specs/features/search.md#query-syntax:

    [field:][!][^]pattern[$]

Tests are expect-style: the test body is the pre-registered intent
document — assert_match-free, so each test reads as one input → one
outcome pair.
"""
from __future__ import annotations

import pytest

from brew_hop_search.search import parse_query, Term


# ── parse_query: shape of parsed terms ──────────────────────────────────────


def test_parse_bare_term():
    assert parse_query("python") == [Term(field=None, negate=False,
                                          anchor_start=False, anchor_end=False,
                                          literal="python")]


def test_parse_prefix_anchor():
    assert parse_query("^python") == [Term(field=None, negate=False,
                                           anchor_start=True, anchor_end=False,
                                           literal="python")]


def test_parse_suffix_anchor():
    assert parse_query("python$") == [Term(field=None, negate=False,
                                           anchor_start=False, anchor_end=True,
                                           literal="python")]


def test_parse_exact_anchor():
    assert parse_query("^python$") == [Term(field=None, negate=False,
                                            anchor_start=True, anchor_end=True,
                                            literal="python")]


def test_parse_quoted_phrase():
    assert parse_query('"machine learning"') == [
        Term(field=None, negate=False, anchor_start=False, anchor_end=False,
             literal="machine learning")
    ]


def test_parse_quoted_phrase_with_anchors():
    # Anchors inside the quotes still bind to the pattern.
    assert parse_query('"^foo bar$"') == [
        Term(field=None, negate=False, anchor_start=True, anchor_end=True,
             literal="foo bar")
    ]


def test_parse_field_name():
    assert parse_query("name:python") == [
        Term(field="name", negate=False, anchor_start=False, anchor_end=False,
             literal="python")
    ]


def test_parse_field_desc_alias():
    # `d:` and `description:` both alias to `desc`
    assert parse_query("d:browser description:fast") == [
        Term(field="desc", negate=False, anchor_start=False, anchor_end=False,
             literal="browser"),
        Term(field="desc", negate=False, anchor_start=False, anchor_end=False,
             literal="fast"),
    ]


def test_parse_field_with_anchors():
    assert parse_query("name:^py") == [
        Term(field="name", negate=False, anchor_start=True, anchor_end=False,
             literal="py")
    ]


def test_parse_negation():
    assert parse_query("!python") == [
        Term(field=None, negate=True, anchor_start=False, anchor_end=False,
             literal="python")
    ]


def test_parse_negated_scoped_phrase():
    # Canonical order: field → negate → ^pattern$
    assert parse_query('!desc:"old api"') == [
        Term(field="desc", negate=True, anchor_start=False, anchor_end=False,
             literal="old api")
    ]


def test_parse_multiple_terms():
    terms = parse_query("^py !@3.9 desc:build")
    assert terms == [
        Term(field=None, negate=False, anchor_start=True, anchor_end=False,
             literal="py"),
        Term(field=None, negate=True, anchor_start=False, anchor_end=False,
             literal="@3.9"),
        Term(field="desc", negate=False, anchor_start=False, anchor_end=False,
             literal="build"),
    ]


def test_parse_empty():
    assert parse_query("") == []
    assert parse_query("   ") == []


def test_parse_case_fold_literal():
    # Literals are lowercased during parse so the matcher is a plain str op.
    t = parse_query("Python")[0]
    assert t.literal == "python"


# ── Term.matches: predicate behavior ────────────────────────────────────────


def _fm(name: str, desc: str = "") -> dict:
    return {"name": name, "desc": desc}


def test_match_bare_substring_hits_name_or_desc():
    t = parse_query("python")[0]
    assert t.matches(_fm("python@3.13", "interpreted language"))
    assert t.matches(_fm("foo", "python bindings"))
    assert not t.matches(_fm("ruby", "a gem"))


def test_match_prefix_anchor():
    t = parse_query("^py")[0]
    assert t.matches(_fm("python", ""))
    assert t.matches(_fm("foo", "python bindings"))  # desc also anchors
    assert not t.matches(_fm("cpython", ""))


def test_match_suffix_anchor():
    t = parse_query("search$")[0]
    assert t.matches(_fm("brew-hop-search", ""))
    assert not t.matches(_fm("searcher", ""))


def test_match_exact_anchor():
    t = parse_query("^python$")[0]
    assert t.matches(_fm("python", "anything"))
    assert not t.matches(_fm("python@3.13", ""))
    # Exact can still hit via desc if desc equals the literal
    assert t.matches(_fm("foo", "python"))


def test_match_scoped_to_name():
    t = parse_query("name:^py")[0]
    assert t.matches(_fm("python", "anything"))
    assert not t.matches(_fm("ruby", "python bindings"))  # desc doesn't count


def test_match_scoped_to_desc():
    t = parse_query("desc:browser")[0]
    assert t.matches(_fm("firefox", "a web browser"))
    assert not t.matches(_fm("browser", "something else"))


def test_match_phrase_with_whitespace():
    t = parse_query('"machine learning"')[0]
    assert t.matches(_fm("scikit", "machine learning toolkit"))
    assert not t.matches(_fm("foo", "machine-learning toolkit"))  # needs space


def test_match_negation():
    t = parse_query("!@3.9")[0]
    assert t.matches(_fm("python@3.13", "interpreted"))
    assert not t.matches(_fm("python@3.9", "interpreted"))


def test_match_negation_scoped():
    t = parse_query('!name:legacy')[0]
    assert t.matches(_fm("modern-tool", "legacy replacement"))  # desc doesn't fail it
    assert not t.matches(_fm("legacy-tool", "anything"))


# ── cask/tap scope: name: matches token OR localized name ────────────────────


def test_match_cask_name_covers_token_and_aliases():
    t = parse_query("name:firefox")[0]
    # Cask convention: name: scans token ∪ name[] (both lowercased)
    cask = {"token": "firefox", "name": "Firefox", "desc": "browser"}
    assert t.matches(cask)
    cask2 = {"token": "visual-studio-code", "name": "Visual Studio Code",
             "desc": "editor"}
    t2 = parse_query("name:visual")[0]
    assert t2.matches(cask2)


# ── search() integration: rank order preserved ──────────────────────────────


def test_integration_exact_beats_prefix_beats_substring():
    """Exact match scores highest; prefix next; substring last."""
    from brew_hop_search.search import score_term

    t_exact = parse_query("^python$")[0]
    t_prefix = parse_query("^python")[0]
    t_sub = parse_query("python")[0]

    # Same record — each anchor tier scores its own ceiling.
    rec = _fm("python", "interpreter")
    assert score_term(t_exact, rec) == 100  # ^python$ = exact
    assert score_term(t_prefix, rec) == 60  # ^python = prefix tier
    assert score_term(t_sub, rec) == 100  # unanchored: name equals literal

    rec2 = _fm("python@3.13", "interpreter")
    assert score_term(t_exact, rec2) == 0  # doesn't match, predicate fails
    assert score_term(t_prefix, rec2) == 60
    # Bare `python` also hits as prefix since name starts with it; legacy
    # scorer had the same bias (prefix > substring, regardless of anchor).
    assert score_term(t_sub, rec2) == 60

    rec3 = _fm("ipython", "interpreter")
    # Now substring-only (not a prefix): 30
    assert score_term(t_sub, rec3) == 30
