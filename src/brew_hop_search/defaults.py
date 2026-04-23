# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Centralized default values.

Every default the app consults lives here. Per-module imports reference
these rather than defining their own, so changing a timeout or threshold
means editing one file.

Intended priority order when wiring runtime resolution (implemented
per-setting): this module → environment variable (where supported) →
CLI argument (where supported).
"""
from __future__ import annotations

# ── cache stale thresholds (seconds) ───────────────────────────────────────

# Formula/cask index from formulae.brew.sh. Drives the `--stale` flag and
# the automatic background-refresh window for the remote API caches.
STALE_API = 6 * 3600  # 6 hours

# Tapped repos (scanned from $(brew --repo)/Library/Taps/).
STALE_TAPS = 3600  # 1 hour

# Installed-packages index (refreshed from `brew info --json=v2 --installed`).
STALE_INSTALLED = 3600  # 1 hour

# Local brew API cache at $(brew --cache)/api/.
STALE_LOCAL = 3600  # 1 hour

# ── result shaping ─────────────────────────────────────────────────────────

# -n / --limit default. Overridable by env var BREW_HOP_SEARCH_LIMIT and
# then by the CLI flag. Stored as str because argparse parses N[+OFF].
LIMIT = "20"

# ── network ────────────────────────────────────────────────────────────────

# HTTP timeout for API fetches (seconds).
API_TIMEOUT = 10

# Gap between live PyPI "up to date?" checks for `-VV`. Not a hard cap —
# -VV always hits PyPI; this is for passive warn-on-stale paths.
VERSION_CHECK_INTERVAL = 4 * 3600  # 4 hours
