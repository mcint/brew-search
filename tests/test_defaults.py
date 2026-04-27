# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for env-var-overridable defaults (12-factor short-timeout hooks)."""
from __future__ import annotations

import pytest

from brew_hop_search.defaults import (
    parse_duration,
    stale_api_seconds, stale_taps_seconds,
    stale_installed_seconds, stale_local_seconds,
)


def test_parse_duration_units():
    assert parse_duration("30s") == 30
    assert parse_duration("1m") == 60
    assert parse_duration("1h") == 3600
    assert parse_duration("1d") == 86400
    assert parse_duration("1h30m") == 5400
    assert parse_duration("90") == 90  # bare seconds


def test_parse_duration_rejects_garbage():
    with pytest.raises(ValueError):
        parse_duration("nope")


@pytest.mark.parametrize("name,fn,default", [
    ("STALE_API", stale_api_seconds, 6 * 3600),
    ("STALE_TAPS", stale_taps_seconds, 3600),
    ("STALE_INSTALLED", stale_installed_seconds, 3600),
    ("STALE_LOCAL", stale_local_seconds, 3600),
])
def test_env_override_sets_short_ttl(monkeypatch, name, fn, default):
    """Setting BREW_HOP_SEARCH_STALE_<KIND>=2s makes that TTL 2 seconds."""
    monkeypatch.delenv(f"BREW_HOP_SEARCH_{name}", raising=False)
    assert fn() == default
    monkeypatch.setenv(f"BREW_HOP_SEARCH_{name}", "2s")
    assert fn() == 2
    monkeypatch.setenv(f"BREW_HOP_SEARCH_{name}", "5m")
    assert fn() == 300


def test_env_override_falls_back_on_garbage(monkeypatch):
    """Garbled env value falls back to the built-in default rather than crashing."""
    monkeypatch.setenv("BREW_HOP_SEARCH_STALE_API", "🦆")
    assert stale_api_seconds() == 6 * 3600
