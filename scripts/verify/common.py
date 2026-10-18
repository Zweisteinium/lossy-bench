"""Shared helpers for the independent re-computation in scripts/verify/ (stdlib only).

Written from the raw data, not by importing scripts/analyze.py; the definitions follow analyze.py:
  - only complete jobs count (an attempt ends with job_done ok=true; a job run twice: its last complete attempt);
  - flags: spectrum verdict "lossy"; lossprint transcode_probability >= 0.5; flaccheck transcode_verdict
    TRANSCODED ("flaccheck_wide": also SUSPICIOUS); None where the detector line has no usable output;
  - Wilson score interval, z = 1.96.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
CORPUS = ROOT / "corpus"
DETS = ("spectrum", "lossprint", "flaccheck", "flaccheck_wide")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(p, lo, hi) as fractions; (nan, nan, nan) for n = 0."""
    if n == 0:
        return (math.nan,) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def fmt(k: int, n: int) -> str:
    """'k/n = p% [lo-hi]' with one decimal, as in analyze.py's tables."""
    if n == 0:
        return f"{k}/{n}"
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * p:.1f}% [{100 * lo:.1f}-{100 * hi:.1f}]"


def jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_phase(n: int):
    """-> (records, stats). records: {(path, variant): {detector: line}} of complete jobs only."""
    current, complete, seen, ended = defaultdict(list), {}, set(), set()
    for d in jsonl(RES / f"phase{n}.jsonl"):
        if d["detector"] == "run_start":
            continue
        job = d["job"]
        seen.add(job)
        current[job].append(d)
        if d["detector"] in ("job_done", "job_error"):
            ended.add(job)
            attempt = current.pop(job)
            if d["detector"] == "job_done" and d["ok"]:
                complete[job] = attempt
    recs = {}
    for job, lines in complete.items():
        path = job.split(":", 1)[1]
        for d in lines:
            if d["detector"] != "job_done":
                recs.setdefault((path, d["variant"]), {})[d["detector"]] = d
    stats = {"complete": len(complete), "seen": len(seen), "not_complete": sorted(seen - set(complete)),
             "unterminated": sorted(set(current))}
    return recs, stats


def flags(rec: dict, lp_thr: float = 0.5) -> dict:
    sp, lp, fc = rec.get("spectrum"), rec.get("lossprint"), rec.get("flaccheck")
    out = {}
    out["spectrum"] = None if not (sp and sp.get("ok")) else ((sp.get("out") or {}).get("spectrum") or {}).get("verdict") == "lossy"
    lpo = (lp or {}).get("out")
    out["lossprint"] = None if not lpo else lpo["transcode_probability"] >= lp_thr
    fco = (fc or {}).get("out")
    out["flaccheck"] = None if not fco else fco.get("transcode_verdict") == "TRANSCODED"
    out["flaccheck_wide"] = None if not fco else fco.get("transcode_verdict") in ("TRANSCODED", "SUSPICIOUS")
    return out


def values(rec: dict) -> dict:
    spo = (rec.get("spectrum") or {}).get("out") or {}
    s = spo.get("spectrum") or {}
    lpo = (rec.get("lossprint") or {}).get("out") or {}
    fco = (rec.get("flaccheck") or {}).get("out") or {}
    return {"verdict": s.get("verdict"), "cutoff": s.get("cutoff_hz"), "drop": s.get("drop_db"),
            "fl_edge": spo.get("flicker_at_edge"), "edge_check": spo.get("edge_check"),
            "p": lpo.get("transcode_probability"), "lp_enc": lpo.get("encoder"), "fc": fco.get("transcode_verdict")}


def has_youtube(inv_item: dict | None) -> bool:
    t = json.dumps((inv_item or {}).get("tags") or {}).lower()
    return "youtube.com" in t or "youtu.be" in t


def loud_groups(meta: dict) -> list[str]:
    g = []
    rms, flat, peak = meta.get("rms_db"), meta.get("flat_factor"), meta.get("peak_db")
    if rms is not None:
        g.append("loud_rms>-9dB" if rms > -9 else "quiet_rms<-18dB" if rms < -18 else "rms_-18..-9dB")
    if flat is not None and flat >= 1:
        g.append("clipped_flat>=1")
    if peak is not None and peak >= -0.1:
        g.append("peak>=-0.1dBFS")
    return g


def load_corpus():
    jobs = {d["path"]: d for d in jsonl(CORPUS / "jobs.jsonl")}
    inv = {d["path"]: d for d in jsonl(CORPUS / "inventory.jsonl")}
    return jobs, inv
