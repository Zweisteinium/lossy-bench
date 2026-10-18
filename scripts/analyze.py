#!/usr/bin/env python3
"""Analysis of the benchmark run (results/phase1.jsonl, results/phase2.jsonl) -> results/analysis/.

Only complete jobs count (their job_done line ok; a job run twice: its last complete run). Negatives: the set A
originals (presumed genuine, by trust sub-tier) and the bait round trips (genuine audio behind a steep resampler
edge). Positives: the set B transcodes and the processed variants. Detector flags:
  spectrum   verdict "lossy" (Echolot's own decision)
  lossprint  transcode_probability >= threshold (0.5 by default; swept)
  flaccheck  transcode_verdict TRANSCODED (and, as "flaccheck_wide", also SUSPICIOUS)
Rates come with Wilson 95% intervals. Files Echolot already marks as made from lossy (spectrum_mark) are reported
apart from the false-positive rates (their spectrum flag is the very verdict that marked them: circular).

Usage: analyze.py [--partial]   (--partial: also with phase 2 missing, for progress reports)
"""

import csv
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "analysis"
REPRO_SINCE = "2026-10-02T17:00"  # 4ea672f "Improve fake FLAC detection" (2026-10-02 16:54): stored verdicts since
THRESHOLDS = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99)
DETECTORS = ("spectrum", "lossprint", "flaccheck", "flaccheck_wide")


def wilson(k: int, n: int) -> str:
    if not n:
        return "–"
    p, z = k / n, 1.96
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return f"{100 * p:.1f}% [{100 * max(c - h, 0):.1f}–{100 * min(c + h, 1):.1f}] ({k}/{n})"


def load(phase: int) -> dict:
    """(path, variant) -> {detector: line} of complete jobs only."""
    f = RES / f"phase{phase}.jsonl"
    if not f.exists():
        return {}
    runs = defaultdict(list)  # job -> [lines of one attempt], attempts in file order
    current = defaultdict(list)
    complete = {}
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("detector") == "run_start":
                continue
            current[d["job"]].append(d)
            if d["detector"] in ("job_done", "job_error"):
                if d["detector"] == "job_done" and d["ok"]:
                    complete[d["job"]] = current[d["job"]]
                runs[d["job"]].append(current.pop(d["job"]))
    out = {}
    for job, lines in complete.items():
        path = job.split(":", 1)[1]
        for d in lines:
            if d["detector"] not in ("job_done",):
                out.setdefault((path, d["variant"]), {})[d["detector"]] = d
    stats = {"jobs_complete": len(complete), "jobs_attempted": len(runs),
             "jobs_incomplete_or_changed": sorted(j for j in runs if j not in complete)}
    out[("__stats__", phase)] = stats
    return out


def flags(rec: dict, threshold: float = 0.5) -> dict:
    """Per detector: True/False/None (None: no valid output)."""
    out = {}
    sp = (rec.get("spectrum") or {}).get("out") or {}
    s = sp.get("spectrum") or {}
    out["spectrum"] = None if not (rec.get("spectrum") or {}).get("ok") else s.get("verdict") == "lossy"
    lp = (rec.get("lossprint") or {}).get("out")
    out["lossprint"] = None if not lp else lp["transcode_probability"] >= threshold
    fc = (rec.get("flaccheck") or {}).get("out")
    out["flaccheck"] = None if not fc else fc.get("transcode_verdict") == "TRANSCODED"
    out["flaccheck_wide"] = None if not fc else fc.get("transcode_verdict") in ("TRANSCODED", "SUSPICIOUS")
    return out


def raw(rec: dict) -> dict:
    sp = (rec.get("spectrum") or {}).get("out") or {}
    s = sp.get("spectrum") or {}
    lp = (rec.get("lossprint") or {}).get("out") or {}
    fc = (rec.get("flaccheck") or {}).get("out") or {}
    ev = {e.get("signal"): e.get("value") for e in fc.get("evidence") or [] if isinstance(e, dict)}
    return {"sp_verdict": s.get("verdict"), "sp_cutoff": s.get("cutoff_hz"), "sp_drop": s.get("drop_db"),
            "sp_flicker": s.get("flicker"), "sp_flicker_at_edge": sp.get("flicker_at_edge"), "sp_source": s.get("source"),
            "lp_p": lp.get("transcode_probability"), "lp_encoder": lp.get("encoder"), "lp_kbps": lp.get("bitrate_kbps"),
            "fc_verdict": fc.get("transcode_verdict"), "fc_conf": fc.get("confidence"), "fc_codec": fc.get("codec_guess"),
            "fc_cutoff": ev.get("cutoff_hz"), "fc_brick_wall": ev.get("brick_wall")}


def loudness(meta: dict) -> list[str]:
    out = []
    rms, flat, peak = meta.get("rms_db"), meta.get("flat_factor"), meta.get("peak_db")
    if rms is not None:
        out.append("loud_rms>-9dB" if rms > -9 else "quiet_rms<-18dB" if rms < -18 else "rms_-18..-9dB")
    if flat is not None and flat >= 1:
        out.append("clipped_flat>=1")
    if peak is not None and peak >= -0.1:
        out.append("peak>=-0.1dBFS")
    return out


def youtube(item: dict | None) -> bool:
    """A YouTube URL in the file's own tags (purl, comment, description): provenance found during the run, not used to
    select; reported as its own group, never moved between tiers after the fact."""
    t = json.dumps((item or {}).get("tags") or {}).lower()
    return "youtube.com" in t or "youtu.be" in t


def table(rows, header) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def main() -> None:
    partial = "--partial" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {json.loads(line)["path"]: json.loads(line) for line in open(ROOT / "corpus" / "jobs.jsonl", encoding="utf-8")}
    inv = {json.loads(line)["path"]: json.loads(line) for line in open(ROOT / "corpus" / "inventory.jsonl", encoding="utf-8")}
    p1, p2, p3 = load(1), load(2), load(3)
    st1, st2, st3 = (p.pop(("__stats__", i), {}) for i, p in ((1, p1), (2, p2), (3, p3)))
    report = [f"# Lossy-detection benchmark: analysis{' (partial)' if partial else ''}", ""]
    report += ["## Completeness", "",
               f"- phase 1 (originals): {st1.get('jobs_complete', 0)} of {len(jobs)} jobs complete; "
               f"incomplete or changed: {len(st1.get('jobs_incomplete_or_changed', []))}",
               f"- phase 2 (variants): {st2.get('jobs_complete', 0)} of "
               f"{sum(bool({'B', 'bait', 'processed'} & set(j['sets'])) for j in jobs.values())} jobs complete; "
               f"incomplete or changed: {len(st2.get('jobs_incomplete_or_changed', []))}"]
    bad = Counter()
    for recs in (p1, p2):
        for (path, variant), rec in recs.items():
            for det, d in rec.items():
                if not d["ok"]:
                    bad[(det, (d.get("error") or "")[:60])] += 1
    report += ["- failed lines (complete jobs): " + (", ".join(f"{k[0]}: {k[1]!r} ×{v}" for k, v in bad.most_common(12)) or "none"), ""]

    # 1. reproduction of Echolot's stored verdicts (harness check)
    repro, mism = Counter(), []
    for (path, variant), rec in p1.items():
        if variant != "original":
            continue
        filed = (inv.get(path, {}).get("filed") or {}).get("ts") or ""
        if filed < REPRO_SINCE:
            continue
        stored = inv[path]["quality"] == "fake" or bool(inv[path]["lossy_sourced"])
        f = flags(rec)["spectrum"]
        if f is None:
            repro["no harness verdict"] += 1
            continue
        repro["agree" if f == stored else "MISMATCH"] += 1
        if f != stored:
            mism.append((path, "lossy" if stored else "ok", raw(rec)))
    report += ["## Reproduction check: harness spectrum() vs Echolot's stored verdict", "",
               f"Files filed since {REPRO_SINCE} (after 4ea672f): " + ", ".join(f"{k} {v}" for k, v in sorted(repro.items())), ""]
    if mism:
        report += [table([(p, s, r["sp_verdict"], r["sp_cutoff"], r["sp_drop"], r["sp_flicker"]) for p, s, r in mism[:40]],
                         ["file", "stored", "harness", "cutoff", "drop dB", "flicker"]), ""]
    with open(OUT / "reproduction_mismatches.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "stored", *raw({}).keys()])
        for p, s, r in mism:
            w.writerow([p, s, *r.values()])

    # 2. false positives on presumed-genuine originals
    groups = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # group -> detector -> [flagged, n]
    originals = []
    for (path, variant), rec in p1.items():
        if variant != "original" or path not in jobs:
            continue
        j = jobs[path]
        meta = (rec.get("meta") or {}).get("out") or {}
        f = flags(rec)
        marked = bool(j.get("spectrum_mark"))
        originals.append((path, j, f, raw(rec), meta))
        keys = ["Echolot-marked fake (circular, apart)"] if marked else \
            ["all (unmarked)", f"subtier {j['subtier']}", *[f"stratum {s}" for s in j["strata"]],
             *[f"measured {s}" for s in loudness(meta)], f"format {j.get('bps')}/{j.get('rate')}",
             "provenance YouTube URL in tags" if youtube(inv.get(path)) else "all (unmarked, no YouTube URL in tags)"]
        for k in keys:
            for det in DETECTORS:
                if f[det] is not None:
                    groups[k][det][0] += f[det]
                    groups[k][det][1] += 1
    order = sorted(groups, key=lambda k: (not k.startswith("all"), not k.startswith("subtier"), not k.startswith("Echolot"), k))
    report += ["## False positives on presumed-genuine originals (set A)", "",
               "Flag rate with Wilson 95% interval. A flagged \"genuine\" file is a false positive only if the file "
               "really is genuine: tiers 1 and 2_proven are the most trustworthy; tier 3 may hold real fakes. "
               "\"measured clipped\" is confounded: decoding a lossy file of a loud master clips its overshoots (flat "
               "factor 0 -> 1-10 after MP3 320, 13-22 after Opus 160 on five loud tier-1/2 masters), so clipping is also "
               "a sign of a lossy source, not only a stratum.", "",
               table([(k, *(wilson(*groups[k][d]) for d in DETECTORS)) for k in order], ["group", *DETECTORS]), ""]

    # 3. bait and 4. recall. Bait counts as genuine only when its source does: sources Echolot marks as lossy or
    # lossprint flagged in their original form are reported apart ("doubted"), as planned
    doubted = {p_ for p_, j, f, r, m in originals if j.get("spectrum_mark") or f["lossprint"]}
    var = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    var_fmt = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    lp_by_var = defaultdict(list)
    for (path, variant), rec in p2.items():
        if path not in jobs:
            continue
        f = flags(rec)
        r = raw(rec)
        j = jobs[path]
        if variant.startswith("bait") and path in doubted:
            variant = "doubted source: " + variant
        pooled = j.get("rate") == 44100  # (set B's 11 sources at 48 kHz: only in the by-format table)
        if r["lp_p"] is not None and pooled:
            lp_by_var[variant].append(r["lp_p"])
        for det in DETECTORS:
            if f[det] is not None:
                if pooled:
                    var[variant][det][0] += f[det]
                    var[variant][det][1] += 1
                var_fmt[(variant, f"{j.get('bps')}/{j.get('rate')}")][det][0] += f[det]
                var_fmt[(variant, f"{j.get('bps')}/{j.get('rate')}")][det][1] += 1
    bait = [v for v in var if v.startswith("bait")]
    bait_doubted = [v for v in var if v.startswith("doubted source")]
    pos = [v for v in var if not v.startswith(("bait", "doubted source"))]
    report += ["## Bait: genuine audio behind a steep resampler edge (false positives)", "",
               table([(v, *(wilson(*var[v][d]) for d in DETECTORS)) for v in sorted(bait) + sorted(bait_doubted)],
                     ["variant", *DETECTORS]), "",
               "## Recall on transcodes (positives)", "",
               "Sources at 44.1 kHz only; set B's 11 sources at 48 kHz are in the by-format table below.", "",
               table([(v, *(wilson(*var[v][d]) for d in DETECTORS),
                       f"{min(lp_by_var[v]):.3f}" if lp_by_var[v] else "–") for v in sorted(pos)],
                     ["variant", *DETECTORS, "lossprint min p"]), "",
               "### Recall by source format", "",
               table([(v, fmt, *(wilson(*var_fmt[(v, fmt)][d]) for d in DETECTORS)) for v, fmt in sorted(var_fmt)
                      if not v.startswith("bait")], ["variant", "source", *DETECTORS]), ""]

    # 4a. the 48 kHz control (phase 3)
    ctl = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    ctl_lp = defaultdict(list)
    for (path, variant), rec in p3.items():
        if path in doubted:
            variant = "doubted source: " + variant
        f = flags(rec)
        if (rec.get("lossprint") or {}).get("out"):
            ctl_lp[variant].append(rec["lossprint"]["out"]["transcode_probability"])
        for det in DETECTORS:
            if f[det] is not None:
                ctl[variant][det][0] += f[det]
                ctl[variant][det][1] += 1
    report += ["## 48 kHz control (phase 3): genuine with a 20 kHz edge (negative) vs Opus 160 at 48 kHz (positive)", "",
               f"{st3.get('jobs_complete', 0)} sources complete (tiers 1 and 2_proven; see select_ctl48.py).", "",
               table([(v, *(wilson(*ctl[v][d]) for d in DETECTORS),
                       f"{min(ctl_lp[v]):.2e}–{max(ctl_lp[v]):.2e}" if ctl_lp[v] else "–") for v in sorted(ctl)],
                     ["variant", *DETECTORS, "lossprint p range"]), ""]

    # 4b. combined rules: FP on unmarked originals and bait, recall on transcodes
    rules = {
        "spectrum OR lossprint": lambda f: f["spectrum"] or f["lossprint"],
        "spectrum AND lossprint": lambda f: f["spectrum"] and f["lossprint"],
        "lossprint AND flaccheck": lambda f: f["lossprint"] and f["flaccheck"],
        "2 of 3": lambda f: f["spectrum"] + f["lossprint"] + f["flaccheck"] >= 2,
    }

    def rule_rate(items, rule):
        fs = [f for f in items if None not in (f["spectrum"], f["lossprint"], f["flaccheck"])]
        return wilson(sum(bool(rule(f)) for f in fs), len(fs))

    orig_f = [f for p, j, f, r, m in originals if not j.get("spectrum_mark")]
    bait_f = [flags(rec) for (path, v), rec in p2.items() if v.startswith("bait") and path not in doubted]
    pos_f = [flags(rec) for (path, v), rec in p2.items() if not v.startswith("bait")
             and jobs.get(path, {}).get("rate") == 44100]
    report += ["## Combined rules", "",
               table([(k, rule_rate(orig_f, r), rule_rate(bait_f, r), rule_rate(pos_f, r)) for k, r in rules.items()],
                     ["rule", "FP originals (unmarked)", "FP bait", "recall all transcodes"]), ""]
    cand = [(p, j, r) for p, j, f, r, m in originals if not j.get("spectrum_mark")
            and sum(bool(f[d]) for d in ("spectrum", "lossprint", "flaccheck")) >= 2]
    report += [f"Unmarked originals flagged by at least two detectors (fake candidates, or shared false positives): "
               f"{len(cand)}", ""]
    if cand:
        report += [table([(p, j["subtier"], r["sp_verdict"], r["sp_cutoff"], r["sp_drop"],
                           f"{r['lp_p']:.3f}" if r["lp_p"] is not None else "–", r["lp_encoder"], r["fc_verdict"],
                           r["fc_codec"]) for p, j, r in cand],
                         ["file", "subtier", "spectrum", "cutoff", "drop dB", "lossprint p", "lp codec", "flaccheck",
                          "fc codec"]), ""]

    # 4c. spectrum() threshold sweep, replayed from the stored raw values (cutoff, drop, flicker at the edge)
    def sim(r, drop_db=30.0, traces_from=19000, flicker=0.03, max_cut=20400):
        """spectrum()'s decision with other thresholds; None where it can't be replayed (drop < 25 dB is only
        replayable for drop_db >= 25, which the grid keeps to)."""
        if r["sp_verdict"] not in ("ok", "lossy") or r["sp_drop"] is None:
            return None
        if not (r["sp_drop"] >= drop_db and r["sp_cutoff"] < max_cut):
            return False
        if r["sp_cutoff"] < traces_from:
            return True
        fe = r["sp_flicker_at_edge"]  # (None with a drop >= 25 dB: too few loud frames, which spectrum() counts lossy)
        return fe is None or fe > flicker

    all_raw = [(("orig", j), r) for p_, j, f, r, m in originals] + \
        [((v, jobs.get(path)), raw(rec)) for (path, v), rec in p2.items() if jobs.get(path, {}).get("rate") == 44100] + \
        [((v, jobs.get(path)), raw(rec)) for (path, v), rec in p3.items()]
    replay = Counter((sim(r) == (r["sp_verdict"] == "lossy")) for _, r in all_raw if sim(r) is not None)
    grid = [(d, t, fl) for d in (25.0, 27.0, 28.0, 30.0) for t in (17000, 17500, 18000, 18500, 19000)
            for fl in (0.02, 0.03, 0.05)]
    focus = ("aac_128", "aac_256", "fdkaac_256", "fdkaac_vbr5", "mp3_320", "lame_320", "mp3_v0", "opus_160",
             "vorbis_q6", "ctl48_opus160")

    def rate(items, d, t, fl):
        xs = [sim(r, d, t, fl) for r in items]
        xs = [x for x in xs if x is not None]
        return f"{100 * sum(xs) / len(xs):.1f}% ({sum(xs)}/{len(xs)})" if xs else "–"

    neg_o = [r for (k, j), r in all_raw if k == "orig" and j and not j.get("spectrum_mark")
             and not youtube(inv.get(j["path"]))]
    neg_b = [r for (k, j), r in all_raw if (k.startswith("bait") or k == "ctl48_40k") and (j or {}).get("path") not in doubted]
    pos_focus = {v: [r for (k, j), r in all_raw if k == v] for v in focus}
    pos_all = [r for (k, j), r in all_raw if k != "orig" and not k.startswith("bait") and k != "ctl48_40k"]
    rows = [(d, t, fl, rate(neg_o, d, t, fl), rate(neg_b, d, t, fl), rate(pos_all, d, t, fl),
             *(rate(pos_focus[v], d, t, fl) for v in focus)) for d, t, fl in grid]
    report += ["## spectrum() threshold sweep (replayed from stored values)", "",
               f"Replay at Echolot's thresholds (30 dB, 19 kHz, 0.03, 20.4 kHz) reproduces the real verdict: "
               f"{replay[True]} agree, {replay[False]} differ.", "",
               table(rows, ["DROP_DB", "TRACES_FROM", "FLICKER", "FP originals (unmarked, no YouTube)",
                            "FP bait + ctl48_40k", "recall all", *focus]), ""]

    # 4d. candidate rules on two halves (split by a hash of the source path): rules found on one half must hold on
    # the other, or the gain is in-sample
    def opus48(r, j):
        return (j or {}).get("rate") == 48000 or r.get("_rate") == 48000

    candidates = {
        "spectrum (current)": lambda r, j: sim(r),
        "spectrum with TRACES_FROM 18 kHz": lambda r, j: sim(r, traces_from=18000),
        "spectrum + 25-30 dB with flicker >= 0.05": lambda r, j: None if sim(r) is None else sim(r) or (
            r["sp_drop"] is not None and 25 <= r["sp_drop"] < 30 and r["sp_cutoff"] < 19000
            and (r["sp_flicker_at_edge"] is None or r["sp_flicker_at_edge"] >= 0.05)),
        "spectrum + 48 kHz Opus band (19.8-20.5 kHz, drop >= 20)": lambda r, j: None if sim(r) is None else sim(r) or (
            r.get("_rate") == 48000 and r["sp_cutoff"] is not None and 19800 <= r["sp_cutoff"] <= 20500
            and (r["sp_drop"] or 0) >= 20),
        "lossprint >= 0.5": lambda r, j: None if r["lp_p"] is None else r["lp_p"] >= 0.5,
        "spectrum OR lossprint": lambda r, j: None if r["lp_p"] is None else bool(sim(r)) or r["lp_p"] >= 0.5,
    }

    def half(path):
        # (salted: the selection itself filled the sets in plain sha256 order, so an unsalted split is unbalanced)
        return "half 1" if hashlib.sha256(b"heldout:" + path.encode()).digest()[0] < 128 else "half 2"

    sets_h = defaultdict(list)  # (kind, half) -> [(raw, job)]
    for p_, j, f, r, m in originals:
        if not j.get("spectrum_mark") and not youtube(inv.get(p_)):
            sets_h[("FP originals", half(p_))].append((r | {"_rate": j.get("rate")}, j))
    for (path, v), rec in list(p2.items()) + list(p3.items()):
        j = jobs.get(path) or {}
        r = raw(rec)
        rate_v = 48000 if v.startswith("ctl48") or v == "mp3_320_up48" else j.get("rate")
        r["_rate"] = rate_v
        if v.startswith("bait") or v == "ctl48_40k":
            if path not in doubted:
                sets_h[("FP bait", half(path))].append((r, j))
        elif j.get("rate") == 44100:
            sets_h[("recall transcodes", half(path))].append((r, j))

    def crate(items, rule):
        xs = [rule(r, j) for r, j in items]
        xs = [bool(x) for x in xs if x is not None]
        return f"{100 * sum(xs) / len(xs):.1f}% ({sum(xs)}/{len(xs)})" if xs else "–"

    cols = [(k, h) for k in ("FP originals", "FP bait", "recall transcodes") for h in ("half 1", "half 2")]
    report += ["## Candidate rules on two halves (held-out check)", "",
               "Unmarked originals without a YouTube URL, bait and ctl48_40k, transcodes of 44.1 kHz sources; halves by a "
               "hash of the source path. A rule is only credible if both halves agree.", "",
               table([(name, *(crate(sets_h[c], rule) for c in cols)) for name, rule in candidates.items()],
                     ["rule", *(f"{k} {h}" for k, h in cols)]), ""]

    # 4e. experiment: spectrum() without clipped frames (clipfree.py), paired with the same files as Echolot measures them
    cf_path = RES / "clipfree.jsonl"
    if cf_path.exists():
        cf = {}
        for line in open(cf_path, encoding="utf-8"):
            d = json.loads(line)
            cf[(d["path"], d["variant"])] = d  # (the last line per item counts)
        same = Counter(d.get("same_as_echolot") for d in cf.values() if d.get("ok"))
        neg = [(k, d) for k, d in cf.items() if k[1] == "original" and d.get("ok") and k[0] in jobs
               and not jobs[k[0]].get("spectrum_mark") and not youtube(inv.get(k[0]))]
        n_orig = sum(1 for p_, j, f, r, m in originals if not j.get("spectrum_mark") and not youtube(inv.get(p_)))
        # (baseline: Echolot's own audio.spectrum() verdict; the stereo-mixed "asis" path matches it but for flicker
        # rounding, see same_as_echolot)
        flips = [(k[0], d) for k, d in neg if d["echolot"]["verdict"] != "lossy" and d["clipfree"]["verdict"] == "lossy"]
        lost = [(k[0], d) for k, d in neg if d["echolot"]["verdict"] == "lossy" and d["clipfree"]["verdict"] != "lossy"]
        rows = []
        for v in sorted({k[1] for k in cf} - {"original"}):
            ds = [d for k, d in cf.items() if k[1] == v and d.get("ok")]
            a_ = sum(d["echolot"]["verdict"] == "lossy" for d in ds)
            c_ = sum(d["clipfree"]["verdict"] == "lossy" for d in ds)
            rows.append((v, len(ds), f"{100 * a_ / len(ds):.1f}% ({a_})" if ds else "–",
                         f"{100 * c_ / len(ds):.1f}% ({c_})" if ds else "–"))
        report += ["## Experiment: spectrum() without clipped frames", "",
                   f"Self-check (the as-Echolot path equals audio.spectrum()): {same[True]} same, {same[False]} differ. "
                   f"Originals measured: {len(neg)} unmarked, without a YouTube URL, reaching the clip level; the other "
                   f"{n_orig - len(neg)} have no clipped frame and are unchanged by construction.", "",
                   f"New flags on those originals: {len(flips)} of {n_orig} ({100 * len(flips) / max(n_orig, 1):.2f}%); "
                   f"flags lost: {len(lost)}.", ""]
        lp_of = {p_: r["lp_p"] for p_, j, f, r, m in originals}
        n_lp = sum((lp_of.get(p_) or 0) >= 0.5 for p_, d in flips)
        report += [f"Of the new flags, {n_lp} are also flagged by lossprint (>= 0.5) in their original form.", ""]
        if flips:
            report += [table([(p_, jobs[p_]["subtier"], f"{lp_of.get(p_) or 0:.3f}", d["asis"]["cutoff_hz"], d["asis"]["drop_db"],
                               d["clipfree"]["cutoff_hz"], d["clipfree"]["drop_db"], d["clipfree"].get("flicker"),
                               f"{d['clipfree']['clipped_frames']}/{d['clipfree']['clipped_frames'] + d['clipfree']['frames']}")
                              for p_, d in flips[:40]],
                             ["file", "subtier", "lossprint p", "cut", "drop", "cut clip-free", "drop clip-free", "flicker",
                              "clipped frames"]), ""]
        report += [table(rows, ["variant", "n", "recall as Echolot", "recall clip-free"]), ""]

    # 5. lossprint threshold sweep
    neg_sets = {
        "originals tier 1 + 2_proven (unmarked)": [r["lp_p"] for p, j, f, r, m in originals
                                                  if not j.get("spectrum_mark") and j["subtier"] in ("1", "2_proven")],
        "originals all (unmarked)": [r["lp_p"] for p, j, f, r, m in originals if not j.get("spectrum_mark")],
        "bait (all cut-offs)": [p for v in bait for p in lp_by_var[v]],
    }
    pos_all = [p for v in pos for p in lp_by_var[v]]
    rows = []
    for t in THRESHOLDS:
        rows.append((t, *(wilson(sum(p >= t for p in xs if p is not None), sum(p is not None for p in xs))
                          for xs in neg_sets.values()),
                     wilson(sum(p >= t for p in pos_all), len(pos_all))))
    report += ["## lossprint threshold sweep", "",
               table(rows, ["threshold", *(f"FP {k}" for k in neg_sets), "recall all transcodes"]), ""]

    # 6. flicker below 19 kHz
    fl = defaultdict(list)
    for p, j, f, r, m in originals:
        if not j.get("spectrum_mark") and r["sp_flicker_at_edge"] is not None and (r["sp_cutoff"] or 0) < 19000:
            fl["genuine originals (unmarked)"].append(r["sp_flicker_at_edge"])
    for (path, variant), rec in p2.items():
        r = raw(rec)
        if r["sp_flicker_at_edge"] is not None and (r["sp_cutoff"] or 0) < 19000:
            fl["bait (genuine)" if variant.startswith("bait") else re.sub(r"_.*", "", variant) + " (lossy)"].append(
                r["sp_flicker_at_edge"])
    def q(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(p * len(xs)))]
    report += ["## Flicker at edges below 19 kHz (drop >= 25 dB)", "",
               table([(k, len(v), f"{min(v):.3f}", f"{q(v, .05):.3f}", f"{statistics.median(v):.3f}", f"{q(v, .95):.3f}",
                       f"{max(v):.3f}") for k, v in sorted(fl.items()) if v],
                     ["group", "n", "min", "p5", "median", "p95", "max"]), ""]

    # 7. disagreement list and per-file table
    cols = ["path", "variant", "subtier", "spectrum_mark", "strata", "peak_db", "rms_db", "flat_factor",
            "spectrum", "lossprint", "flaccheck", *raw({}).keys()]
    with open(OUT / "originals.csv", "w", newline="") as fa, open(OUT / "disagreements.csv", "w", newline="") as fd:
        wa, wd = csv.writer(fa), csv.writer(fd)
        wa.writerow(cols)
        wd.writerow(cols)
        n_dis = 0
        for p, j, f, r, m in sorted(originals):
            row = [p, "original", j["subtier"], j.get("spectrum_mark"), ";".join(j["strata"]), m.get("peak_db"),
                   m.get("rms_db"), m.get("flat_factor"), f["spectrum"], f["lossprint"], f["flaccheck"], *r.values()]
            wa.writerow(row)
            vals = {f[d] for d in ("spectrum", "lossprint", "flaccheck") if f[d] is not None}
            if len(vals) > 1:
                wd.writerow(row)
                n_dis += 1
    with open(OUT / "variants.csv", "w", newline="") as fv:
        wv = csv.writer(fv)
        wv.writerow(["path", "variant", "subtier", "spectrum", "lossprint", "flaccheck", *raw({}).keys()])
        for (path, variant), rec in sorted(p2.items()):
            f = flags(rec)
            wv.writerow([path, variant, jobs.get(path, {}).get("subtier"), f["spectrum"], f["lossprint"], f["flaccheck"],
                         *raw(rec).values()])
    report += [f"Disagreements among the originals (detectors differ): {n_dis}, in `disagreements.csv`; all originals "
               "in `originals.csv`, all variants in `variants.csv`.", ""]
    (OUT / "summary.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
