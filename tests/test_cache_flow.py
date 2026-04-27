# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for the cache-first stale flow primitives.

Covers:
- sentinel file write/read round-trip
- refresh tracker registration
- trailing_refresh_status: success, failure, timeout, ^C
- force_refresh_for / conditional_refresh_secs interpretation of --refresh
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time

import pytest


# ── sentinel primitives ────────────────────────────────────────────────────

def test_sentinel_round_trip(tmp_path):
    from brew_hop_search.cache import write_sentinel, read_sentinel
    p = tmp_path / "x.done"
    write_sentinel(p, duration_ms=1234, ok=True, msg="")
    out = read_sentinel(p)
    assert out == (1234, True, "")


def test_sentinel_missing_returns_none(tmp_path):
    from brew_hop_search.cache import read_sentinel
    assert read_sentinel(tmp_path / "nope.done") is None


def test_sentinel_records_failure_and_msg(tmp_path):
    from brew_hop_search.cache import write_sentinel, read_sentinel
    p = tmp_path / "fail.done"
    write_sentinel(p, duration_ms=42, ok=False, msg="DNS lookup failed")
    duration, ok, msg = read_sentinel(p)
    assert duration == 42
    assert ok is False
    assert msg == "DNS lookup failed"


def test_sentinel_atomic_write(tmp_path):
    """Tmp file shouldn't linger after a successful write."""
    from brew_hop_search.cache import write_sentinel
    p = tmp_path / "x.done"
    write_sentinel(p, 1, True)
    assert p.exists()
    assert not (tmp_path / "x.done.tmp").exists()


# ── refresh tracker ────────────────────────────────────────────────────────

def test_register_pending_refresh_visible(tmp_path):
    """A registered refresh shows up in pending_refreshes()."""
    from brew_hop_search.cache import register_pending_refresh, pending_refreshes
    # Test isolation: snapshot the existing list.
    before = list(pending_refreshes())
    register_pending_refresh("test-kind", tmp_path / "x.done")
    after = pending_refreshes()
    new = [e for e in after if e not in before]
    assert len(new) == 1
    assert new[0][0] == "test-kind"
    assert new[0][1] == tmp_path / "x.done"


# ── --refresh argv interpretation helpers ─────────────────────────────────

class _NS:
    """Minimal Namespace stand-in."""
    def __init__(self, refresh):
        self.refresh = refresh


def test_force_refresh_for_bare_means_all_kinds():
    from brew_hop_search.cli import force_refresh_for
    args = _NS(refresh=0)
    for k in ("index", "installed", "taps", "local"):
        assert force_refresh_for(args, k)


def test_force_refresh_for_kindset_filters():
    from brew_hop_search.cli import force_refresh_for
    args = _NS(refresh=frozenset({"installed"}))
    assert force_refresh_for(args, "installed")
    assert not force_refresh_for(args, "index")


def test_force_refresh_for_duration_means_no_force():
    """--refresh=6h is conditional, not force."""
    from brew_hop_search.cli import force_refresh_for
    args = _NS(refresh=6 * 3600)
    assert not force_refresh_for(args, "index")


def test_conditional_refresh_secs_returns_dur_only():
    from brew_hop_search.cli import conditional_refresh_secs
    assert conditional_refresh_secs(_NS(refresh=None)) is None
    assert conditional_refresh_secs(_NS(refresh=0)) is None
    assert conditional_refresh_secs(_NS(refresh=frozenset({"index"}))) is None
    assert conditional_refresh_secs(_NS(refresh=3600)) == 3600


# ── trailing_refresh_status ────────────────────────────────────────────────

@pytest.fixture
def fake_tty(monkeypatch):
    """Force the trailing-status helper to think stderr is a TTY."""
    import brew_hop_search.display as d
    monkeypatch.setattr(d, "USE_COLOR_STDERR", True)


@pytest.fixture
def clean_tracker():
    """Clear the module-level pending refresh tracker around the test."""
    import brew_hop_search.cache as c
    saved = list(c._pending_refreshes)
    c._pending_refreshes.clear()
    yield
    c._pending_refreshes.clear()
    c._pending_refreshes.extend(saved)


def test_trailing_status_no_pending_returns_immediately(fake_tty, clean_tracker, capsys):
    from brew_hop_search.display import trailing_refresh_status
    trailing_refresh_status()
    captured = capsys.readouterr()
    assert captured.err == ""


def test_trailing_status_completes_when_sentinel_appears(
    fake_tty, clean_tracker, capsys, tmp_path
):
    """Foreground polls the sentinel; once it appears, prints the done line."""
    from brew_hop_search.cache import (
        register_pending_refresh, write_sentinel,
    )
    from brew_hop_search.display import trailing_refresh_status

    spath = tmp_path / "ready.done"
    register_pending_refresh("index", spath)
    # Pre-write the sentinel so the first poll picks it up.
    write_sentinel(spath, duration_ms=250, ok=True)

    trailing_refresh_status(poll=0.01, max_wait=2.0)
    err = capsys.readouterr().err
    # Final line shows kind, ✓, duration in seconds.
    assert "index" in err
    assert "✓" in err
    assert "0.2" in err or "0.3" in err  # 250ms ≈ 0.2-0.3s


def test_trailing_status_reports_failure(
    fake_tty, clean_tracker, capsys, tmp_path
):
    from brew_hop_search.cache import (
        register_pending_refresh, write_sentinel,
    )
    from brew_hop_search.display import trailing_refresh_status

    spath = tmp_path / "fail.done"
    register_pending_refresh("installed", spath)
    write_sentinel(spath, 500, ok=False, msg="brew not found")

    trailing_refresh_status(poll=0.01, max_wait=2.0)
    err = capsys.readouterr().err
    assert "installed" in err
    assert "✗" in err
    assert "brew not found" in err


def test_trailing_status_times_out(
    fake_tty, clean_tracker, capsys, tmp_path
):
    """If the sentinel never appears within max_wait, surface a clear note."""
    from brew_hop_search.cache import register_pending_refresh
    from brew_hop_search.display import trailing_refresh_status

    spath = tmp_path / "stuck.done"
    register_pending_refresh("index", spath)

    # Very short wait → guaranteed timeout
    trailing_refresh_status(poll=0.01, max_wait=0.05)
    err = capsys.readouterr().err
    assert "still updating" in err


def test_trailing_status_skipped_when_not_tty(clean_tracker, capsys, tmp_path,
                                               monkeypatch):
    """Pipelines exit immediately — no blocking on bg refresh."""
    import brew_hop_search.display as d
    monkeypatch.setattr(d, "USE_COLOR_STDERR", False)
    from brew_hop_search.cache import register_pending_refresh
    from brew_hop_search.display import trailing_refresh_status

    register_pending_refresh("index", tmp_path / "anything.done")
    trailing_refresh_status(poll=0.01, max_wait=10.0)
    assert capsys.readouterr().err == ""
