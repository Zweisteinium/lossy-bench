"""Decoded-audio MD5 (tag-independent) of library files, as the stream-capture tool computes it:
ffmpeg -v error -i F -map 0:a -c:a pcm_s32le -f md5 -    Paths (relative to tracks/) on stdin; prints md5 <TAB> path."""
import os, subprocess, sys
from pathlib import Path
LIB = Path(os.environ.get("LOSSY_BENCH_LIB", "tracks"))  # the library's track directory
for line in sys.stdin:
    rel = line.rstrip("\n")
    if not rel:
        continue
    p = LIB / rel
    if not p.is_file():
        print(f"missing\t{rel}", flush=True); continue
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(p), "-map", "0:a", "-c:a", "pcm_s32le", "-f", "md5", "-"], capture_output=True, text=True)
    out = r.stdout.strip()
    print(f"{out.removeprefix('MD5=') if r.returncode == 0 and out.startswith('MD5=') else 'error: ' + r.stderr.strip()[:100]}\t{rel}", flush=True)
