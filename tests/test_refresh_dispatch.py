# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for the dispatch layer between `--refresh=KIND` parsing and the
source-module `ensure_cache` calls.

`tests/test_refresh.py` covers the parser. This file covers what the CLI
actually does once parsing succeeds — i.e. the missing layer that let
`--refresh=taps` quietly do nothing in the 2026-05-18 session.
"""
from __future__ import annotations

import subprocess
import sys

import pytest


def _patch_sources(monkeypatch):
    """Replace every source's ensure_cache with a call recorder.

    Returns a dict {kind: list[bool]} where each list is the sequence of
    `force` values seen for that kind. The CLI's dispatch logic is what
    we're verifying; the actual scanners stay out of the way.
    """
    calls: dict[str, list[bool]] = {
        "api_formula": [], "api_cask": [],
        "installed": [], "taps": [], "local": [],
    }

    def fake_api(kind, url, force=False, *a, **kw):
        calls[f"api_{kind}"].append(bool(force))
        return True

    def fake_installed(force=False, *a, **kw):
        calls["installed"].append(bool(force))
        return True

    def fake_taps(force=False, *a, **kw):
        calls["taps"].append(bool(force))
        return True

    def fake_local(force=False, *a, **kw):
        calls["local"].append(bool(force))
        return True

    monkeypatch.setattr("brew_hop_search.sources.api.ensure_cache", fake_api)
    monkeypatch.setattr("brew_hop_search.sources.installed.ensure_cache", fake_installed)
    monkeypatch.setattr("brew_hop_search.sources.taps.ensure_cache", fake_taps)
    monkeypatch.setattr("brew_hop_search.sources.local.ensure_cache", fake_local)
    return calls


# ── --refresh=KIND with a query, no source flag ────────────────────────────

def test_refresh_taps_with_query_forces_taps_refresh(monkeypatch, tmp_path):
    """`bhs --refresh=taps foo` must force-refresh taps even without -T."""
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(tmp_path / "db.sqlite"))
    calls = _patch_sources(monkeypatch)
    # Stop search before any FTS work — we only care about dispatch.
    monkeypatch.setattr("brew_hop_search.search.search", lambda *a, **kw: [])

    from brew_hop_search.cli import main
    try:
        main(["--refresh=taps", "foo"])
    except SystemExit:
        pass

    assert calls["taps"] == [True], (
        "Expected taps.ensure_cache(force=True) to fire when "
        "--refresh=taps is given. Got: " + repr(calls)
    )


def test_refresh_local_with_query_forces_local_refresh(monkeypatch, tmp_path):
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(tmp_path / "db.sqlite"))
    calls = _patch_sources(monkeypatch)
    monkeypatch.setattr("brew_hop_search.search.search", lambda *a, **kw: [])

    from brew_hop_search.cli import main
    try:
        main(["--refresh=local", "foo"])
    except SystemExit:
        pass

    assert calls["local"] == [True], repr(calls)


def test_refresh_does_not_force_unrequested_sources(monkeypatch, tmp_path):
    """`--refresh=taps foo` must not force-refresh local or installed."""
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(tmp_path / "db.sqlite"))
    calls = _patch_sources(monkeypatch)
    monkeypatch.setattr("brew_hop_search.search.search", lambda *a, **kw: [])

    from brew_hop_search.cli import main
    try:
        main(["--refresh=taps", "foo"])
    except SystemExit:
        pass

    assert calls["installed"] == [], repr(calls)
    assert calls["local"] == [], repr(calls)


# ── source flag already set: don't double-call ─────────────────────────────

# ── standalone --refresh=KIND (no query, no source flag) ───────────────────

def test_refresh_taps_only_no_query(monkeypatch, tmp_path, capsys):
    """`bhs --refresh=taps` (no query) refreshes taps and exits — does
    not print the usage banner."""
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(tmp_path / "db.sqlite"))
    calls = _patch_sources(monkeypatch)

    from brew_hop_search.cli import main
    main(["--refresh=taps"])

    assert calls["taps"] == [True]
    out = capsys.readouterr()
    # Stdout must NOT carry the "try:" usage banner.
    assert "try:" not in out.out
    assert "brew-hop-search python" not in out.out
    # Stderr should carry the per-kind status line.
    assert "[cache] taps" in out.err


def test_refresh_all_runs_every_kind(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(tmp_path / "db.sqlite"))
    calls = _patch_sources(monkeypatch)

    from brew_hop_search.cli import main
    main(["--refresh=all"])

    assert calls["api_formula"] == [True]
    assert calls["api_cask"] == [True]
    assert calls["installed"] == [True]
    assert calls["taps"] == [True]
    assert calls["local"] == [True]


def test_refresh_only_does_not_run_unselected_kinds(monkeypatch, tmp_path):
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(tmp_path / "db.sqlite"))
    calls = _patch_sources(monkeypatch)

    from brew_hop_search.cli import main
    main(["--refresh=taps"])

    assert calls["installed"] == []
    assert calls["local"] == []
    assert calls["api_formula"] == []
    assert calls["api_cask"] == []


def test_refresh_only_verbose_reports_total(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(tmp_path / "db.sqlite"))
    _patch_sources(monkeypatch)

    from brew_hop_search.cli import main
    main(["--refresh=all", "-v"])

    err = capsys.readouterr().err
    # One line per kind plus a "total" footer.
    assert "[cache] local" in err
    assert "[cache] taps" in err
    assert "[cache] installed" in err
    assert "[cache] index" in err
    assert "[cache] total" in err


def test_refresh_taps_with_T_flag_no_double_call(monkeypatch, tmp_path):
    """`bhs -T --refresh=taps foo` shouldn't call ensure_cache twice for
    taps — the existing `-T` branch already covers it via _force()."""
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(tmp_path / "db.sqlite"))
    calls = _patch_sources(monkeypatch)
    monkeypatch.setattr("brew_hop_search.search.search", lambda *a, **kw: [])

    from brew_hop_search.cli import main
    try:
        main(["-T", "--refresh=taps", "foo"])
    except SystemExit:
        pass

    # Exactly one call, with force=True.
    assert calls["taps"] == [True], repr(calls)
