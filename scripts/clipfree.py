#!/usr/bin/env python3
"""Experiment after phase 2: spectrum() with clipped frames left out (clipfree_worker.py) -> results/clipfree.jsonl.

Negatives: every set-A original (library, read-only). Positives: 60 set-B sources at 44.1 kHz (salted hash order),
each as mp3_192, mp3_320, mp3_v2, aac_128, lame_320, vorbis_q3, made exactly as in run.py, scored, deleted. Paired:
the same file is measured as Echolot does it and clip-free. Resumable per item. Usage: clipfree.py [--workers N]
"""

import hashlib
import json
import shutil
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402  (the harness's encoder table, paths and nice settings)

OUT = run.RESULTS / "clipfree.jsonl"
VARIANTS = ("mp3_192", "mp3_320", "mp3_v2", "aac_128", "lame_320", "vorbis_q3")
N_POS = 60
lock = threading.Lock()


class Worker:
    def __init__(self):
        self.p = subprocess.Popen(
            ["docker", "run", "--rm", "-i", "--network", "none", "--cpu-shares", "128",
             "-v", f"{run.LIB.parent}:{run.LIB.parent}:ro", "-v", f"{run.SCRATCH}:{run.SCRATCH}:ro",
             "-v", f"{run.ROOT / 'scripts'}:/bench:ro", "--entrypoint", "nice", run.IMAGE,
             "-n", "19", "ionice", "-c3", "python", "-u", "/bench/clipfree_worker.py"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def ask(self, path: Path) -> dict:
        self.p.stdin.write(json.dumps({"id": 0, "path": str(path)}) + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def close(self):
        self.p.stdin.close()
        self.p.wait(60)


def write(line: dict) -> None:
    with lock, open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def make(src: Path, variant: str, wd: Path, rate: int) -> Path | None:
    tmp = wd / f"{variant}.flac"
    if variant in run.FFMPEG:
        args, ext, _ = run.FFMPEG[variant]
        enc = wd / f"{variant}.enc.{ext}"
        e = run.run([*run.NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0",
                     "-map_metadata", "-1", *args, str(enc)])
    else:
        args, ext, _ = run.CLI[variant]
        wav = wd / "source.wav"
        if not wav.exists():
            run.run([*run.NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0",
                     "-map_metadata", "-1", "-c:a", "pcm_s16le", str(wav)])
        enc = wd / f"{variant}.enc.{ext}"
        e = run.run([*run.NICE, *args, str(wav), str(enc)])
    if e.returncode != 0 or not enc.is_file():
        return None
    d = run.run([*run.NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(enc), "-map", "0:a:0",
                 "-map_metadata", "-1", "-ar", str(rate), "-sample_fmt", "s16", "-c:a", "flac", str(tmp)])
    enc.unlink(missing_ok=True)
    return tmp if d.returncode == 0 else None


def main() -> None:
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 2
    jobs = [json.loads(line) for line in open(run.ROOT / "corpus" / "jobs.jsonl", encoding="utf-8")]
    done = set()
    if OUT.exists():
        done = {(d["path"], d["variant"]) for d in map(json.loads, open(OUT, encoding="utf-8"))}
    # originals whose decoded peak stays below the clip level have no clipped frame, so their clip-free result is
    # identical by construction: only the others are measured (peak from phase 1's astats, with a margin)
    peak = {}
    for line in open(run.RESULTS / "phase1.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d["detector"] == "meta" and d["variant"] == "original":
            peak[d["job"].split(":", 1)[1]] = (d.get("out") or {}).get("peak_db")
    neg = [("original", j) for j in jobs if "A" in j["sets"]
           and (peak.get(j["path"]) is None or peak[j["path"]] >= -0.05)]
    print(f"clipfree: {len(neg)} of {sum('A' in j['sets'] for j in jobs)} originals reach the clip level", flush=True)
    b = sorted((j for j in jobs if "B" in j["sets"] and j["rate"] == 44100),
               key=lambda j: hashlib.sha256(b"clipfree:" + j["path"].encode()).hexdigest())[:N_POS]
    items = [(v, j) for v, j in neg if (j["path"], v) not in done] + \
            [("pos", j) for j in b if any((j["path"], v) not in done for v in VARIANTS)]
    print(f"clipfree: {len(items)} items to run", flush=True)
    local = threading.local()

    def do(item):
        kind, j = item
        if not hasattr(local, "w"):
            local.w = Worker()
        src = run.LIB / j["path"]
        if run.stat(src) != (j["size"], j["mtime"]):
            write({"path": j["path"], "variant": kind, "error": "changed"})
            return
        if kind == "original":
            write({"path": j["path"], "variant": "original", **local.w.ask(src)})
            return
        wd = run.SCRATCH / f"clipfree-{uuid.uuid4().hex[:12]}"
        wd.mkdir(parents=True)
        try:
            for v in VARIANTS:
                if (j["path"], v) in done:
                    continue
                f = make(src, v, wd, j["rate"])
                write({"path": j["path"], "variant": v, **(local.w.ask(f) if f else {"ok": False, "error": "make failed"})})
        finally:
            shutil.rmtree(wd, ignore_errors=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(do, items))
    print("clipfree: done", flush=True)


if __name__ == "__main__":
    main()
