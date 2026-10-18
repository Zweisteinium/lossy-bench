#!/usr/bin/env python3
"""The 48 kHz control (phase 3) -> corpus/jobs_ctl48.jsonl, corpus/set_ctl48.csv.

Added during the run, after lossprint flagged 6 of 15 unmarked 48 kHz originals as "opus ~100-130 kbps": 5 of them
carry a YouTube URL in their tags (YouTube serves Opus at 48 kHz, band-limited at 20 kHz). The question it answers:
does lossprint react to Opus itself, or to any 48 kHz file with a steep 20 kHz edge? Sources are only trusted files
(tier 1 and 2_proven), chosen by provenance, never by a detector:
  - the 48 kHz tier-1 files of set A without a YouTube URL in their tags (all of them);
  - 30 bait sources (tiers 1 and 2_proven, 44.1 kHz), at most one per artist, in a stable sha256 order.
Each gets two variants at 48 kHz (run.py --phase 3): ctl48_40k (genuine, soxr through 40 kHz: a steep edge near
20 kHz; negative) and ctl48_opus160 (libopus 160k decoded at its native 48 kHz; positive).
"""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N_BAIT = 30


def youtube(item: dict) -> bool:
    t = json.dumps(item.get("tags") or {}).lower()
    return "youtube.com" in t or "youtu.be" in t


def main() -> None:
    inv = {json.loads(line)["path"]: json.loads(line) for line in open(ROOT / "corpus" / "inventory.jsonl", encoding="utf-8")}
    jobs = [json.loads(line) for line in open(ROOT / "corpus" / "jobs.jsonl", encoding="utf-8")]
    native = [j for j in jobs if j["rate"] == 48000 and j["subtier"] == "1" and not youtube(inv[j["path"]])]
    pool = sorted((j for j in jobs if "bait" in j["sets"]), key=lambda j: hashlib.sha256(j["path"].encode()).hexdigest())
    picked, artists = [], set()
    for j in pool:
        artist = j["path"].split("/", 1)[0].casefold()
        if artist in artists:
            continue
        artists.add(artist)
        picked.append(j)
        if len(picked) == N_BAIT:
            break
    chosen = [j | {"sets": ["ctl48"], "ctl48_source": "48k tier 1"} for j in native] + \
             [j | {"sets": ["ctl48"], "ctl48_source": "44.1k bait source"} for j in picked]
    with open(ROOT / "corpus" / "jobs_ctl48.jsonl", "w", encoding="utf-8") as f:
        for j in chosen:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    with open(ROOT / "corpus" / "set_ctl48.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "size", "mtime", "tier", "subtier", "rate", "bps", "source", "strata"])
        for j in chosen:
            w.writerow([j["path"], j["size"], j["mtime"], j["tier"], j["subtier"], j["rate"], j["bps"],
                        j["ctl48_source"], ";".join(j["strata"])])
    print(f"ctl48: {len(native)} native 48 kHz tier 1, {len(picked)} bait sources -> {len(chosen)} jobs")


if __name__ == "__main__":
    main()
