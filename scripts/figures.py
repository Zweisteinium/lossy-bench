# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib==3.10.7"]
# ///
"""Figures and the README summary table from the analysis output: results/analysis/summary.md (the k/n cells),
originals.csv and variants.csv (lossprint scores), and scripts/verify/v2_clipfree.py (clip-free recall).
Writes docs/figures/*.svg and prints the README table. Usage: uv run scripts/figures.py"""

import csv
import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANA = ROOT / "results" / "analysis"
OUT = ROOT / "docs" / "figures"
DETS = ["spectrum", "lossprint", "flaccheck"]
COLOR = {"spectrum": "#4C78A8", "lossprint": "#2CA02C", "flaccheck": "#E45756"}
LABEL = {"spectrum": "spectrum (Echolot)", "lossprint": "lossprint", "flaccheck": "flaccheck"}
GROUPS = [
    ("MP3 128 / 192", ["mp3_128", "mp3_192"]),
    ("MP3 320", ["mp3_320", "lame_320"]),
    ("MP3 VBR (V2, V0)", ["mp3_v2", "mp3_v0", "lame_v0"]),
    ("AAC 128 / 256", ["aac_128", "aac_256", "fdkaac_256", "fdkaac_vbr5"]),
    ("Vorbis q3 to q9", ["vorbis_q3", "vorbis_q6", "vorbis_q9", "oggenc_q6"]),
    ("Opus 96 / 160", ["opus_96", "opus_160", "opusenc_160"]),
    ("MP3 320, then gain or 48 kHz", ["mp3_320_gain", "mp3_320_up48"]),
]
KN = re.compile(r"\((\d+)/(\d+)\)")


def tables() -> dict:
    """{section title: {row label: {column: (k, n)}}} of summary.md."""
    out, section, header = {}, None, None
    for line in open(ANA / "summary.md", encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#"):
            section, header = line.lstrip("#").strip(), None
        elif not line.startswith("|"):
            header = None if not line.strip() else header
        elif header is None:
            header = [c.strip() for c in line.strip("|").split("|")]
        elif not set(line) <= set("|-"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            vals = {h: tuple(map(int, m.groups())) for h, c in zip(header, cells) if (m := KN.search(c))}
            out.setdefault(section, {})[cells[0]] = vals
    return out


def pct(x: float) -> str:
    """A rate in percent: one decimal below 10% (0.7%), none above (42%)."""
    return "0%" if x == 0 else f"{x:.1f}%" if x < 9.95 else f"{x:.0f}%"


def save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.svg")
    if os.environ.get("FIG_PNG"):  # review copies
        fig.savefig(Path(os.environ["FIG_PNG"]) / f"{name}.png", dpi=110)
    plt.close(fig)


def pool(rows: dict, variants: list[str], det: str) -> tuple[int, int]:
    return tuple(map(sum, zip(*(rows[v][det] for v in variants))))


def style(ax, title: str, pad: int = 12) -> None:
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=pad)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="x", color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)


def hbars(ax, labels: list[str], data: dict, note: dict | None = None) -> None:
    """Grouped horizontal bars: data[det] = [(k, n), ...] per label; Wilson intervals as whiskers."""
    h = 0.26
    for i, det in enumerate(DETS):
        ys = [j + (i - 1) * h for j in range(len(labels))]
        vals = [100 * k / n for k, n in data[det]]
        bars = ax.barh(ys, vals, h * 0.92, color=COLOR[det], label=LABEL[det])
        for j, (b, v) in enumerate(zip(bars, vals)):
            text = (note or {}).get((det, j)) or pct(v)
            ax.text(v + 1.2, b.get_y() + b.get_height() / 2, text, va="center", fontsize=7.5,
                    color="#333333")
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 112)
    ax.set_xticks(range(0, 101, 25), [f"{x}%" for x in range(0, 101, 25)])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "svg.fonttype": "path",
                         "figure.facecolor": "white", "axes.facecolor": "white"})
    t = tables()
    rec = t["Recall on transcodes (positives)"]
    fp = t["False positives on presumed-genuine originals (set A)"]
    bait = t["Bait: genuine audio behind a steep resampler edge (false positives)"]
    ctl = t["48 kHz control (phase 3): genuine with a 20 kHz edge (negative) vs Opus 160 at 48 kHz (positive)"]
    allv = [v for _, vs in GROUPS for v in vs]
    assert sorted(allv) == sorted(rec), "every recall row in exactly one group"

    # 1. detection per transcode group
    labels = [g for g, _ in GROUPS] + ["All transcodes"]
    data = {d: [pool(rec, vs, d) for _, vs in GROUPS] + [pool(rec, allv, d)] for d in DETS}
    fig, ax = plt.subplots(figsize=(8, 5.6))
    hbars(ax, labels, data)
    style(ax, "Transcodes detected (higher is better)", pad=28)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=8.5)
    fig.text(0.01, 0.01, f"{pool(rec, allv, 'lossprint')[1]:,} transcodes of 44.1 kHz sources. Per-encoding numbers with "
             "Wilson 95% intervals: docs/results.md.", fontsize=7, color="#666666")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "detection")

    # 2. false alarms on genuine audio
    orig = fp["all (unmarked, no YouTube URL in tags)"]
    neg = [("Original FLACs (2,381)", orig), ("Resampled via 32 kHz", bait["bait_32k"]),
           ("Resampled via 38 kHz", bait["bait_38k"]), ("Resampled via 40 kHz", bait["bait_40k"]),
           ("48 kHz, edge at 20 kHz", ctl["ctl48_40k"])]
    data = {d: [row[d] for _, row in neg] for d in DETS}
    fig, ax = plt.subplots(figsize=(8, 4.4))
    hbars(ax, [label for label, _ in neg], data, note={("spectrum", 0): "0% (by construction)"})
    style(ax, "Genuine audio flagged as lossy (lower is better)", pad=28)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=8.5)
    fig.text(0.01, 0.01, "Originals: lossprint's rate is an upper bound (part of its flags are real fakes); spectrum's "
             "0% is circular, the library's marks came from spectrum.", fontsize=7, color="#666666")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "false-alarms")

    # 3. scorecard: recall vs false alarms on resampled genuine audio
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    for d in DETS:
        k, n = pool(rec, allv, d)
        bk, bn = pool(bait, ["bait_32k", "bait_38k", "bait_40k"], d)
        x, y = 100 * bk / bn, 100 * k / n
        ax.scatter([x], [y], s=260, color=COLOR[d], zorder=3, edgecolor="white", linewidth=1.5)
        dx, dy, va = {"lossprint": (12, -6, "top"), "spectrum": (-14, -8, "top"), "flaccheck": (-14, 8, "bottom")}[d]
        ax.annotate(f"{LABEL[d]}\n{pct(y)} caught, {pct(x)} false alarms", (x, y), xytext=(dx, dy),
                    textcoords="offset points", fontsize=8.5, va=va, ha="left" if dx > 0 else "right")
    ax.set_xlim(-5, 105)
    ax.set_ylim(0, 108)
    ax.set_xlabel("False alarms: genuine audio resampled through 32, 38 or 40 kHz")
    ax.set_ylabel("Transcodes detected")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.text(-3, 104, "ideal: top left", fontsize=8, color="#666666")
    style(ax, "Overall: detection against false alarms")
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    fig.tight_layout()
    save(fig, "scorecard")

    # 4. lossprint scores: originals vs transcodes
    p_orig = [float(r["lp_p"]) for r in csv.DictReader(open(ANA / "originals.csv", encoding="utf-8"))
              if r["lp_p"] and not r["spectrum_mark"]]
    p_tc = [float(r["lp_p"]) for r in csv.DictReader(open(ANA / "variants.csv", encoding="utf-8"))
            if r["lp_p"] and r["variant"] in allv]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bins = [i / 50 for i in range(51)]
    ax.hist(p_tc, bins=bins, color=COLOR["lossprint"], alpha=0.55,
            label=f"transcodes, 44.1 and 48 kHz sources ({len(p_tc):,})")
    ax.hist(p_orig, bins=bins, histtype="step", color="#222222", linewidth=1.4,
            label=f"unmarked originals ({len(p_orig):,})")
    ax.set_yscale("log")
    ax.axvline(0.5, color="#333333", linestyle=":", linewidth=1)
    ax.axvline(0.9, color="#333333", linestyle="--", linewidth=1)
    ax.text(0.5, 0.62, " 0.5: doubtful", fontsize=7.5, transform=ax.get_xaxis_transform())
    ax.text(0.9, 0.62, " 0.9: lossy", fontsize=7.5, transform=ax.get_xaxis_transform())
    ax.set_xlabel("lossprint transcode probability")
    ax.set_ylabel("files (log scale)")
    ax.legend(loc="upper left", bbox_to_anchor=(0.22, 1.0), frameon=False, fontsize=8.5)
    style(ax, "lossprint scores are near 0 or near 1")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "lossprint-scores")

    # 5. clip-free: spectrum's recall as Echolot measures it and without clipped frames
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify" / "v2_clipfree.py")], capture_output=True,
                         text=True, check=True, cwd=ROOT / "scripts" / "verify").stdout
    pat = re.compile(r"^\s*(\w+)\s+as Echolot (\d+)/(\d+) .*\| clip-free (\d+)/(\d+)", re.M)
    cf = sorted(((m[1], int(m[2]) / int(m[3]), int(m[4]) / int(m[5])) for m in pat.finditer(run)), key=lambda c: c[1] - c[2])
    assert cf, "clip-free lines"
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for i, (v, a, b) in enumerate(cf):
        ax.plot([100 * a, 100 * b], [i, i], color="#bbbbbb", linewidth=3, zorder=1)
        ax.scatter([100 * a], [i], color="#9ecae1", s=70, zorder=2, label="as Echolot measures" if i == 0 else None)
        ax.scatter([100 * b], [i], color=COLOR["spectrum"], s=70, zorder=2, label="without clipped frames" if i == 0 else None)
        ax.text(max(a, b) * 100 + 2, i, f"{pct(100 * a)} → {pct(100 * b)}", va="center", fontsize=8)
    ax.set_yticks(range(len(cf)), [v.replace("_", " ") for v, _, _ in cf])
    ax.invert_yaxis()
    ax.set_xlim(40, 112)
    ax.set_xticks(range(40, 101, 10))
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=8.5)
    style(ax, "spectrum without clipped frames (60 songs per encoding)", pad=28)
    fig.tight_layout()
    save(fig, "clipfree")

    # the README table
    def cell(kn): return pct(100 * kn[0] / kn[1])
    print("| | spectrum | lossprint | flaccheck |\n|---|---|---|---|")
    print("| **Lossy files detected** (higher is better) | | | |")
    for (g, vs) in GROUPS:
        print(f"| {g} ({pool(rec, vs, 'lossprint')[1]:,}) | " + " | ".join(cell(pool(rec, vs, d)) for d in DETS) + " |")
    print("| **All transcodes** " + f"({pool(rec, allv, 'lossprint')[1]:,}) | "
          + " | ".join(f"**{cell(pool(rec, allv, d))}**" for d in DETS) + " |")
    print(f"| Opus 160 at 48 kHz ({ctl['ctl48_opus160']['lossprint'][1]}) | "
          + " | ".join(cell(ctl["ctl48_opus160"][d]) for d in DETS) + " |")
    print("| **Genuine audio flagged** (lower is better) | | | |")
    for label, row in neg:
        print(f"| {label} | " + " | ".join(cell(row[d]) for d in DETS) + " |")


if __name__ == "__main__":
    main()
