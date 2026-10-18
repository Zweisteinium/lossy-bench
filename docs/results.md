# Results

Results of the benchmark of three lossy-source detectors for FLAC on one private library of 5,092 FLACs: the
spectrum check of Echolot, a self-hosted library manager (`spectrum()`, commit e9f0bf9), lossprint 1.1.0 and
flaccheck 0.1.2. Methods and definitions: [methods.md](methods.md); data files: [data.md](data.md).

**Conventions.** Rates are given as percentage, Wilson 95% interval (z = 1.96) and k or k/n. A detector "flags" a
file when spectrum's verdict is `lossy`, lossprint's `transcode_probability` (p) is ≥ 0.5 unless another threshold
is named, or flaccheck's `transcode_verdict` is `TRANSCODED`. "Echolot-marked" means Echolot's stored label for the
file is lossy (`quality = fake` or a `lossy_sourced` entry); "unmarked" originals are all others.

Trust tiers of the originals (provenance only, never detector output): tier 1 **store-tagged** (store or stream
names in the tags, not proven); tier 2 **stream capture, hash-proven** (decoded audio identical to a capture of the
stream; sub-tiers `2_proven` exact capture, `2_fade` capture with the stream's fade-in, `2_altered` capture
reported altered); tier 3 **corroborated** (no store or stream provenance, at least three corroborating signs);
tier 4 **doubtful** (not used in set A).

## Contents

1. [Headline findings](#1-headline-findings)
2. [Material and completeness](#2-material-and-completeness)
3. [False positives on presumed-genuine originals](#3-false-positives-on-presumed-genuine-originals)
4. [Bait: genuine audio behind a resampler edge](#4-bait-genuine-audio-behind-a-resampler-edge)
5. [Recall per encoding](#5-recall-per-encoding)
6. [Recall by source format](#6-recall-by-source-format)
7. [48 kHz control](#7-48-khz-control)
8. [Threshold sweeps](#8-threshold-sweeps)
9. [Combined rules and the held-out check](#9-combined-rules-and-the-held-out-check)
10. [Clip-free experiment](#10-clip-free-experiment)
11. [Stream-capture ground truth](#11-stream-capture-ground-truth)
12. [Decision rule](#12-decision-rule)
13. [Limitations and threats to validity](#13-limitations-and-threats-to-validity)
14. [Verification](#14-verification)

## 1. Headline findings

1. **lossprint caught every transcode.** Recall on the transcodes of 44.1 kHz sources (20 encodings, 3,564 files)
   is 100.0% [99.9–100.0]; it also caught all 198 transcodes of the 48 kHz sources. Its lowest score on a transcode
   is 0.703, and 3,555 / 3,564 (99.7% [99.5–99.9]) score ≥ 0.9. On bait it flags 0.7% [0.2–2.1] (3 / 423).
2. **lossprint's flags on originals are an upper bound.** It flags 4.9% [4.1–5.9] (121 / 2,453) of the unmarked
   originals, but the flags concentrate where real fakes are likely: 44.4% of the files with a YouTube URL in their
   own tags, 49.4% of the 48 kHz files, 3.3% [2.7–4.1] of the 44.1 kHz files without a YouTube URL. The 48 kHz
   control shows that a genuine steep 20 kHz edge does not trigger it (0 / 32).
3. **spectrum's 0 false positives on unmarked originals hold by construction.** Echolot's stored marks were
   produced by spectrum itself, so the unmarked originals are exactly the files spectrum calls clean; 0 / 2,453 is
   a consistency check, not an estimate. Spectrum flags 47 / 2,500 (1.9% [1.4–2.5]) of all originals, 38 of them
   also flagged by lossprint. Its real false-positive evidence is the bait (100% at 32 and 38 kHz, 6.4% [3.4–11.7]
   at 40 kHz) and the 48 kHz control (2 / 32).
4. **spectrum misses everything without an encoder edge below ~19.5 kHz.** Pooled recall 42.3% [40.7–44.0]; MP3 V0
   8.8%, AAC 256 (ffmpeg) 1.1%, Vorbis q6 and q9 7.4% and 4.8%, Opus 2.1–6.9%.
5. **flaccheck is not usable as a detector here.** It flags 12.3% [11.0–13.6] of the unmarked originals and 90.1%
   [86.9–92.6] of the bait, at 52.4% [50.8–54.1] recall.
6. **Clipping hides encoder edges.** Measured without the clipped FFT frames, spectrum's recall rises from 58.3% to
   95.0% on MP3 V2, from 70.0% to 100.0% on AAC 128 and from 71.7% to 86.7% on MP3 320 (60 songs each), with 1.4%
   [1.0–1.9] new flags on originals, 0.4% [0.2–0.8] of them not confirmed by lossprint.
7. **Lowering spectrum's `TRACES_FROM` from 19 to 18 kHz** cuts its flags on bait and the 48 kHz control from 64.4%
   to 34.9% at identical recall and without new flags on originals; both held-out halves agree.
8. **Lossy masters exist.** Of 10 songs captured bit-exact from Spotify Lossless (9 disputed, 1 control), 8 have masters that
   lossprint scores ≥ 0.968 (lossy-sourced); 6 library copies are bit-identical to the stream. lossprint's score
   does not separate a lossy copy from a lossy master; only a capture of the stream does.
9. **Decision rule.** A spectrum verdict of lossy stands; otherwise lossprint p ≥ 0.9 is lossy and 0.5–0.9
   doubtful; a stream capture judged lossy counts as a lossy master ([section 12](#12-decision-rule)).

## 2. Material and completeness

| Set | Files | Use |
|---|---|---|
| A: originals | 2,500 (tier 1 270, 2_proven 124, 2_fade 8, 2_altered 9, tier 3 2,089) | negatives as they are; the 47 Echolot-marked reported apart |
| B: transcode sources | 200 of A (189 at 44.1 kHz, 11 at 48 kHz) | 18 transcodes each (positives) |
| processed | 108 of A | MP3 320 at −1.3 dB and MP3 320 resampled to 48 kHz (positives) |
| bait | 150 of A (tier 1 140, 2_proven 10) | soxr round trip through 32, 38 and 40 kHz (negatives) |
| 48 kHz control | 34 (4 native 48 kHz tier-1 files, 30 bait sources) | genuine through 40 kHz at 48 kHz (negative); Opus 160 at 48 kHz (positive) |

Echolot-marked: A 47 (tier 1 4, 2_proven 10, tier 3 33), B 4, bait 2, processed 2. A YouTube URL in the file's own
tags: 77 of A (76 tier 3, 1 tier 1; 72 unmarked).

| Item | Value |
|---|---|
| Phase 1 jobs (originals) complete | 2,500 / 2,500 |
| Phase 2 jobs (sources of B, bait, processed) complete | 212 / 212 |
| Phase 3 jobs (48 kHz control) complete | 34 / 34 |
| Phase 2 variants made / scored / rejected by the variant checks | 4,266 / 4,212 / 54 |
| Detector lines with `ok = false` in complete jobs | 0 |
| Originals changed during the run or failing to decode | 0 |

The 54 rejected variants come from 10 sources, all at 44.1 kHz: 8 sources lost their 5 ffmpeg-MP3 variants
(40 lines) and, where in the processed set (5 sources), both processed variants (10 lines); 2 sources lost both
ffmpeg-AAC variants (4 lines). No standalone-encoder, Opus, Vorbis or bait variant was rejected. Rejected lines only
lower n.

## 3. False positives on presumed-genuine originals

**Circularity.** Echolot's marks were set by its spectrum check: on all 2,500 originals the harness's spectrum
verdict equals the stored label (2,500 / 2,500, [section 14](#14-verification)). The unmarked originals are
therefore exactly the files spectrum calls clean, and spectrum's column below is 0 by construction. It is a
consistency check, not a false-positive estimate. Across all originals spectrum flags 47 / 2,500 (1.9% [1.4–2.5]);
lossprint flags 38 of those 47 (80.9% [67.5–89.6]). Spectrum's false-positive rate is measured only by the bait
([section 4](#4-bait-genuine-audio-behind-a-resampler-edge)) and the 48 kHz control ([section 7](#7-48-khz-control)).

For lossprint and flaccheck a flag on an original is a false positive only if the original is genuine; their rates
are upper bounds.

| Group (unmarked originals) | n | spectrum | lossprint | flaccheck |
|---|---|---|---|---|
| all | 2,453 | 0.0% [0.0–0.2] (0) | 4.9% [4.1–5.9] (121) | 12.3% [11.0–13.6] (301) |
| no YouTube URL in tags | 2,381 | 0.0% [0.0–0.2] (0) | 3.7% [3.0–4.6] (89) | 11.9% [10.7–13.3] (284) |
| YouTube URL in tags | 72 | 0.0% [0.0–5.1] (0) | 44.4% [33.5–55.9] (32) | 23.6% [15.3–34.6] (17) |
| tier 1 | 266 | 0.0% [0.0–1.4] (0) | 4.5% [2.6–7.7] (12) | 15.0% [11.2–19.8] (40) |
| tier 2_proven | 114 | 0.0% [0.0–3.3] (0) | 2.6% [0.9–7.5] (3) | 11.4% [6.8–18.5] (13) |
| tier 1 + 2_proven | 380 | 0.0% [0.0–1.0] (0) | 3.9% [2.4–6.4] (15) | 13.9% [10.8–17.8] (53) |
| tier 2_fade / 2_altered | 8 / 9 | 0 / 0 | 0 / 0 | 0 / 0 |
| tier 3 | 2,056 | 0.0% [0.0–0.2] (0) | 5.2% [4.3–6.2] (106) | 12.1% [10.7–13.5] (248) |
| 16 bit / 44.1 kHz | 2,078 | 0.0% [0.0–0.2] (0) | 2.8% [2.2–3.6] (58) | 11.7% [10.4–13.1] (243) |
| 24 bit / 44.1 kHz | 290 | 0.0% [0.0–1.3] (0) | 7.2% [4.8–10.8] (21) | 9.7% [6.8–13.6] (28) |
| 16 bit / 48 kHz | 23 | 0.0% [0.0–14.3] (0) | 73.9% [53.5–87.5] (17) | 26.1% [12.5–46.5] (6) |
| 24 bit / 48 kHz | 62 | 0.0% [0.0–5.8] (0) | 40.3% [29.0–52.7] (25) | 38.7% [27.6–51.2] (24) |
| 48 kHz pooled | 85 | 0.0% [0.0–4.3] (0) | 49.4% [39.0–59.8] (42) | 35.3% [26.0–45.9] (30) |
| 44.1 kHz, no YouTube URL | 2,326 | 0.0% [0.0–0.2] (0) | 3.3% [2.7–4.1] (77) | 11.6% [10.3–12.9] (269) |
| clipped (flat factor ≥ 1) | 608 | 0.0% [0.0–0.6] (0) | 14.3% [11.7–17.3] (87) | 7.4% [5.6–9.8] (45) |
| loud (RMS > −9 dB) | 641 | 0.0% [0.0–0.6] (0) | 8.0% [6.1–10.3] (51) | 8.6% [6.7–11.0] (55) |
| quiet (RMS < −18 dB) | 64 | 0.0% [0.0–5.7] (0) | 1.6% [0.3–8.3] (1) | 25.0% [16.0–36.8] (16) |
| *Echolot-marked (circular, apart)* | 47 | 100.0% [92.4–100.0] (47) | 80.9% [67.5–89.6] (38) | 80.9% [67.5–89.6] (38) |

The full stratum table (era, genre, live, vinyl, remaster, short, 24 bit, peak level) is in
`results/analysis/summary.md`.

- lossprint scores in the 0.5–0.9 band: 17 / 2,453 unmarked originals (0.7% [0.4–1.1]). p < 0.01: 2,257 / 2,500
  originals (90.3% [89.1–91.4]).
- Unmarked originals flagged by at least two of the three detectors: 41 (1.7% [1.2–2.3]; 35 tier 3, 6 tier 1).
  Originals on which the three detectors disagree: 397.
- The 9 Echolot-marked originals that lossprint scores below 0.5: 4 have a steep edge at 15.5–18.4 kHz (drop
  30.8–99.7 dB) at lossprint p < 0.01, with flaccheck agreeing on 3 of them; 5 have spectrum's "traces" verdict
  (edge 19.4–20.3 kHz, drop 32.1–48.6 dB). lossprint names 7 of the 9 "musepack".

## 4. Bait: genuine audio behind a resampler edge

soxr round trip 44.1 → 32 / 38 / 40 → 44.1 kHz of the 141 bait sources that are not doubted (doubted: Echolot-marked
or lossprint-flagged in their original form). Every flag is a false positive if the source is genuine.

| Bait | spectrum | lossprint | flaccheck |
|---|---|---|---|
| 32 kHz (edge ~15.3 kHz) | 100.0% [97.3–100.0] (141/141) | 1.4% [0.4–5.0] (2/141) | 90.1% [84.0–94.0] (127/141) |
| 38 kHz (edge ~18.1 kHz) | 100.0% [97.3–100.0] (141/141) | 0.7% [0.1–3.9] (1/141) | 87.9% [81.5–92.3] (124/141) |
| 40 kHz (edge ~19.1 kHz) | 6.4% [3.4–11.7] (9/141) | 0.0% [0.0–2.7] (0/141) | 92.2% [86.6–95.6] (130/141) |
| pooled | 68.8% [64.2–73.0] (291/423) | 0.7% [0.2–2.1] (3/423) | 90.1% [86.9–92.6] (381/423) |

Bait of the 9 doubted sources, reported apart (32 / 38 / 40 kHz): spectrum 9/9, 9/9, 7/9; lossprint 5/9, 8/9, 8/9;
flaccheck 9/9, 6/9, 7/9. Over all 450 bait files including doubted ones, lossprint p < 0.01 on 420 (93.3%
[90.6–95.3]) and p ≥ 0.5 on 24 (5.3% [3.6–7.8]), 21 of which belong to doubted sources.

## 5. Recall per encoding

Transcodes of the 189 set-B sources at 44.1 kHz (processed variants: 103 sources). n is below 189 where the variant
checks rejected lines ([section 2](#2-material-and-completeness)).

| Encoding | n | spectrum | lossprint | flaccheck | lossprint min p |
|---|---|---|---|---|---|
| mp3_128 (ffmpeg) | 181 | 91.2% [86.1–94.5] | 100.0% [97.9–100.0] | 84.0% [77.9–88.6] | 1.000 |
| mp3_192 | 181 | 88.4% [82.9–92.3] | 100.0% [97.9–100.0] | 74.6% [67.8–80.4] | 1.000 |
| mp3_320 | 181 | 73.5% [66.6–79.4] | 100.0% [97.9–100.0] | 77.9% [71.3–83.3] | 0.933 |
| mp3_v2 | 181 | 62.4% [55.2–69.2] | 100.0% [97.9–100.0] | 61.3% [54.1–68.1] | 1.000 |
| mp3_v0 | 181 | 8.8% [5.5–13.9] | 100.0% [97.9–100.0] | 21.5% [16.2–28.1] | 0.992 |
| lame_320 (LAME CLI) | 189 | 74.1% [67.4–79.8] | 100.0% [98.0–100.0] | 78.8% [72.5–84.1] | 0.933 |
| lame_v0 | 189 | 9.0% [5.7–13.9] | 100.0% [98.0–100.0] | 21.7% [16.4–28.1] | 0.987 |
| aac_128 (ffmpeg) | 187 | 68.4% [61.5–74.7] | 100.0% [98.0–100.0] | 70.6% [63.7–76.7] | 1.000 |
| aac_256 | 187 | 1.1% [0.3–3.8] | 100.0% [98.0–100.0] | 8.6% [5.3–13.4] | 0.945 |
| fdkaac_256 (CBR) | 189 | 98.4% [95.4–99.5] | 100.0% [98.0–100.0] | 82.5% [76.5–87.3] | 0.703 |
| fdkaac_vbr5 | 189 | 80.4% [74.2–85.5] | 100.0% [98.0–100.0] | 82.0% [75.9–86.8] | 0.995 |
| vorbis_q3 (ffmpeg) | 189 | 49.2% [42.2–56.3] | 100.0% [98.0–100.0] | 47.1% [40.1–54.2] | 1.000 |
| vorbis_q6 | 189 | 7.4% [4.5–12.0] | 100.0% [98.0–100.0] | 24.9% [19.2–31.5] | 0.999 |
| vorbis_q9 | 189 | 4.8% [2.5–8.8] | 100.0% [98.0–100.0] | 20.1% [15.0–26.4] | 0.854 |
| oggenc_q6 | 189 | 7.4% [4.5–12.0] | 100.0% [98.0–100.0] | 24.9% [19.2–31.5] | 0.999 |
| opus_96 (ffmpeg) | 189 | 2.1% [0.8–5.3] | 100.0% [98.0–100.0] | 43.4% [36.5–50.5] | 0.999 |
| opus_160 | 189 | 6.3% [3.7–10.8] | 100.0% [98.0–100.0] | 45.5% [38.6–52.6] | 0.895 |
| opusenc_160 | 189 | 6.9% [4.1–11.4] | 100.0% [98.0–100.0] | 42.9% [36.0–50.0] | 0.907 |
| mp3_320_gain (−1.3 dB) | 103 | 89.3% [81.9–93.9] | 100.0% [96.4–100.0] | 92.2% [85.4–96.0] | 1.000 |
| mp3_320_up48 (48 kHz s32) | 103 | 44.7% [35.4–54.3] | 100.0% [96.4–100.0] | 74.8% [65.6–82.2] | 0.870 |
| **pooled** | 3,564 | 42.3% [40.7–44.0] (1,509) | 100.0% [99.9–100.0] (3,564) | 52.4% [50.8–54.1] (1,869) | 0.703 |

k per cell is in `results/analysis/summary.md`.

- Every transcode spectrum caught also has lossprint p ≥ 0.5: 1,509 / 1,509 pooled, 1,625 / 1,625 over all phase-2
  transcodes of either source rate.
- **Sensitivity to doubted sources.** 9 of the 189 pooled sources are Echolot-marked or lossprint-flagged in their
  original form, so their variants may be transcodes of lossy audio. Without them spectrum's pooled recall is
  41.7% [40.0–43.4] (1,419 / 3,404), and the low-recall encodings drop further (aac_256 1.1% → 0.0% (0/178), mp3_v0
  8.8% → 6.3%, lame_v0 9.0% → 6.1%, opus_160 6.3% → 4.4%, vorbis_q9 4.8% → 2.8%): part of spectrum's few hits on
  high-bitrate encodings came from the source's own edge. lossprint stays at 100%.

## 6. Recall by source format

Pooled over all positive variants per source format. 44.1 kHz: the 20 encodings of section 5; 48 kHz: the 18
transcodes of the 11 set-B sources at 48 kHz, which are kept out of every other pooled number.

| Source format | n | spectrum | lossprint | lossprint ≥ 0.9 | flaccheck |
|---|---|---|---|---|---|
| 16 bit / 44.1 kHz | 2,909 | 41.7% [39.9–43.5] (1,212) | 100.0% [99.9–100.0] | 99.7% [99.5–99.9] (2,901) | 52.4% [50.6–54.2] (1,524) |
| 24 bit / 44.1 kHz | 655 | 45.3% [41.6–49.2] (297) | 100.0% [99.4–100.0] | 99.8% [99.1–100.0] (654) | 52.7% [48.8–56.5] (345) |
| 16 bit / 48 kHz (3 sources) | 54 | 64.8% [51.5–76.2] (35) | 100.0% [93.4–100.0] | 100.0% [93.4–100.0] (54) | 70.4% [57.2–80.9] (38) |
| 24 bit / 48 kHz (8 sources) | 144 | 56.2% [48.1–64.1] (81) | 100.0% [97.4–100.0] | 100.0% [97.4–100.0] (144) | 68.1% [60.1–75.1] (98) |

Per encoding and format: `results/analysis/summary.md`, "Recall by source format"; lossprint is at 100% in every
cell. Spectrum's higher recall at 48 kHz comes from encodings it otherwise misses (e.g. lame_v0 7.1% (11/154) at
16 bit / 44.1 kHz, 3/8 at 24 bit / 48 kHz). At 48 kHz FDK 256 is 11/11 and Opus 160 3/11 for spectrum.

## 7. 48 kHz control

Sources of tiers 1 and 2_proven (32 not doubted; the 2 doubted ones apart).

| Variant | spectrum | lossprint | flaccheck | lossprint p range |
|---|---|---|---|---|
| ctl48_40k (genuine, steep edge near 20 kHz; negative) | 6.2% [1.7–20.1] (2/32) | 0.0% [0.0–10.7] (0/32) | 87.5% [71.9–95.0] (28/32) | 0 – 1.06e-03 |
| ctl48_opus160 (positive) | 6.2% [1.7–20.1] (2/32) | 100.0% [89.3–100.0] (32/32) | 43.8% [28.2–60.7] (14/32) | 0.996 – 1.000 |

lossprint separates Opus at 48 kHz from a genuine 48 kHz file with a 20 kHz edge; its flags on 48 kHz originals
(49.4%, section 3) are therefore not explained by the edge alone.

## 8. Threshold sweeps

**lossprint.** Recall on the 3,564 pooled transcodes and flags on negatives at selected thresholds:

| Threshold | Recall | FP unmarked tier 1 + 2_proven (380) | FP all unmarked originals (2,453) | FP bait (423) |
|---|---|---|---|---|
| 0.5 | 100.0% [99.9–100.0] (3,564) | 3.9% [2.4–6.4] (15) | 4.9% [4.1–5.9] (121) | 0.7% [0.2–2.1] (3) |
| 0.8 | 100.0% [99.8–100.0] (3,563) | 3.7% [2.2–6.1] (14) | 4.6% [3.8–5.5] (113) | 0.2% [0.0–1.3] (1) |
| 0.9 | 99.7% [99.5–99.9] (3,555) | 2.6% [1.4–4.8] (10) | 4.2% [3.5–5.1] (104) | 0.2% [0.0–1.3] (1) |
| 0.95 | 99.6% [99.3–99.7] (3,548) | 2.6% [1.4–4.8] (10) | 4.1% [3.4–5.0] (101) | 0.2% [0.0–1.3] (1) |
| 0.99 | 99.2% [98.9–99.5] (3,537) | 2.4% [1.3–4.4] (9) | 4.0% [3.3–4.8] (98) | 0.2% [0.0–1.3] (1) |

At 0.84 recall is 99.9% [99.8–100.0] (3,562). The 9 transcodes below 0.9: six fdkaac_256 (0.703, 0.808, 0.841,
0.848, 0.855, 0.898), vorbis_q9 0.854, mp3_320_up48 0.870, opus_160 0.895. Over all 3,762 phase-2 transcodes (both
source rates) 3,753 score ≥ 0.9 (99.8% [99.5–99.9]); the minimum is 0.703, 9 lie in [0.7, 0.9), none below 0.7.
Thresholds 0.3–0.99: `summary.md`, "lossprint threshold sweep".

**spectrum.** Its decision was replayed from the stored cutoff, drop and flicker over a grid of DROP_DB {25, 27, 28,
30 dB} × TRACES_FROM {17, 17.5, 18, 18.5, 19 kHz} × FLICKER {0.02, 0.03, 0.05} (60 rows, all in `summary.md`).
Negatives: unmarked originals without a YouTube URL (2,381); bait that is not doubted plus ctl48_40k (423 + 32 =
455). Positives: the pooled transcodes plus the 34 ctl48_opus160 (3,598). Away from Echolot's constants the
originals' column is no longer 0 by construction.

| DROP_DB / TRACES_FROM / FLICKER | FP originals | FP bait + ctl48_40k | Recall |
|---|---|---|---|
| 30 / 19 kHz / 0.03 (Echolot) | 0.0% [0.0–0.2] (0) | 64.4% [59.9–68.7] (293) | 42.1% [40.5–43.7] (1,515) |
| 30 / 18 kHz / 0.03 | 0.0% [0.0–0.2] (0) | 34.9% [30.7–39.4] (159) | 42.1% [40.5–43.7] (1,515) |
| 30 / 18 kHz / 0.02 | 0.3% [0.2–0.7] (8) | 37.4% [33.0–41.9] (170) | 45.7% [44.0–47.3] (1,643) |
| 28 / 18 kHz / 0.03 | 0.6% [0.4–1.0] (14) | 34.9% [30.7–39.4] (159) | 46.1% [44.5–47.7] (1,658) |
| 25 / 18 kHz / 0.02 | 2.3% [1.7–2.9] (54) | 37.4% [33.0–41.9] (170) | 55.6% [54.0–57.2] (2,001) |

- The bait column depends only on TRACES_FROM: 63.5–66.2% at 18.5 and 19 kHz, 33.4–37.4% at 17–18 kHz.
- Flags on originals depend on DROP_DB and FLICKER: 0 at 30 dB with FLICKER ≥ 0.03, up to 2.4% (58) at 25 dB and
  0.02.
- The highest recall in the grid is 55.6%.

## 9. Combined rules and the held-out check

**Combined rules.** Negatives: unmarked originals (2,453) and bait that is not doubted (423); positives: the 3,564
pooled transcodes. The originals' column inherits spectrum's circularity: a rule that requires spectrum is 0 there by
construction.

| Rule | FP originals | FP bait | Recall |
|---|---|---|---|
| spectrum OR lossprint | 4.9% [4.1–5.9] (121) | 68.8% [64.2–73.0] (291) | 100.0% [99.9–100.0] (3,564) |
| spectrum AND lossprint | 0.0% [0.0–0.2] (0) | 0.7% [0.2–2.1] (3) | 42.3% [40.7–44.0] (1,509) |
| lossprint AND flaccheck | 1.7% [1.2–2.3] (41) | 0.7% [0.2–2.1] (3) | 52.4% [50.8–54.1] (1,869) |
| 2 of 3 | 1.7% [1.2–2.3] (41) | 60.5% [55.8–65.1] (256) | 59.8% [58.2–61.4] (2,132) |

**Held-out check.** Candidate rules on two halves split by a salted sha256 of the source path. Negatives: unmarked
originals without a YouTube URL, bait that is not doubted, and ctl48_40k; positives: transcodes of 44.1 kHz sources
including ctl48_opus160 of the 30 bait-derived control sources (3,594).

| Rule | FP originals half 1 / 2 | FP bait half 1 / 2 | Recall half 1 / 2 |
|---|---|---|---|
| spectrum (Echolot) | 0.0% [0.0–0.3] (0/1,176) / 0.0% [0.0–0.3] (0/1,205) | 63.8% [57.4–69.7] (148/232) / 65.0% [58.6–71.0] (145/223) | 41.5% [39.2–43.8] (739/1,780) / 42.8% [40.5–45.1] (776/1,814) |
| TRACES_FROM 18 kHz | 0 / 0 | 35.3% [29.5–41.7] (82) / 34.5% [28.6–41.0] (77) | 41.5% (739) / 42.8% (776) |
| + 25–30 dB edges with flicker ≥ 0.05 | 0.4% [0.2–1.0] (5) / 0.5% [0.2–1.1] (6) | 63.8% / 65.0% | 45.2% [42.9–47.5] (804) / 46.1% [43.8–48.4] (836) |
| + 48 kHz Opus band (19.8–20.5 kHz, drop ≥ 20 dB) | 0.6% [0.3–1.2] (7) / 0.2% [0.1–0.7] (3) | 63.8% / 65.0% | 44.1% [41.8–46.4] (785) / 44.2% [41.9–46.5] (802) |
| lossprint ≥ 0.5 | 3.6% [2.7–4.8] (42) / 3.9% [2.9–5.1] (47) | 0.4% [0.1–2.4] (1) / 0.9% [0.2–3.2] (2) | 100.0% [99.8–100.0] / 100.0% [99.8–100.0] |
| spectrum OR lossprint | 3.6% (42) / 3.9% (47) | 63.8% / 65.0% | 100.0% / 100.0% |

The halves agree for every rule. The 48 kHz Opus band rule hits 37 unmarked 48 kHz originals (27 of them with a
YouTube URL); lossprint ≥ 0.5 agrees on 35 of the 37 (94.6% [82.3–98.5]).

## 10. Clip-free experiment

Spectrum's edge search repeated without the FFT frames that contain a clipped sample (|x| ≥ 0.999).

| Item | Value |
|---|---|
| Items measured | 1,471, all ok: the 1,111 originals with a phase-1 peak ≥ −0.05 dBFS, and 60 B songs × 6 encodings |
| Self-check: as-Echolot path equals `spectrum()` | 1,470 / 1,471 (one differs by 0.0005 in flicker at the 0.03 boundary) |
| Unmarked originals without a YouTube URL | 2,381: 1,016 measured; 1,365 have no clipped frame and are unchanged by construction |
| New flags on those originals | 33 / 2,381 = 1.4% [1.0–1.9] (24 tier 3, 8 tier 1, 1 tier 2_fade); flags lost: 0 |
| of them also lossprint ≥ 0.5 | 23 |
| not confirmed by lossprint | 10 / 2,381 = 0.4% [0.2–0.8] (5 tier 3, 4 tier 1, 1 tier 2_fade); clip-free drop of 6 of them in [32, 36) dB |
| Phase-2 spectrum verdict equals the experiment's as-Echolot verdict | 345 / 345 comparable (song, encoding) pairs |

| Encoding (60 songs) | as Echolot | clip-free |
|---|---|---|
| mp3_192 | 90.0% [79.9–95.3] (54) | 100.0% [94.0–100.0] (60) |
| mp3_320 | 71.7% [59.2–81.5] (43) | 86.7% [75.8–93.1] (52) |
| lame_320 | 71.7% [59.2–81.5] (43) | 85.0% [73.9–91.9] (51) |
| mp3_v2 | 58.3% [45.7–69.9] (35) | 95.0% [86.3–98.3] (57) |
| aac_128 | 70.0% [57.5–80.1] (42) | 100.0% [94.0–100.0] (60) |
| vorbis_q3 | 46.7% [34.6–59.1] (28) | 95.0% [86.3–98.3] (57) |

A 36 dB minimum for flags that only appear clip-free would remove those 6 originals and one gained hit each on
mp3_320 and lame_320; it was chosen on the same sample and is not held out. The 60 positive songs carry no Echolot
mark; 5 of them had their ffmpeg-MP3 variants rejected in phase 2 but are included here (the experiment does not
apply the length check). Bait was not measured clip-free.

## 11. Stream-capture ground truth

Ten songs were captured bit-exact from Spotify Lossless. All are songs whose library copy lossprint flags (p ≥ 0.5)
and spectrum does not, at 44.1 kHz, none in set A: nine without an encoder signature visible in the spectrogram,
and FindMyName – Rebel, with a visible MP3 signature, as positive control. Each capture's decoded audio matches the
MD5 recorded at capture time; Turno – Killer VIP's capture is bit-exact except for the stream's ~10 ms fade-in at
the start. Spotify serves what the
label delivered, so a capture is the release as distributed, and a lossy-sourced capture means a lossy-sourced
master.

The captures were scored with spectrum and lossprint in the Echolot image (`results/capture-check/recs_scan.jsonl`)
and compared with the library copies sample by sample (`scripts/align_diff.py`, `results/capture-check/align.jsonl`):
lag of the best cross-correlation over the first 30 s, then over the overlap the share of identical samples at the
coarser bit depth, the residual relative to the capture and the least-squares gain.

| Song | Bits library / capture | Length library − capture (samples) | Lag (samples) | Identical | Residual | lossprint library | lossprint capture | spectrum capture | Reading |
|---|---|---|---|---|---|---|---|---|---|
| FindMyName – Rebel | 16 / 16 | +32 | 3,038 | 100% | none | 1.0000 mp3 288 | 1.0000 mp3 289 | ok (19.8 kHz, 24.3 dB) | lossy master, copy identical |
| Hedex – Clara | 16 / 16 | +37 | 1,288 | 100% | none | 0.9998 mp3 280 | 0.9999 mp3 278 | ok | lossy master, copy identical |
| Indivision – Untold Words | 16 / 16 | +29 | 1,284 | 100% | none | 1.0000 mp3 300 | 1.0000 mp3 298 | ok | lossy master, copy identical |
| keshi – i swear i'll never leave again | 16 / 16 | +1 | 0 | 100% | none | 1.0000 aac 258 | 1.0000 aac 258 | ok | lossy master, copy identical |
| mxmtoon – cliché | 16 / 16 | +5 | 0 | 100% | none | 1.0000 aac 300 | 1.0000 aac 300 | ok | lossy master, copy identical |
| Sydney Rose – Novels | 16 / 16 | +28 | 798 | 100% | none | 1.0000 aac 216 | 1.0000 aac 207 | ok | lossy master, copy identical |
| Pink Sweat$ – Cocaine | 16 / 24 | +14 | 1 | 50.2% at 16 bit | −79.4 dB | 0.8957 mp3 322 | 0.9681 mp3 322.5 | ok | lossy master, copy reduced to 16 bit |
| Zeph – Forever & Always | 16 / 24 | +41 | 0 | 50.2% at 16 bit | −75.8 dB | 1.0000 aac 273 | 1.0000 aac 255 | **lossy** (18.9 kHz, 36.3 dB) | lossy master, copy reduced to 16 bit |
| Taylor Swift – Everything Has Changed | 16 / 16 | +1,991 | 1,082 | 1.3% | −30.2 dB (gain 1.00095) | 1.0000 aac 264 | 0.0000 | ok | clean master, lossy copy |
| Turno – Killer VIP | 24 / 24 | +2,305 | 2,113 | 0.004% | −26.0 dB (gain 1.00487) | 1.0000 aac 300 | 0.0000 | ok | clean master, lossy copy |

"aac" is lossprint's `ffmpeg_aac` family. Bit depths, length differences and the library-side lossprint values come
from the same comparison run; the repository keeps the alignment results and the scan of the captures.

- No library copy is MD5-identical to its capture (lengths differ by 1 to 2,305 samples), but 6 are bit-identical
  over the aligned overlap, and 2 are the same master reduced to 16 bit (residual below −75 dB).
- **Lossy-sourced masters** (capture lossprint ≥ 0.9): 8 / 10, 80.0% [49.0–94.3]. This is not a rate for the
  library: the 10 were chosen as disputed cases.
- **Lossy copies of clean masters:** 2 / 10 (Taylor Swift, Turno). The capture scores p < 1e-4, the library copy
  1.0000, and the copy differs from the stream with a residual of −30 / −26 dB. In the comparison run the residual
  rose with frequency (from −35.4 / −33.5 dB below 4 kHz to −14.2 / −14.7 dB at 19–22 kHz) at a lag constant over
  the song, which reads as codec noise rather than a different master; `align.jsonl` keeps only the scalar values.
- **lossprint's p does not separate master from copy.** The 8 lossy masters score 0.968–1.000 on the capture, like
  lossy copies. Its bitrate estimate moves by up to 9 kbps on bit-identical audio (Sydney Rose 216 vs 207), so
  "same encoder and bitrate" is no match rule, and on the same master its p crosses the 0.9 threshold between the
  16-bit copy and the 24-bit capture (Pink Sweat$: 0.8957 vs 0.9681).
- **spectrum** calls 1 of the 10 captures lossy: Spotify's own 24-bit Zeph master (edge 18.9 kHz, 36.3 dB), which
  lossprint also scores as lossy-sourced.

## 12. Decision rule

The rule that follows from sections 3–11:

1. **A spectrum verdict of lossy always stands.** On the modelled encoders spectrum adds no recall to lossprint
   (every spectrum hit is a lossprint hit, 1,625 / 1,625). On real files it does: 9 of the 47 originals spectrum
   flags score below 0.5 on lossprint, 4 of them with a steep edge at 15.5–18.4 kHz and a drop of 30.8–99.7 dB that
   lossprint scores below 0.01. The cost is spectrum's false positives on genuine audio behind a resampler edge at
   38 kHz or below (section 4); its rate on the library itself cannot be measured here (section 3).
2. **Otherwise lossprint p ≥ 0.9 is lossy.** At 0.9 recall stays at 99.7% [99.5–99.9] (3,555 / 3,564; all 9 misses
   lie in 0.70–0.90), while flags drop on unmarked tier 1 + 2_proven originals from 3.9% to 2.6% and on bait from
   0.7% to 0.2%.
3. **lossprint 0.5 ≤ p < 0.9 is doubtful,** a label without a decision. The band holds both classes: 17 of 2,453
   unmarked originals (0.7% [0.4–1.1]), 9 of 3,564 transcodes (0.3% [0.1–0.5]) and one lossy master's library copy
   (Pink Sweat$, 0.8957).
4. **A stream capture judged lossy counts as a lossy master.** A lossy-sourced capture of the official stream is the
   best version that stream offers; a library copy identical to it is not a transcode of a better source. A copy
   that differs from a clean capture (Taylor Swift, Turno) remains a lossy copy. No detector score makes this
   distinction (section 11).

## 13. Limitations and threats to validity

**Labels.**
- **spectrum's false-positive rate on originals is 0 by construction.** The stored marks equal spectrum's verdict on
  all 2,500 originals, so the unmarked negatives are exactly the files spectrum calls clean (section 3).
  Independent evidence on spectrum's false positives comes only from the bait and the 48 kHz control.
- **Tier 1 is tags only, and tags are copied onto transcodes.** 6 of the 41 originals flagged by two detectors and
  8 of the 33 clip-free flags are tier 1; tier-1 lossprint rate 4.5% vs 2.6% for tier 2_proven.
- **Tier 3 holds real fakes.** 35 of the 41 two-detector candidates are tier 3; tier-3 lossprint rate 5.2%
  [4.3–6.2] (106 / 2,056).
- **Tier 2 proves the stream, not the master.** 10 of the 124 2_proven originals are Echolot-marked, and 3 of the
  other 114 are lossprint flags; the capture comparison found 8 lossy masters among 10 disputed songs.
- **lossprint's false-positive rates are upper bounds.** Its flags concentrate on files with a YouTube URL in their
  tags (44.4% vs 3.7% without) and at 48 kHz (49.4% vs 3.3% at 44.1 kHz without a YouTube URL), and the 48 kHz
  control shows that it does not react to a genuine 20 kHz edge. The remaining 44.1 kHz lossprint-only flags have
  no per-file ground truth.
- **"Doubted" uses detector output.** Bait and control sources are split by Echolot's mark and by lossprint itself.
  This favours lossprint on the bait: 21 of the 24 bait files with p ≥ 0.5 belong to doubted sources.
- **Clipping is confounded with a lossy source:** a lossy round trip of a loud master clips by itself, so the
  clipped stratum mixes loud genuine masters and fakes.

**Positives and negatives.**
- Positives are synthetic: 18 encodings by current encoders, one version each, one generation. Real fakes also come
  from other encoders: 4 Echolot-marked originals with a steep 15.5–18.4 kHz edge score lossprint p < 0.01
  (section 3). lossprint's training data are unknown; overlap with the benchmark's encoders (ffmpeg, LAME) cannot be
  excluded, so its 100% may be optimistic for unseen encoders.
- 9 of the 189 pooled B sources are doubted themselves; their variants are transcodes of possibly lossy audio
  (sensitivity in section 5).
- Set B has 11 sources at 48 kHz; they are out of every pooled number and reported by format (section 6).
- Bit depth differs between classes for 24-bit sources: variants are decoded to 16 bit (except mp3_320_up48) while
  their originals stay 24 bit ([methods.md](methods.md)).
- Bait covers soxr resampling only, not other mastering low-pass filters.
- The 54 rejected variants (10 sources) lower n non-randomly: they are sources whose length hits an ffmpeg edge case.

**Sample.**
- One library of 5,092 FLACs: 4,639 with an import record in Echolot, 453 from before Echolot.
- Genre and era skew (library, from tags): electronic 1,912 (37.5%), genre missing or unknown 1,937 (38.0%),
  rock/metal 214 (4.2%), classical/acoustic 160 (3.1%); releases of the 2010s and 2020s 4,440 (87.2%).
- spectrum's thresholds were developed on this library (Echolot commit 4ea672f), so its replay and threshold grid
  are in-sample; only the held-out halves guard the rule comparison, and both halves come from the same library.
- Rules tuned after seeing results (clip-free 36 dB minimum, 48 kHz Opus band) are not confirmed out of sample.
- The stream-capture ground truth covers 10 hand-picked disputed songs; 8 / 10 is not a library rate.

## 14. Verification

The numbers in sections 2–10 were recomputed from the raw data (`results/phase{1,2,3}.jsonl`,
`results/clipfree.jsonl`, `corpus/`) by independent stdlib scripts that do not import `scripts/analyze.py`:

| Script | Covers |
|---|---|
| `scripts/verify/v1_benchmark.py` | completeness, sets, reproduction, false positives, bait, recall, 48 kHz control, combined rules, replay, held-out, lossprint sweep; compares every `(k/n)` cell of `results/analysis/summary.md` |
| `scripts/verify/v2_clipfree.py` | clip-free experiment |

Run with `nice -n 19 python3 scripts/verify/v1_benchmark.py` (likewise `v2_clipfree.py`). All 1,460 `(k/n)` cells of
`summary.md` (false positives 148, bait 24, recall 80, recall by source format 328, 48 kHz control 16, combined
rules 12, spectrum threshold sweep 780, held-out 36, lossprint sweep 36) and all 20 "lossprint min p" values agree
with the re-computation, as do the clip-free numbers. `scripts/analyze.py` rebuilds `results/analysis/` from the
published data byte for byte. Section 6 and the 9 marked originals in section 3 come from
`results/analysis/variants.csv`, `originals.csv` and `corpus/jobs.jsonl`; section 11 from `results/capture-check/`
and the comparison run.

**Definitions.** The re-computation follows `analyze.py`: only complete jobs count (an attempt ending in `job_done`
with `ok = true`; for a job run twice, its last complete attempt); Echolot-marked originals apart; bait of doubted
sources apart; the 11 set-B sources at 48 kHz out of pooled recall. One deviation: "not complete" counts every job
with any line but no successful `job_done`, also one without a terminator line, where `analyze.py` counts only jobs
with a `job_done` or `job_error` line; in this run both are 0. Groups not in `summary.md` (tier 1 + 2_proven pooled,
48 kHz pooled, 44.1 kHz without a YouTube URL) and the sensitivity analysis without doubted sources are marked as
extra in the verification output.

**Reproduction of Echolot's verdicts.**

| Check | Result |
|---|---|
| Harness `spectrum()` vs Echolot's stored verdict, set-A files imported since 2026-10-02T17:00 (after commit 4ea672f set the current thresholds) | 860 / 860 agree, 100.0% [99.6–100.0] (22 of them stored lossy) |
| Same over all 2,500 originals | 2,500 / 2,500 agree |
| Replay of spectrum's decision from stored cutoff, drop and flicker at Echolot's constants | 6,579 / 6,582 agree, 100.0% [99.9–100.0]; 3 differ (stored drop exactly 30.0 dB, unrounded just below) |
| `edge_check` (a widened second call found the same edge), all files with drop ≥ 25 dB | 3,446 / 3,446 |
| Run's decoded-audio MD5 of tier-2 originals equals the hash that put them in tier 2 | 141 / 141 |
