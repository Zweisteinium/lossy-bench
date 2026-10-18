"""Integrity of the library FLACs that have no clean decode evidence yet (read-only): a full decode with every
frame's checksum checked (Echolot's audio.damage(): the stream bytes only, past an ID3 tag in front and before an
ID3v1/APE tag at the end), and the decoded sample count against the header's, exactly.

Run inside the Echolot container (it has Echolot, ffmpeg and mutagen), the paths on stdin (relative to tracks/):
  docker exec -i echolot nice -n 19 python - < scripts/check_integrity.py  (paths: see the README)
Prints: result <TAB> size <TAB> path; result "ok", else why (damaged / samples differ / trailing data / unreadable).
"""

import re
import subprocess
import sys
from pathlib import Path

from mutagen.flac import FLAC

from echolot.library import audio

LIB = Path("/music/tracks")


def check(p: Path) -> str:
    try:
        info = FLAC(p).info
    except Exception as e:
        return f"unreadable header: {e!r}"[:120]
    why = audio.damage(p)
    if why:
        return why
    start, end = audio._stream_bytes(p)
    cmd = ["ffmpeg", "-nostats", "-loglevel", "level+info", "-i", f"subfile,,start,{start},end,{end},,:{p}",
           "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"]
    said = subprocess.run(cmd, capture_output=True, timeout=600).stderr.decode(errors="replace")
    counts = re.findall(r"n_samples: (\d+)", said)
    decoded = int(counts[-1]) // info.channels if counts else 0
    if decoded != info.total_samples:
        return f"samples differ: decoded {decoded}, header {info.total_samples}"
    if any("[error]" in line for line in said.splitlines()):
        return "trailing data after the last frame"  # every sample decoded, junk after them
    return "ok"


for line in sys.stdin:
    rel = line.rstrip("\n")
    if rel:
        p = LIB / rel
        if not p.is_file():  # (renamed or retired by Echolot meanwhile: the live library)
            print(f"missing\t0\t{rel}", flush=True)
            continue
        print(f"{check(p)}\t{p.stat().st_size}\t{rel}", flush=True)
