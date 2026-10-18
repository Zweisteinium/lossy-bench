#!/usr/bin/env python3
"""Spectrogram PNGs for the review: every original in results/analysis/disagreements.csv -> results/analysis/spectrograms/.

Read-only on the library (ffmpeg showspectrumpic, host ffmpeg, nice/ionice), one PNG per file, named by row number and
a short name; index.csv maps them back to the paths. Usage: spectrograms.py [--workers N]
"""

import csv
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = Path(os.environ.get("LOSSY_BENCH_LIB", "tracks"))  # the library's track directory
OUT = ROOT / "results" / "analysis" / "spectrograms"
NICE = ["nice", "-n", "19", "ionice", "-c3"]


def render(i: int, path: str) -> tuple[str, str, str]:
    name = f"{i:03d}_" + re.sub(r"[^A-Za-z0-9]+", "_", Path(path).stem)[:60].strip("_") + ".png"
    tmp = OUT / (name + ".tmp.png")
    r = subprocess.run([*NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(LIB / path),
                        "-filter_complex", "[0:a:0]showspectrumpic=s=1600x600:mode=combined:scale=log:legend=1", "-frames:v", "1",
                        "-f", "image2", "-c:v", "png", str(tmp)], capture_output=True, timeout=600)
    if r.returncode != 0:
        tmp.unlink(missing_ok=True)
        return path, "", r.stderr.decode(errors="replace").strip()[-200:]
    tmp.replace(OUT / name)
    return path, name, ""


def main() -> None:
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 3
    OUT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(ROOT / "results" / "analysis" / "disagreements.csv", encoding="utf-8")))
    paths = list(dict.fromkeys(r["path"] for r in rows))
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda a: render(*a), enumerate(paths, 1)))
    with open(OUT / "index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["png", "path", "error"])
        for path, name, err in res:
            w.writerow([name, path, err])
    print(f"{sum(bool(n) for _, n, _ in res)} of {len(res)} spectrograms -> {OUT}")


if __name__ == "__main__":
    main()
