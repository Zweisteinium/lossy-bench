#!/usr/bin/env python3
"""Independent re-computation of the clip-free experiment (results/clipfree.jsonl), compared with the numbers in
results/analysis/summary.md and the 2026-10-15 answer. Usage: nice -n 19 python3 scripts/verify/v2_clipfree.py"""

import hashlib
from collections import Counter

from common import RES, fmt, has_youtube, jsonl, load_corpus, load_phase, values

jobs, inv = load_corpus()
p1, _ = load_phase(1)
p2, _ = load_phase(2)
cf = {}
lines = 0
for d in jsonl(RES / "clipfree.jsonl"):
    lines += 1
    cf[(d["path"], d["variant"])] = d  # last line per item counts
ok = {k: d for k, d in cf.items() if d.get("ok")}
print(f"lines {lines}, items {len(cf)}, ok {len(ok)}, not ok {len(cf) - len(ok)}: "
      f"{Counter(d.get('error') for d in cf.values() if not d.get('ok'))}")
orig = {k: d for k, d in ok.items() if k[1] == "original"}
print(f"originals measured: {len(orig)} of {sum('A' in j['sets'] for j in jobs.values())}; "
      f"variants: {len(ok) - len(orig)} ({len({k[0] for k in ok if k[1] != 'original'})} songs)")
print("same_as_echolot (all ok items):", dict(Counter(d.get("same_as_echolot") for d in ok.values())))
# selection check: measured = peak >= -0.05 dBFS (or no peak) in phase 1
sel = {p for p, j in jobs.items() if (p1[(p, "original")]["meta"]["out"].get("peak_db") is None
                                       or p1[(p, "original")]["meta"]["out"]["peak_db"] >= -0.05)}
print(f"originals with phase-1 peak >= -0.05 dBFS: {len(sel)}; equal to the measured set: {sel == {k[0] for k in orig}}")

clean = [p for p, j in jobs.items() if not j["spectrum_mark"] and not has_youtube(inv.get(p))]
neg = [(p, cf[(p, "original")]) for p in clean if (p, "original") in orig]
print(f"unmarked originals without a YouTube URL: {len(clean)}; measured (reach the clip level): {len(neg)}; "
      f"not measured: {len(clean) - len(neg)}; all originals not measured: {len(jobs) - len(orig)}")
flips = [(p, d) for p, d in neg if d["echolot"]["verdict"] != "lossy" and d["clipfree"]["verdict"] == "lossy"]
lost = [(p, d) for p, d in neg if d["echolot"]["verdict"] == "lossy" and d["clipfree"]["verdict"] != "lossy"]
lp = {p: values(p1[(p, "original")])["p"] for p in jobs}
conf = [p for p, d in flips if lp[p] >= 0.5]
rest = [(p, d) for p, d in flips if lp[p] < 0.5]
print(f"new flags: {fmt(len(flips), len(clean))}; lost: {len(lost)}; also lossprint >= 0.5: {len(conf)}; "
      f"not confirmed by lossprint: {fmt(len(rest), len(clean))}")
print("  not confirmed, by subtier:", dict(Counter(jobs[p]["subtier"] for p, d in rest)))
print("  their clip-free drop dB:", sorted(d["clipfree"]["drop_db"] for p, d in rest))
print(f"  of them with clip-free drop in [32, 36): {sum(32 <= d['clipfree']['drop_db'] < 36 for p, d in rest)}")
print("  flips by subtier:", dict(Counter(jobs[p]["subtier"] for p, d in flips)))

print("\nvariants (as Echolot -> clip-free), n = ok items:")
for v in sorted({k[1] for k in ok} - {"original"}):
    ds = [(k[0], d) for k, d in ok.items() if k[1] == v]
    a = sum(d["echolot"]["verdict"] == "lossy" for _, d in ds)
    c = sum(d["clipfree"]["verdict"] == "lossy" for _, d in ds)
    gained = [d for _, d in ds if d["echolot"]["verdict"] != "lossy" and d["clipfree"]["verdict"] == "lossy"]
    below36 = sum(d["clipfree"]["drop_db"] < 36 for d in gained)
    # consistency with phase 2 (same encoder, same source): Echolot's verdict on the phase-2 variant
    both = [(p, d) for p, d in ds if (p, v) in p2 and "spectrum" in p2[(p, v)]]
    agree = sum((values(p2[(p, v)])["verdict"] == "lossy") == (d["echolot"]["verdict"] == "lossy") for p, d in both)
    print(f"  {v:10s} as Echolot {fmt(a, len(ds))} | clip-free {fmt(c, len(ds))} | gained {len(gained)}, "
          f"of them clip-free drop < 36 dB: {below36} | phase-2 verdict agrees {agree}/{len(both)}")
src = sorted({k[0] for k in ok if k[1] != "original"})
print("positive songs: marked", sum(bool(jobs[p]["spectrum_mark"]) for p in src), "| salted order reproduces:",
      src == sorted(sorted((p for p, j in jobs.items() if "B" in j["sets"] and j["rate"] == 44100),
                           key=lambda p: hashlib.sha256(b"clipfree:" + p.encode()).hexdigest())[:60]))
