# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for the install history log."""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def hist_db(tmp_path, monkeypatch):
    """Point the cache at a tmp DB and return its path."""
    db_path = tmp_path / "history.db"
    monkeypatch.setenv("BREW_HOP_SEARCH_DB", str(db_path))
    yield db_path


def test_record_installed_uses_installed_version_not_index(hist_db):
    """Regression for: -H showed the index `versions.stable`, not the
    actually-installed version. The point of the history log is to know
    *what was installed* on this machine."""
    from brew_hop_search.history import record_installed, get_history

    formulae = [{
        "name": "python@3.13",
        "versions": {"stable": "3.13.5"},   # index says 3.13.5
        "installed": [{"version": "3.13.1"}],  # but we have 3.13.1
    }]
    record_installed(formulae, casks=[])

    rows = get_history("python@3.13")
    assert [r["version"] for r in rows] == ["3.13.1"], (
        "history must record the installed version, not the index version"
    )


def test_record_installed_logs_each_keg(hist_db):
    """Side-by-side kegs: each installed version gets its own row."""
    from brew_hop_search.history import record_installed, get_history

    formulae = [{
        "name": "openssl@3",
        "versions": {"stable": "3.5.0"},
        "installed": [{"version": "3.4.0"}, {"version": "3.4.1"}],
    }]
    record_installed(formulae, casks=[])

    versions = sorted(r["version"] for r in get_history("openssl@3"))
    assert versions == ["3.4.0", "3.4.1"]


def test_record_installed_skips_orphan_no_install(hist_db):
    """Formula in the index but with no installed[] array: don't record."""
    from brew_hop_search.history import record_installed, get_history

    formulae = [{
        "name": "ghost",
        "versions": {"stable": "1.0"},
        "installed": [],
    }]
    record_installed(formulae, casks=[])
    assert get_history("ghost") == []


def test_record_installed_cask_prefers_installed(hist_db):
    """Casks: `installed` field reflects what's on disk. If absent, fall
    back to the cask's `version` field."""
    from brew_hop_search.history import record_installed, get_history

    casks = [
        {"token": "firefox", "version": "200.0", "installed": "121.0"},
        {"token": "iterm2", "version": "3.5.0"},  # no installed field
    ]
    record_installed(formulae=[], casks=casks)

    assert [r["version"] for r in get_history("firefox")] == ["121.0"]
    assert [r["version"] for r in get_history("iterm2")] == ["3.5.0"]


def test_record_installed_dedupes_same_version(hist_db):
    """Re-running with the same installed version doesn't grow the log."""
    from brew_hop_search.history import record_installed, get_history

    formulae = [{
        "name": "node",
        "versions": {"stable": "21.6.1"},
        "installed": [{"version": "21.6.0"}],
    }]
    record_installed(formulae, casks=[])
    record_installed(formulae, casks=[])

    rows = get_history("node")
    assert len(rows) == 1
    assert rows[0]["version"] == "21.6.0"
