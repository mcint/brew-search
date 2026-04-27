# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for the TOML config + env layer that sets default output format.

Resolution order: CLI flag > env > TOML config > built-in default.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest


# ── unit: resolve_output_format() ──────────────────────────────────────────

@pytest.fixture
def cfg_env(tmp_path, monkeypatch):
    """Point the config layer at a tmp config file and clean env."""
    cfg = tmp_path / "config.toml"
    monkeypatch.setenv("BREW_HOP_SEARCH_CONFIG", str(cfg))
    monkeypatch.delenv("BREW_HOP_SEARCH_FORMAT", raising=False)
    yield cfg


def test_no_config_no_env_returns_none(cfg_env):
    from brew_hop_search._config import resolve_output_format
    assert resolve_output_format() is None


def test_env_canonicalizes_aliases(cfg_env, monkeypatch):
    from brew_hop_search._config import resolve_output_format
    monkeypatch.setenv("BREW_HOP_SEARCH_FORMAT", "long")
    assert resolve_output_format() == "multi"
    monkeypatch.setenv("BREW_HOP_SEARCH_FORMAT", "JSON:Short")
    assert resolve_output_format() == "json:short"
    monkeypatch.setenv("BREW_HOP_SEARCH_FORMAT", "tty")
    assert resolve_output_format() == "default"


def test_env_overrides_config(cfg_env, monkeypatch):
    from brew_hop_search._config import resolve_output_format
    cfg_env.write_text('[output]\ndefault = "csv"\n')
    monkeypatch.setenv("BREW_HOP_SEARCH_FORMAT", "multi")
    assert resolve_output_format() == "multi"


def test_config_used_when_env_unset(cfg_env):
    from brew_hop_search._config import resolve_output_format
    cfg_env.write_text('[output]\ndefault = "table"\n')
    assert resolve_output_format() == "table"


def test_unknown_name_in_env_falls_through_to_config(cfg_env, monkeypatch):
    """Garbage env value doesn't blank out an otherwise-good config value."""
    from brew_hop_search._config import resolve_output_format
    cfg_env.write_text('[output]\ndefault = "csv"\n')
    monkeypatch.setenv("BREW_HOP_SEARCH_FORMAT", "🦆")
    assert resolve_output_format() == "csv"


# ── integration: format applied to a real query ────────────────────────────

def _seed(db_path):
    import json, time, sqlite_utils
    db = sqlite_utils.Database(db_path)
    db["formula"].insert_all(
        [{"name": "python@3.13", "desc": "interp",
          "homepage": "https://python.org/",
          "version": "3.13.2",
          "raw": json.dumps({"name": "python@3.13",
                              "desc": "interp",
                              "homepage": "https://python.org/",
                              "versions": {"stable": "3.13.2"}})}],
        pk="name",
    )
    db["formula"].enable_fts(["name", "desc"], tokenize="porter")
    db["_meta"].insert({"kind": "formula", "updated_at": time.time(),
                        "count": 1}, pk="kind", replace=True)


def _run(env_extra, *args):
    base = {**os.environ, **env_extra}
    r = subprocess.run(
        [sys.executable, "-m", "brew_hop_search.cli", *args],
        capture_output=True, text=True, env=base, timeout=30,
    )
    return re.sub(r"\033\[[0-9;]*m", "", r.stdout + r.stderr)


def test_env_format_multi_applies(tmp_path):
    """BREW_HOP_SEARCH_FORMAT=multi without --multi yields multi output."""
    db = tmp_path / "x.db"
    _seed(db)
    out = _run(
        {"BREW_HOP_SEARCH_DB": str(db),
         "BREW_HOP_SEARCH_FORMAT": "multi",
         "BREW_HOP_SEARCH_CONFIG": str(tmp_path / "missing.toml")},
        "-f", "python",
    )
    # Multi-line output has labeled fields; default human output doesn't.
    assert "version" in out
    assert "url" in out


def test_cli_flag_overrides_env_format(tmp_path):
    """--json beats $BREW_HOP_SEARCH_FORMAT=multi."""
    db = tmp_path / "x.db"
    _seed(db)
    out = _run(
        {"BREW_HOP_SEARCH_DB": str(db),
         "BREW_HOP_SEARCH_FORMAT": "multi",
         "BREW_HOP_SEARCH_CONFIG": str(tmp_path / "missing.toml")},
        "-f", "--json", "python",
    )
    # JSON envelope = first non-blank char is '{'
    out_stripped = out.strip()
    assert out_stripped.startswith("{")


def test_config_format_applies(tmp_path):
    """[output] default = 'csv' in config sets the output format."""
    db = tmp_path / "x.db"
    _seed(db)
    cfg = tmp_path / "config.toml"
    cfg.write_text('[output]\ndefault = "csv"\n')
    out = _run(
        {"BREW_HOP_SEARCH_DB": str(db),
         "BREW_HOP_SEARCH_CONFIG": str(cfg)},
        "-f", "python",
    )
    # CSV header on first line.
    assert out.splitlines()[0].startswith("source,name,version")
