"""pytest conftest — show expected output at -vv (self-documenting tests).

Usage:
  pytest tests/ -vv           show expected output after each test
  pytest tests/ -vv -k fmt    show just formatter examples
  pytest tests/ -vv -k expect show just inline-expect examples
"""
from __future__ import annotations

import pytest

from tests.snap import drain_expects

_verbosity = 0
_tw = None


def pytest_sessionstart(session):
    global _verbosity, _tw
    _verbosity = session.config.option.verbose
    if _verbosity >= 2:
        tr = session.config.pluginmanager.get_plugin("terminalreporter")
        if tr:
            _tw = tr._tw


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    yield

    expects = drain_expects()
    if _verbosity < 2 or not expects or _tw is None:
        return

    for label, content in expects:
        _tw.line()
        _tw.write(f"    ╌╌ {label} ", bold=True)
        _tw.line("╌" * max(1, 60 - len(label)))
        for line in content.splitlines():
            _tw.line(f"    │ {line}")
