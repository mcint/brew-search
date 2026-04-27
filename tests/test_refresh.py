# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for --refresh / --fresh value parsing.

The flag accepts three shapes:
  - bare              → const=0 (force-refresh everything this command touches)
  - =DUR              → int seconds (legacy; refresh if older than DUR)
  - =KIND[,KIND...]   → frozenset (force-refresh only listed kinds)
"""
from __future__ import annotations

import argparse

import pytest

from brew_hop_search.cli import parse_refresh, REFRESH_KINDS


# ── happy paths ────────────────────────────────────────────────────────────

def test_duration_form():
    assert parse_refresh("6h") == 6 * 3600
    assert parse_refresh("30m") == 1800
    assert parse_refresh("90") == 90


@pytest.mark.parametrize("kind", ["index", "installed", "outdated",
                                   "taps", "local"])
def test_single_kind(kind):
    out = parse_refresh(kind)
    assert isinstance(out, frozenset)
    if kind == "outdated":
        # 'outdated' expands to its dependencies
        assert out == frozenset({"index", "installed"})
    else:
        assert out == frozenset({kind})


def test_multiple_kinds():
    out = parse_refresh("index,installed")
    assert out == frozenset({"index", "installed"})


def test_kind_all_expands():
    out = parse_refresh("all")
    assert out == frozenset({"index", "installed", "taps", "local"})


def test_kind_outdated_expands_to_index_and_installed():
    """`outdated` is derived from index+installed, so refreshing it means
    refreshing both inputs."""
    assert parse_refresh("outdated") == frozenset({"index", "installed"})
    # Combined with another kind: still expands.
    assert parse_refresh("outdated,taps") == frozenset({"index", "installed", "taps"})


def test_case_insensitive():
    assert parse_refresh("Index") == frozenset({"index"})
    assert parse_refresh("INDEX,Installed") == frozenset({"index", "installed"})


def test_whitespace_in_csv_kinds():
    assert parse_refresh("index, installed ,taps") == frozenset(
        {"index", "installed", "taps"}
    )


# ── error paths ────────────────────────────────────────────────────────────

def test_unknown_kind_clear_error():
    with pytest.raises(argparse.ArgumentTypeError) as exc:
        parse_refresh("frobnicate")
    msg = str(exc.value)
    # Must name the unknown kind AND list the valid set so the user can fix it.
    assert "frobnicate" in msg
    for k in REFRESH_KINDS:
        assert k in msg


def test_mixing_duration_and_kind_rejected():
    """`installed,6h` — '6h' is not a kind, so reject."""
    with pytest.raises(argparse.ArgumentTypeError) as exc:
        parse_refresh("installed,6h")
    assert "6h" in str(exc.value)


def test_empty_value_rejected():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_refresh("")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_refresh("   ")


def test_garbage_neither_duration_nor_kind():
    with pytest.raises(argparse.ArgumentTypeError) as exc:
        parse_refresh("nope")
    msg = str(exc.value)
    assert "nope" in msg
    # Hints at both forms it could have meant.
    assert "duration" in msg.lower() or "kind" in msg.lower()
