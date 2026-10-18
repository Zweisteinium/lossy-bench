#!/usr/bin/env python3
"""Independent re-computation of the benchmark's headline numbers (phases 1-3) from the raw data, compared cell by
cell with results/analysis/summary.md. Stdlib only. Usage: nice -n 19 python3 scripts/verify/v1_benchmark.py

Definitions follow scripts/analyze.py (see docs/results.md, "Verification"); deviations are marked "deviation".
"""

import hashlib
import sys
from collections import Counter, defaultdict

from common import CORPUS, DETS, fmt, flags, has_youtube, jsonl, load_corpus, load_phase, loud_groups, values
from summary_tables import compare, parse

jobs, inv = load_corpus()
ctl_jobs = {d["path"]: d for d in jsonl(CORPUS / "jobs_ctl48.jsonl")}
p1, s1 = load_phase(1)
p2, s2 = load_phase(2)
p3, s3 = load_phase(3)
summ = parse()
problems = []


def add(store, key, f):
    for d in DETS:
        if f[d] is not None:
            store[key][d][0] += f[d]
            store[key][d][1] += 1


def as_kn(store):
    return {k: {d: tuple(v[d]) for d in DETS if v[d][1]} for k, v in store.items()}


def counter():
    return defaultdict(lambda: defaultdict(lambda: [0, 0]))


# ---------------------------------------------------------------- completeness
print("## Completeness")
want2 = [p for p, j in jobs.items() if {"B", "bait", "processed"} & set(j["sets"])]
for n, s, want in ((1, s1, len(jobs)), (2, s2, len(want2)), (3, s3, len(ctl_jobs))):
    print(f"phase {n}: {s['complete']} of {want} jobs complete; seen {s['seen']}; not complete {len(s['not_complete'])}; "
          f"unterminated {len(s['unterminated'])}")
rej = [(p, v, d["meta"].get("error")) for (p, v), d in p2.items() if "meta" in d and not d["meta"]["ok"]]
scored2 = sum(1 for d in p2.values() if "spectrum" in d)
print(f"phase 2 variants: {len(p2)} meta lines, {scored2} scored, {len(rej)} rejected by the variant checks")
print("  rejected by variant:", dict(Counter(v for _, v, _ in rej)))
print("  rejected source files:", len({p for p, _, _ in rej}),
      "(by rate:", dict(Counter(jobs[p]["rate"] for p in {p for p, _, _ in rej})), ")")
mp3_ff = {"mp3_128", "mp3_192", "mp3_320", "mp3_v0", "mp3_v2", "mp3_320_gain", "mp3_320_up48"}
print("  sources with rejected ffmpeg-MP3 lines:", len({p for p, v, _ in rej if v in mp3_ff}),
      "; with rejected ffmpeg-AAC lines:", len({p for p, v, _ in rej if v.startswith("aac_")}))
other = [(p, v, e) for p, v, e in rej if v not in mp3_ff and not v.startswith("aac_")]
print("  other rejected lines:", [(v, e) for p, v, e in other])
bad_lines = sum(1 for recs in (p1, p2, p3) for rec in recs.values() for det, d in rec.items()
                if det != "meta" and not d["ok"])
print(f"detector lines with ok=false in complete jobs: {bad_lines}")
p1meta_bad = sum(1 for (p, v), d in p1.items() if not d["meta"]["ok"])
print(f"phase 1 meta lines with ok=false (changed file / decode problem): {p1meta_bad}")

# ---------------------------------------------------------------- sets
print("\n## Sets")
sets = Counter(s for j in jobs.values() for s in j["sets"])
print("sets in jobs.jsonl:", dict(sets), "| phase-2 jobs:", len(want2), "| ctl48 jobs:", len(ctl_jobs))
print("B by rate:", dict(Counter(j["rate"] for j in jobs.values() if "B" in j["sets"])))
print("spectrum_mark per set:", {s: sum(1 for j in jobs.values() if s in j["sets"] and j["spectrum_mark"])
                                 for s in ("A", "B", "bait", "processed")})
yt_all = [p for p, j in jobs.items() if has_youtube(inv.get(p))]
print(f"A with a YouTube URL in tags: {len(yt_all)} (by subtier {dict(Counter(jobs[p]['subtier'] for p in yt_all))}; "
      f"unmarked {sum(1 for p in yt_all if not jobs[p]['spectrum_mark'])})")

# ---------------------------------------------------------------- reproduction
print("\n## Reproduction check")
REPRO_SINCE = "2026-10-02T17:00"
rep = Counter()
for (p, v), rec in p1.items():
    if v != "original":
        continue
    ts = ((inv.get(p) or {}).get("filed") or {}).get("ts") or ""
    if ts < REPRO_SINCE:
        continue
    stored = inv[p]["quality"] == "fake" or bool(inv[p]["lossy_sourced"])
    f = flags(rec)["spectrum"]
    rep["no verdict" if f is None else "agree" if f == stored else "mismatch"] += 1
    rep["stored lossy"] += stored
print("filed since", REPRO_SINCE, dict(rep))
# edge_check on every drop >= 25 dB, all phases
ec = Counter()
for recs in (p1, p2, p3):
    for rec in recs.values():
        if "spectrum" in rec:
            x = values(rec)
            if x["drop"] is not None and x["drop"] >= 25:
                ec[x["edge_check"]] += 1
print("edge_check for drop >= 25 dB (all phases):", dict(ec))
# tier-2 audio MD5: run vs the hash that put them in tier 2
lib_md5 = {}
for line in open(CORPUS / "evidence" / "capture_library_md5.tsv", encoding="utf-8"):
    m, path = line.rstrip("\n").split("\t", 1)
    lib_md5[path] = m
t2 = [p for p, j in jobs.items() if j["subtier"].startswith("2")]
same = sum(1 for p in t2 if p1[(p, "original")]["meta"]["out"]["audio_md5_s32le"] == lib_md5.get(p))
print(f"tier-2 originals: {len(t2)}; run audio MD5 equals the tier-2 hash: {same}")

# ---------------------------------------------------------------- false positives on originals
print("\n## False positives, set A originals")
g = counter()
originals = []
for (p, v), rec in p1.items():
    if v != "original" or p not in jobs:
        continue
    j = jobs[p]
    f = flags(rec)
    meta = rec["meta"]["out"] or {}
    originals.append((p, j, f, values(rec), meta))
    if j["spectrum_mark"]:
        add(g, ("Echolot-marked fake (circular, apart)",), f)
        continue
    keys = ["all (unmarked)", f"subtier {j['subtier']}", *(f"stratum {s}" for s in j["strata"]),
            *(f"measured {s}" for s in loud_groups(meta)), f"format {j['bps']}/{j['rate']}",
            "provenance YouTube URL in tags" if has_youtube(inv.get(p)) else "all (unmarked, no YouTube URL in tags)"]
    for k in keys:
        add(g, (k,), f)
fp = as_kn(g)
for k in sorted(fp):
    print(f"  {k[0]:45s} " + " | ".join(f"{d} {fmt(*fp[k][d])}" for d in DETS[:3]))
problems += compare("FP originals", summ["False positives on presumed-genuine originals (set A)"], fp)
# extra groups not in summary.md: tier 1 + 2_proven pooled, 48 kHz pooled
for name, sel in (("tier 1 + 2_proven", lambda j: j["subtier"] in ("1", "2_proven")),
                  ("48 kHz (16 and 24 bit)", lambda j: j["rate"] == 48000),
                  ("44.1 kHz, no YouTube URL", lambda j: j["rate"] == 44100 and not has_youtube(inv.get(j["path"])))):
    c = counter()
    for p, j, f, x, m in originals:
        if not j["spectrum_mark"] and sel(j):
            add(c, (name,), f)
    r = as_kn(c)[(name,)]
    print(f"  (extra) {name:37s} " + " | ".join(f"{d} {fmt(*r[d])}" for d in DETS[:3]))

doubted = {p for p, j, f, x, m in originals if j["spectrum_mark"] or f["lossprint"]}
print(f"doubted sources (marked or lossprint-flagged originals): {len(doubted)}; "
      f"among bait sources: {sum(1 for p in doubted if 'bait' in jobs[p]['sets'])}")

# ---------------------------------------------------------------- bait and recall
print("\n## Bait and recall (phase 2)")
var, var_fmt, lp_by = counter(), counter(), defaultdict(list)
for (p, v), rec in p2.items():
    if p not in jobs:
        continue
    j = jobs[p]
    f, x = flags(rec), values(rec)
    if v.startswith("bait") and p in doubted:
        v = "doubted source: " + v
    pooled = j["rate"] == 44100
    if pooled and x["p"] is not None:
        lp_by[v].append(x["p"])
    if pooled:
        add(var, (v,), f)
    add(var_fmt, (v, f"{j['bps']}/{j['rate']}"), f)
vk = as_kn(var)
for k in sorted(vk):
    extra = f" | lossprint min p {min(lp_by[k[0]]):.3f}" if lp_by[k[0]] and not k[0].startswith(("bait", "doubted")) else ""
    print(f"  {k[0]:28s} " + " | ".join(f"{d} {fmt(*vk[k][d])}" for d in DETS[:3]) + extra)
bait_rows = summ["Bait: genuine audio behind a steep resampler edge (false positives)"]
problems += compare("bait", bait_rows, {k: v for k, v in vk.items() if k[0].startswith(("bait", "doubted"))})
rec_rows = summ["Recall on transcodes (positives)"]
problems += compare("recall", rec_rows, {k: v for k, v in vk.items() if not k[0].startswith(("bait", "doubted"))})
# lossprint min p column (string compare)
for key, vals in rec_rows:
    mine = f"{min(lp_by[key[0]]):.3f}"
    if key[-1] != mine:
        problems.append(f"MISMATCH lossprint min p {key[0]}: summary {key[-1]}, recomputed {mine}")
vf = as_kn(var_fmt)
problems += compare("recall by format", summ["Recall by source format"],
                    {k: v for k, v in vf.items() if not k[0].startswith("bait")}, key_len=2)

pos_names = [k[0] for k in vk if not k[0].startswith(("bait", "doubted"))]
pos_p = [p for v in pos_names for p in lp_by[v]]
print(f"pooled positives (44.1 kHz sources, B + processed): {len(pos_p)}; lossprint min {min(pos_p):.4f}")
for t in (0.5, 0.7, 0.84, 0.9, 0.95, 0.99):
    print(f"  lossprint >= {t}: {fmt(sum(q >= t for q in pos_p), len(pos_p))}")
print("  below 0.9:", sorted((round(q, 3), v) for v in pos_names for q in lp_by[v] if q < 0.9))
sp_pos = sum(1 for (p, v), rec in p2.items() if not v.startswith("bait") and jobs[p]["rate"] == 44100
             and flags(rec)["spectrum"])
print(f"spectrum alone, pooled positives: {fmt(sp_pos, len(pos_p))}")
# all phase-2/3 positives regardless of source rate (as the 2026-10-16 lossprint answer counts them)
allpos = [(v, values(rec)) for recs in (p2, p3) for (p, v), rec in recs.items()
          if "lossprint" in rec and not v.startswith("bait") and v != "ctl48_40k"]
ps = [x["p"] for v, x in allpos]
print(f"all positives incl. 48 kHz sources and ctl48_opus160: {len(ps)}; >= 0.9 {fmt(sum(q >= .9 for q in ps), len(ps))}; "
      f"min {min(ps):.3f}; 0.7-0.9: {sum(.7 <= q < .9 for q in ps)}; < 0.7: {sum(q < .7 for q in ps)}")
cs = [x for v, x in allpos if x["verdict"] == "lossy"]
print(f"  spectrum-caught among them: {len(cs)}; with lossprint >= 0.5: {sum(x['p'] >= .5 for x in cs)}")
cs44 = [values(rec) for (p, v), rec in p2.items() if not v.startswith("bait") and jobs[p]["rate"] == 44100
        and flags(rec)["spectrum"]]
print(f"  spectrum-caught, pooled 44.1 kHz: {len(cs44)}; with lossprint >= 0.5: {sum(x['p'] >= .5 for x in cs44)}")
ph1p = [x["p"] for p, j, f, x, m in originals]
print(f"phase-1 originals with lossprint p < 0.01: {sum(q < .01 for q in ph1p)}/{len(ph1p)}")
bait_all = [values(rec)["p"] for (p, v), rec in p2.items() if v.startswith("bait") and "lossprint" in rec]
print(f"bait (all 450, incl. doubted) p < 0.01: {sum(q < .01 for q in bait_all)}/{len(bait_all)}; >= 0.5: "
      f"{sum(q >= .5 for q in bait_all)}")
unm = [x["p"] for p, j, f, x, m in originals if not j["spectrum_mark"]]
print(f"unmarked originals: p >= 0.5 {sum(q >= .5 for q in unm)}; p in [0.5, 0.9): {sum(.5 <= q < .9 for q in unm)}")

# ---------------------------------------------------------------- 48 kHz control
print("\n## 48 kHz control (phase 3)")
ctl, ctl_p = counter(), defaultdict(list)
for (p, v), rec in p3.items():
    if p in doubted:
        v = "doubted source: " + v
    add(ctl, (v,), flags(rec))
    ctl_p[v].append(values(rec)["p"])
ck = as_kn(ctl)
for k in sorted(ck):
    print(f"  {k[0]:32s} " + " | ".join(f"{d} {fmt(*ck[k][d])}" for d in DETS[:3]) +
          f" | lossprint p {min(ctl_p[k[0]]):.2e}..{max(ctl_p[k[0]]):.2e}")
problems += compare("ctl48", summ[next(s for s in summ if s.startswith("48 kHz control"))], ck)
print("  ctl48 sources by origin:", dict(Counter(j["ctl48_source"] for j in ctl_jobs.values())))

# ---------------------------------------------------------------- combined rules
print("\n## Combined rules")
rules = {"spectrum OR lossprint": lambda f: f["spectrum"] or f["lossprint"],
         "spectrum AND lossprint": lambda f: f["spectrum"] and f["lossprint"],
         "lossprint AND flaccheck": lambda f: f["lossprint"] and f["flaccheck"],
         "2 of 3": lambda f: f["spectrum"] + f["lossprint"] + f["flaccheck"] >= 2}
groups = {"FP originals (unmarked)": [f for p, j, f, x, m in originals if not j["spectrum_mark"]],
          "FP bait": [flags(r) for (p, v), r in p2.items() if v.startswith("bait") and p not in doubted],
          "recall all transcodes": [flags(r) for (p, v), r in p2.items() if not v.startswith("bait")
                                    and jobs.get(p, {}).get("rate") == 44100]}
mine = {}
for name, rule in rules.items():
    row = {}
    for gname, fs in groups.items():
        fs = [f for f in fs if None not in (f["spectrum"], f["lossprint"], f["flaccheck"])]
        row[gname] = (sum(bool(rule(f)) for f in fs), len(fs))
    mine[(name,)] = row
    print(f"  {name:25s} " + " | ".join(f"{k} {fmt(*v)}" for k, v in row.items()))
problems += compare("combined rules", summ["Combined rules"], mine)
cand = [p for p, j, f, x, m in originals if not j["spectrum_mark"]
        and sum(bool(f[d]) for d in ("spectrum", "lossprint", "flaccheck")) >= 2]
print(f"unmarked originals flagged by >= 2 detectors: {len(cand)} (by subtier {dict(Counter(jobs[p]['subtier'] for p in cand))})")
dis = sum(1 for p, j, f, x, m in originals if len({f[d] for d in ('spectrum', 'lossprint', 'flaccheck')}) > 1)
print(f"originals where the three detectors disagree: {dis}")


# ---------------------------------------------------------------- spectrum replay and threshold sweep
def sim(x, drop_db=30.0, traces_from=19000, flicker=0.03, max_cut=20400):
    """spectrum()'s decision from stored cutoff, drop and flicker at the edge (same rule as analyze.py's sim)."""
    if x["verdict"] not in ("ok", "lossy") or x["drop"] is None:
        return None
    if x["drop"] < drop_db or x["cutoff"] >= max_cut:
        return False
    if x["cutoff"] < traces_from:
        return True
    return x["fl_edge"] is None or x["fl_edge"] > flicker


print("\n## spectrum() replay and sweep")
allx = [("orig", j, x) for p, j, f, x, m in originals] + \
    [(v, jobs.get(p), values(r)) for (p, v), r in p2.items() if jobs.get(p, {}).get("rate") == 44100] + \
    [(v, jobs.get(p) or ctl_jobs.get(p), values(r)) for (p, v), r in p3.items()]
rp = Counter(sim(x) == (x["verdict"] == "lossy") for _, _, x in allx if sim(x) is not None)
print(f"replay at prod constants: {rp[True]} agree, {rp[False]} differ (of {len(allx)} scored files)")
neg_o = [x for k, j, x in allx if k == "orig" and not j["spectrum_mark"] and not has_youtube(inv.get(j["path"]))]
neg_b = [x for k, j, x in allx if (k.startswith("bait") or k == "ctl48_40k") and j["path"] not in doubted]
pos_all = [x for k, j, x in allx if k != "orig" and not k.startswith("bait") and k != "ctl48_40k"]
focus = ("aac_128", "aac_256", "fdkaac_256", "fdkaac_vbr5", "mp3_320", "lame_320", "mp3_v0", "opus_160", "vorbis_q6",
         "ctl48_opus160")
pos_f = {v: [x for k, j, x in allx if k == v] for v in focus}


def rate(xs, **kw):
    ys = [sim(x, **kw) for x in xs]
    ys = [y for y in ys if y is not None]
    return (sum(ys), len(ys))


sweep = {}
for d in (25.0, 27.0, 28.0, 30.0):
    for t in (17000, 17500, 18000, 18500, 19000):
        for fl in (0.02, 0.03, 0.05):
            kw = dict(drop_db=d, traces_from=t, flicker=fl)
            row = {"FP originals (unmarked, no YouTube)": rate(neg_o, **kw), "FP bait + ctl48_40k": rate(neg_b, **kw),
                   "recall all": rate(pos_all, **kw)} | {v: rate(pos_f[v], **kw) for v in focus}
            sweep[(str(d), str(t), str(fl))] = row
problems += compare("threshold sweep", summ["spectrum() threshold sweep (replayed from stored values)"], sweep, key_len=3)
for key in (("30.0", "19000", "0.03"), ("30.0", "18000", "0.03")):
    r = sweep[key]
    print(f"  {key}: FP orig {fmt(*r['FP originals (unmarked, no YouTube)'])}; FP bait+ctl {fmt(*r['FP bait + ctl48_40k'])}; "
          f"recall {fmt(*r['recall all'])}")


# ---------------------------------------------------------------- held-out halves
def half(path):
    return "half 1" if hashlib.sha256(b"heldout:" + path.encode()).digest()[0] < 128 else "half 2"


hs = defaultdict(list)
for p, j, f, x, m in originals:
    if not j["spectrum_mark"] and not has_youtube(inv.get(p)):
        hs[("FP originals", half(p))].append(x | {"_rate": j["rate"]})
for (p, v), r in list(p2.items()) + list(p3.items()):
    j = jobs.get(p) or {}
    x = values(r)
    x["_rate"] = 48000 if v.startswith("ctl48") or v == "mp3_320_up48" else j.get("rate")
    x["_v"] = v
    if v.startswith("bait") or v == "ctl48_40k":
        if p not in doubted:
            hs[("FP bait", half(p))].append(x)
    elif j.get("rate") == 44100:  # (includes ctl48_opus160 of the 30 bait-derived ctl48 sources, as analyze.py does)
        hs[("recall transcodes", half(p))].append(x)
cands = {
    "spectrum (current)": lambda x: sim(x),
    "spectrum with TRACES_FROM 18 kHz": lambda x: sim(x, traces_from=18000),
    "spectrum + 25-30 dB with flicker >= 0.05": lambda x: None if sim(x) is None else sim(x) or (
        x["drop"] is not None and 25 <= x["drop"] < 30 and x["cutoff"] < 19000 and (x["fl_edge"] is None or x["fl_edge"] >= .05)),
    "spectrum + 48 kHz Opus band (19.8-20.5 kHz, drop >= 20)": lambda x: None if sim(x) is None else sim(x) or (
        x["_rate"] == 48000 and x["cutoff"] is not None and 19800 <= x["cutoff"] <= 20500 and (x["drop"] or 0) >= 20),
    "lossprint >= 0.5": lambda x: None if x["p"] is None else x["p"] >= .5,
    "spectrum OR lossprint": lambda x: None if x["p"] is None else bool(sim(x)) or x["p"] >= .5,
}
print("\n## Held-out halves")
held = {}
for name, rule in cands.items():
    row = {}
    for (kind, h), xs in sorted(hs.items()):
        ys = [bool(y) for y in map(rule, xs) if y is not None]
        row[f"{kind} {h}"] = (sum(ys), len(ys))
    held[(name,)] = row
    print(f"  {name:58s} " + " | ".join(f"{k} {v[0]}/{v[1]} = {100 * v[0] / v[1]:.1f}%" for k, v in row.items()))
problems += compare("held-out", summ["Candidate rules on two halves (held-out check)"], held)
rt = [x for h in ("half 1", "half 2") for x in hs[("recall transcodes", h)]]
print(f"  recall-transcode items: {len(rt)}, of them ctl48_opus160: {sum(x['_v'] == 'ctl48_opus160' for x in rt)}")
# 48 kHz Opus band rule on the unmarked originals (all, incl. YouTube): its hits and lossprint agreement
band = [(p, x) for p, j, f, x, m in originals if not j["spectrum_mark"] and j["rate"] == 48000 and x["cutoff"] is not None
        and 19800 <= x["cutoff"] <= 20500 and (x["drop"] or 0) >= 20]
print(f"48 kHz Opus band rule on unmarked originals: {len(band)} hits; lossprint >= 0.5 on {sum(x['p'] >= .5 for p, x in band)}")
band_all = [(p, x) for p, j, f, x, m in originals if j["rate"] == 48000 and x["cutoff"] is not None
            and 19800 <= x["cutoff"] <= 20500 and (x["drop"] or 0) >= 20]
print(f"  same incl. Echolot-marked originals: {len(band_all)} hits; lossprint >= 0.5 on {sum(x['p'] >= .5 for p, x in band_all)}")

# ---------------------------------------------------------------- lossprint threshold sweep
print("\n## lossprint threshold sweep")
negs = {"FP originals tier 1 + 2_proven (unmarked)": [x["p"] for p, j, f, x, m in originals if not j["spectrum_mark"]
                                                      and j["subtier"] in ("1", "2_proven")],
        "FP originals all (unmarked)": [x["p"] for p, j, f, x, m in originals if not j["spectrum_mark"]],
        "FP bait (all cut-offs)": [q for v in ("bait_32k", "bait_38k", "bait_40k") for q in lp_by[v]]}
lpsw = {}
for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99):
    row = {k: (sum(q >= t for q in xs), len(xs)) for k, xs in negs.items()}
    row["recall all transcodes"] = (sum(q >= t for q in pos_p), len(pos_p))
    lpsw[(str(t),)] = row
problems += compare("lossprint sweep", summ["lossprint threshold sweep"], lpsw)

print("\n## Not in summary.md: label circularity and source sensitivity")
circ = Counter()
for p, j, f, x, m in originals:
    stored = inv[p]["quality"] == "fake" or bool(inv[p]["lossy_sourced"])
    circ[(f["spectrum"] == stored, bool(j["spectrum_mark"]) == stored)] += 1
print(f"all originals: harness spectrum verdict == stored Echolot label, and spectrum_mark == that label: {dict(circ)}")
print(f"spectrum flags on all 2,500 originals (marked included): {fmt(sum(f['spectrum'] for p, j, f, x, m in originals), len(originals))}")
sens, sens_d = Counter(), Counter()
for (p, v), r in p2.items():
    if v.startswith("bait") or jobs[p]["rate"] != 44100 or "spectrum" not in r:
        continue
    f = flags(r)
    sens["n"] += 1
    sens["k"] += f["spectrum"]
    if p not in doubted:
        sens_d["n"] += 1
        sens_d["k"] += f["spectrum"]
print(f"pooled spectrum recall: {fmt(sens['k'], sens['n'])}; without the {len({p for p in doubted if 'B' in jobs[p]['sets'] and jobs[p]['rate'] == 44100})} "
      f"doubted 44.1 kHz B sources: {fmt(sens_d['k'], sens_d['n'])}")
for v in ("aac_256", "mp3_v0", "lame_v0", "opus_160", "vorbis_q9"):
    a = [flags(r)["spectrum"] for (p, vv), r in p2.items() if vv == v and jobs[p]["rate"] == 44100 and "spectrum" in r]
    b = [flags(r)["spectrum"] for (p, vv), r in p2.items() if vv == v and jobs[p]["rate"] == 44100 and "spectrum" in r
         and p not in doubted]
    print(f"  {v}: {fmt(sum(a), len(a))} -> without doubted sources {fmt(sum(b), len(b))}")

print("\n## Verification outcome")
print("\n".join(problems) if problems else "all compared cells agree with results/analysis/summary.md")
sys.exit(0)
