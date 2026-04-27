# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Background process: refresh the installed-packages index.

Spawned by `installed.background_refresh()`. Reads the foreground's
sentinel-file path from BHS_REFRESH_SENTINEL and writes a completion
record so the foreground can show duration + outcome.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from brew_hop_search.sources.installed import refresh, _BG_TIMEOUT
from brew_hop_search.cache import write_sentinel, append_refresh_log


if __name__ == "__main__":
    sentinel = os.environ.get("BHS_REFRESH_SENTINEL")
    start = time.time()
    err = ""
    try:
        ok = refresh(silent=True, timeout=_BG_TIMEOUT)
    except Exception as e:
        ok = False
        err = str(e)[:200]
    duration_ms = int((time.time() - start) * 1000)
    if sentinel:
        try:
            write_sentinel(Path(sentinel), duration_ms, ok, err)
        except Exception:
            pass
    append_refresh_log("installed", duration_ms, ok)
