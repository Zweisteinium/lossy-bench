"""Echolot's spectrum check, unchanged, as a worker inside the echolot:prod image (prod's code and ffmpeg).

Reads one JSON request per line on stdin: {"id": ..., "path": ...}; writes one JSON line per request on stdout:
  {"id", "ok", "error", "spectrum": <spectrum()'s dict as it returns it>,
   "flicker_at_edge": <_flicker() at the detected edge, for every drop >= 25 dB (measurement only), else null>,
   "edge_check": <the second call found the same edge: true/false/null>, "seconds"}

spectrum() is called exactly as Echolot calls it. For flicker_at_edge a second call runs with three module thresholds
widened (DROP_DB 25, TRACES_FROM 0, MAX_LOSSY_CUT unlimited), so _flicker() runs at any edge with a 25 dB drop; its
edge search does not depend on them, so it is the same edge and the same excerpts. Only its "flicker" is kept, never
its verdict. The thresholds are restored right after (one request at a time, single-threaded).
"""

import json
import sys
import time
from pathlib import Path

from echolot.library import audio

WIDE = {"DROP_DB": 25.0, "TRACES_FROM": 0, "MAX_LOSSY_CUT": 10**9}


def flicker_at_edge(path: Path) -> dict:
    saved = {k: getattr(audio, k) for k in WIDE}
    try:
        for k, v in WIDE.items():
            setattr(audio, k, v)
        return audio.spectrum(path)
    finally:
        for k, v in saved.items():
            setattr(audio, k, v)


for line in sys.stdin:
    req = json.loads(line)
    t0 = time.monotonic()
    out = {"id": req["id"], "ok": False, "error": None, "spectrum": None, "flicker_at_edge": None, "edge_check": None}
    try:
        res = audio.spectrum(Path(req["path"]))
        out["spectrum"] = res
        if (res.get("drop_db") or 0) >= WIDE["DROP_DB"]:
            wide = flicker_at_edge(Path(req["path"]))
            out["flicker_at_edge"] = wide.get("flicker")
            out["edge_check"] = wide.get("cutoff_hz") == res.get("cutoff_hz") and wide.get("drop_db") == res.get("drop_db")
        out["ok"] = res.get("verdict") in ("ok", "lossy", "unknown")
    except Exception as e:  # recorded, never skipped silently
        out["error"] = f"{type(e).__name__}: {e}"[:300]
    out["seconds"] = round(time.monotonic() - t0, 3)
    print(json.dumps(out), flush=True)
