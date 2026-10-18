# Data dictionary

Every data file in `corpus/` and `results/`: what it is, which script produced it, size, fields and checksum. How the
files were used: [methods.md](methods.md); the numbers derived from them: [results.md](results.md).

**Conventions.** Library paths are relative to the library's `tracks/` directory (`Artist/Artist - Title.flac`)
unless a prefix is named (`tracks/...`, or `/music/tracks/...` inside the Echolot container). Times without a zone
are local time (CEST); `mtime` is Unix seconds. "Lines" counts the last line also when it has no newline; for CSV
files it includes the header. Units: Hz, dB (dBFS for levels), samples, bytes, seconds, kbps.

The manifest below is the output of `python3 scripts/verify/manifest.py` (path, lines, bytes, sha256 of every file
under `corpus/` and `results/` that git tracks); `manifest.py --ignored` lists the ignored ones.

## Contents

1. [Manifest](#1-manifest)
2. [corpus/](#2-corpus)
3. [corpus/evidence/](#3-corpusevidence)
4. [results/: benchmark run](#4-results-benchmark-run)
5. [results/analysis/](#5-resultsanalysis)
6. [results/capture-check/](#6-resultscapture-check)
7. [Other files](#7-other-files)
8. [Not in this repository](#8-not-in-this-repository)

## 1. Manifest

| File | Lines | Bytes | sha256 |
|---|---|---|---|
| `corpus/evidence/capture_library_md5.tsv` | 192 | 15,139 | `10c9c45dcc667a65c1062230c7008c65c5c4ab3f36b4ae1e272443144a8b8f83` |
| `corpus/evidence/capture_lowbits.jsonl` | 28 | 4,199 | `a0adba9b721c754dd19a79b0b26475d044fea000a4fb9ccc833591ca7b9316fa` |
| `corpus/evidence/corrupt.txt` | 54 | 2,900 | `d3640ef34e31b8f3be713b794ea00119639085e0d834cf9e7e0802e963078656` |
| `corpus/evidence/damage_scan_partial.tsv` | 3,579 | 225,287 | `c2f383023ccec665f1f40dc1b9794db48944913aa84cc97d65394df43ab8df63` |
| `corpus/evidence/integrity_check.err` | 0 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `corpus/evidence/integrity_check.tsv` | 276 | 16,299 | `4fbaf27a5f73e272c2d892f5f3078fd24dae26d53f7455459461d628b75c54b4` |
| `corpus/evidence/reencode_results.jsonl` | 4,888 | 2,263,224 | `d469113f0ca6136055537864e937f4ad005226b3f14b1f2cf8ecd866b4a3d855` |
| `corpus/evidence/reencode_results_id3.jsonl` | 32 | 14,543 | `5583d8e90c0866a6bc180aaead84c33adabe01bab2d56ed48a7efb580b8a3c2e` |
| `corpus/evidence/to_check.txt` | 276 | 12,851 | `0652c76a0c064397c4e5a6c4e7525aaab45acdd0addd58fae1e0b2bd0f0ddacc` |
| `corpus/inventory.jsonl` | 5,092 | 1,601,265 | `6208dc5d8fd68f8bc35fc533a8f316b3ee1769dec358172f516c9f341a99b0c0` |
| `corpus/jobs.jsonl` | 2,500 | 1,516,527 | `f925a738608873dd88f19e0aef5a5bb6d50f986ce4ffd82ab21864d2b358025a` |
| `corpus/jobs_ctl48.jsonl` | 34 | 21,172 | `a155be2dff601730cac1ed3d9be580743d59f15afaa86be928fba8febe77ce9d` |
| `corpus/library_tiers.jsonl` | 5,092 | 2,944,142 | `240e2e731297aa1a3c5ba999da10297a63204e063662ac0a16ff1efaef15bf61` |
| `corpus/selection_summary.txt` | 31 | 1,949 | `584500a22bc3a3076aa6316b62a339c9c80524f479ab8b41180bd228f5c8aa27` |
| `corpus/set_a.csv` | 2,501 | 768,302 | `45fa0552271f82191566c314e7a8b9bc178ebb29eaf179c0256aced32251a6f7` |
| `corpus/set_b.csv` | 201 | 58,167 | `438480264db479d84d87f58cb4447b72043780aa40dee01a8df931ece5b2de94` |
| `corpus/set_bait.csv` | 151 | 41,935 | `767e06cd5ce6f9db3ae0ba857ba8b278871291fc19b3a6e1bd5850303ed65754` |
| `corpus/set_ctl48.csv` | 35 | 4,365 | `6e7ba40a5f155fa65d8c40658e84d5274fff99cbb4f8189f6bc717da2c906ae9` |
| `corpus/set_processed.csv` | 109 | 31,685 | `1a060e800c4850dc50bbe27257b086ce97fe7dc0a9ec918fb98af0258f9d10d5` |
| `results/analysis/disagreements.csv` | 398 | 92,732 | `16f202b2eaaef3b308a71161bd14b39940e9b139ae6c66958a7a16939568064e` |
| `results/analysis/originals.csv` | 2,501 | 548,994 | `13954ac44bbfe528d2cacb3d9be27112b13300435e0f1209b8284422f7f1c23b` |
| `results/analysis/reproduction_mismatches.csv` | 1 | 158 | `2a42167f78fd96c8c04252cbe66f5cdf88a0e22ca771b8421cbe0d7ca0bb513e` |
| `results/analysis/summary.md` | 410 | 52,685 | `e04aadb9356efdb58e3ce2eb94b52f8580cc45dff41ba32ce9f6ffb8cfa04d24` |
| `results/analysis/variants.csv` | 4,267 | 749,370 | `c49f35cb1b2af206e8a0fe3f89a68633cc84fafe2524f99c13e4eb1023bda60b` |
| `results/capture-check/align.jsonl` | 10 | 1,648 | `b6841e98fcf1c79459dfe23c40d0db7a39f0d8f80a0aa9c9aba5e5734a459427` |
| `results/capture-check/recs_scan.jsonl` | 10 | 2,939 | `7daddd1341547e8ee8d1721a6a5e636691088884f19cf0e47fa0bb46a96a237a` |
| `results/clipfree.jsonl` | 1,471 | 649,741 | `b1ce9afe1378ab259b47a1c883a35a63654127398f5dc58df4f414a3a5a9b17c` |
| `results/phase1.jsonl` | 12,501 | 8,561,988 | `1a3d32a63a04e5954656bdef9d9dbd0d4bd1550024cad9b715f6e00d315ee583` |
| `results/phase2.jsonl` | 17,115 | 14,120,120 | `5db428f881ade0f32d342c93595755e2e29eb1fca2f776d38dbbfb5e23dddb72` |
| `results/phase3.jsonl` | 307 | 236,221 | `3f707a2d77896389ef085552bbc402b902352eff0158a3c4538dae5c9eb87d29` |

## 2. corpus/

The library inventory, the trust tiers and strata, and the sets drawn from them ([methods.md](methods.md), Corpus).
The corpus files are published in reduced form: the inventory keeps only the fields below, tier reasons are neutral
strings, and vendor strings outside the common encoders are replaced by `other`. `scripts/analyze.py` run on these
files reproduces `results/analysis/` byte for byte, and `scripts/verify/v1_benchmark.py` and `v2_clipfree.py` run
clean on them.

**`inventory.jsonl`** (5,092 lines, one per library FLAC known to Echolot, taken from its database on 2026-10-15).
Read by `scripts/analyze.py`, `scripts/select_ctl48.py` and `scripts/verify/` (YouTube group, reproduction check).

| Field | Meaning |
|---|---|
| `path` | library path |
| `size`, `mtime` | bytes; Unix seconds (at inventory time) |
| `duration`, `kbps` | seconds; average bitrate (both from Echolot's database) |
| `bps`, `rate`, `channels`, `samples` | FLAC header: bits per sample, sample rate (Hz), channels, total samples |
| `md5_set` | STREAMINFO MD5 present (4,539 true) |
| `quality` | Echolot's stored label: `lossless` (5,000) or `fake` (92) |
| `lossy_sourced` | Echolot's estimated lossy source (`~128 kbps`, `~160-192 kbps`, `~256 kbps / V0`, or empty) on 92 files, else null |
| `filed` | `{"ts": ...}`: the time the file was last imported into Echolot (4,639 files), or null (453 files from before Echolot) |
| `tags` | `{"provenance_url": "youtube.com"}` where the file's own tags contained a YouTube URL (121 files, 77 of them in set A), else `{}` |

**`library_tiers.jsonl`** (5,092 lines): every library FLAC with its selection attributes.

| Field | Meaning |
|---|---|
| `path`, `size`, `mtime`, `duration`, `bps`, `rate`, `channels`, `samples`, `kbps`, `md5_set` | as in the inventory |
| `vendor` | FLAC vendor string (`reference libFLAC ...`, `Lavf...`, `Mutagen ...`, `flacvorbis ...`, `flac-codec ...`), `other` (95) or empty (613) |
| `tier` | 1–4 |
| `subtier` | `1` (278), `2_proven` (124), `2_fade` (8), `2_altered` (9), `3` (3,406), `4` (1,267) |
| `reasons` | list of provenance signs and doubts. Tier reasons: "tagged as store/stream file (tags only, not proven): <store>", for tier 2 the sub-tier (`2_proven`, `2_fade`, `2_altered`) with "stream capture (decoded-audio hash match)" and the capture's verdict (e.g. "stream capture verdict info, exact True, faded False"), "no store or stream provenance, at least three corroborating signs", "store/stream hint (<store>) but doubts", "few provenance signs". Signs: "matched the release (Echolot: exact / ISRC / audio identity)", "STREAMINFO MD5 set", "album tags complete", "release ids (MusicBrainz/barcode/catalog no.)", "reference encoder vendor". Doubts: "no import record (imported before Echolot)", "matched by hand", "matched review", "matched probable", "matched close", "close match for its song", "sent back to review once", "re-encoded by ffmpeg, no MD5". Also "stream capture judged lossy-sourced (kept, marked)" and "stream capture without a hash match (judged on its own signs)". `<store>` is a store name or "vendor string of a store client" |
| `strata` | multi-label: `era_pre1990`, `era_1990s`, `era_2000s`, `era_2010s`, `era_2020s`, `era_unknown`, `old_master`, `genre_classical_acoustic`, `genre_electronic`, `genre_hiphop`, `genre_pop`, `genre_rock_metal`, `genre_unknown`, `live`, `vinyl`, `remaster`, `short`, `bits24`, `bits24_fade`, `rate48000` |
| `integrity` | `verified` (5,089) or `failed` (3) |
| `excluded` | reason for exclusion (5 files: 8 channels, samples differ ×2, damaged FLAC, shorter than 20 s) or empty |
| `spectrum_mark` | `lossy_sourced` where Echolot's stored label is lossy (92), else empty |
| `sets` | subset of `A`, `B`, `bait`, `processed` |

**`jobs.jsonl`** (2,500 lines): one job per set-A file, fields as in `library_tiers.jsonl`; `sets` says which
variants phase 2 makes (B: 18 transcodes; processed: 2; bait: 3). Phase 1 runs all 2,500 jobs, phase 2 the 212 with
B, bait or processed. **`jobs_ctl48.jsonl`** (34 lines; `scripts/select_ctl48.py`): the same fields plus
`ctl48_source` (`48k tier 1`: 4, `44.1k bait source`: 30); `sets` is `["ctl48"]`.

**`set_a.csv`** (2,500 rows), **`set_b.csv`** (200), **`set_bait.csv`** (150), **`set_processed.csv`** (108):
`path, size, mtime, tier, subtier, integrity, spectrum_mark, strata` (`;`-separated), `reasons` (` | `-separated),
`bps, rate, duration` (s, 2 decimals). **`set_ctl48.csv`** (34 rows; `select_ctl48.py`): `path, size, mtime, tier,
subtier, rate, bps, source, strata`.

**`selection_summary.txt`** (31 lines): the counts printed by the selection: library, eligible and set sizes,
sub-tiers per set, exclusions, strata (library / A / B / bait / processed), Echolot-marked files per set, maximum
files per artist.

## 3. corpus/evidence/

Integrity and stream-capture evidence read by the selection ([methods.md](methods.md), Corpus).

| File | Producer | Content |
|---|---|---|
| `reencode_results.jsonl` (4,888) | maintenance re-encode pass of 2026-10-13 (not in this repository) | per file: `path` (`tracks/...`), `t_copy`, `t_enc`, `t_low` (s), `size`, `md5` (STREAMINFO; all-zero if unset), `audio_bytes`, `padding`, `bps`, `ch`, `rate`, `samples`; low-bit analysis of 24-bit files `low_class` (`real24`, `zero`, `zero_after_20ms`), `low_nz`, `low_first_s`, `low_last_s`, `low_zero_bits`; decode check `decode_rc`, `decode_err`, `pcm_md5`, `pcm_samples`; result of `flac -8`: `new_size`, `new_md5`, `new_audio_bytes`, `new_padding`, `audio_same` (bool), `audio_check` (`streaminfo`, `pcm`, `streaminfo+pcm`), `enc_error`, `enc_warn` |
| `reencode_results_id3.jsonl` (32) | same pass, files with an ID3v2 tag in front | as above plus `id3v2_stripped` (bytes) |
| `corrupt.txt` (54) | same pass | first line the count (53), then the files whose re-encode failed with a FLAC decode error (`tracks/...`) |
| `damage_scan_partial.tsv` (3,579) | partial damage scan of 2026-10-13 (not in this repository) | `result <TAB> /music/tracks/...`; 3,577 `ok`, 1 `MISSING`, 1 damaged |
| `to_check.txt` (276) | hand selection | files without clean decode evidence; input of `check_integrity.py` |
| `integrity_check.tsv` (276) | `scripts/check_integrity.py`, 2026-10-15 | `result <TAB> size <TAB> path`; 273 `ok`, 2 `samples differ: decoded N, header M`, 1 damaged |
| `integrity_check.err` (0) | stderr of that run | empty |
| `capture_library_md5.tsv` (192) | `scripts/audio_md5.py` | `audio_md5_s32le <TAB> path`: decoded-audio MD5 (`pcm_s32le`, tag-independent) of the library files that came from stream captures; a match with a capture's hash puts a file in tier 2 |
| `capture_lowbits.jsonl` (28) | 2026-10-13 re-encode pass | 24-bit stream-capture files: `path` (`tracks/...`), `frames` (sample frames), `off_frames` (frames with non-zero low 8 bits), `first`, `last` (frame index), `peak` (24-bit sample value); `off_frames == 440` (9 files) marks `bits24_fade`: 24 bit only because of the stream's ~10 ms fade-in |

## 4. results/: benchmark run

**`phase1.jsonl`, `phase2.jsonl`, `phase3.jsonl`** (12,501 / 17,115 / 307 lines). Producer: `scripts/run.py --phase
N`, spectrum through `scripts/spectrum_worker.py` in the Echolot image (commit e9f0bf9). One JSON line per (job,
variant, detector):

| Field | Meaning |
|---|---|
| `job` | `p1:` / `p2:` / `p3:` + library path; `-` on `run_start` |
| `phase` | 1, 2 or 3 |
| `variant` | `original`; an encoding (`mp3_128` … `oggenc_q6`); `bait_32k`, `bait_38k`, `bait_40k`; `mp3_320_gain`, `mp3_320_up48`; `ctl48_40k`, `ctl48_opus160`; `-` on `run_start` and `job_done` |
| `detector` | `run_start`, `meta`, `spectrum`, `lossprint`, `flaccheck`, `job_done` (`job_error` possible; none occurred) |
| `ok`, `error` | line valid; error text (a rejected variant has `meta` with `ok = false` and no detector lines) |
| `seconds` | `job_done`: wall time of the job (s) |
| `ts` | `run_start`: start time |
| `out` | detector output, below |

`out` by detector:
- `run_start`: `tools` (version strings of host ffmpeg, the Echolot image's ffmpeg, the Echolot image and commit,
  lossprint, flaccheck, lame, opusenc, oggenc, Debian packages), `args` (`phase`, `workers`, `lp_threads`, `only`,
  `out` (absolute output path), `limit`), `todo`.
- `meta` of an original: `sha256` (file), `audio_md5_s32le` (decoded audio), `peak_db`, `rms_db` (dBFS),
  `flat_factor`, `peak_count` (ffmpeg astats), `ffmpeg_rc`, `ffmpeg_err`.
- `meta` of a variant: `encode` (encoder and options), `encoded_bytes` (absent for bait and `ctl48_40k`), `decoded`
  (`codec`, `rate`, `channels`, `samples`, `bits`, `sample_fmt`), `expected_samples`, `delta_samples`, `flac_t`
  (`flac -t` passed).
- `spectrum`: `spectrum` is Echolot's `spectrum()` dict unchanged (`sr` Hz, `cutoff_hz` Hz, `drop_db` dB, `verdict`
  `ok`/`lossy`, optional `flicker` (0–1), `source` (estimated lossy source), `reason`); `flicker_at_edge`
  (`_flicker()` at the detected edge for every drop ≥ 25 dB, else null); `edge_check` (a widened second call found
  the same edge, else null); `seconds`; worker `id`, `ok`, `error`.
- `lossprint`: `transcode_probability` (0–1, the score used), `verdict` (lossprint's own field: `transcode` on
  all lines but one, `clean` on one, regardless of p; not used), `encoder` (family: `mp3`, `ffmpeg_aac`, `vorbis`,
  `opus`, `musepack`, `wma`; null on one line), `bitrate_kbps` (estimate), `path` (as passed: the absolute library path in phase 1, the variant in the
  run's scratch directory in phases 2 and 3).
- `flaccheck`: `transcode_verdict` (`GENUINE`, `TRANSCODED`, `SUSPICIOUS`, `INCONCLUSIVE`), `hires_verdict`,
  `confidence` (0–1), `codec_guess`, `est_source_bitrate_kbps`, `spectral_info_score`, `mode` (`balanced`),
  `duration_secs`, `sample_rate`, `channels`, `bits_per_sample`, `evidence` (list of `detector`, `signal`, `value`,
  `weight`, `note`), `path` (absolute path of the per-job symlink in the run's scratch directory).

Counts: phase 1: 2,500 jobs × (`meta`, `spectrum`, `lossprint`, `flaccheck`, `job_done`) + `run_start`. Phase 2:
212 jobs, 4,266 `meta` lines, 4,212 scored variants, 54 rejected. Phase 3: 34 jobs × 2 variants.

**`clipfree.jsonl`** (1,471 lines). Producer: `scripts/clipfree.py` with `scripts/clipfree_worker.py` (in the
Echolot image). Fields: `path`; `variant` (`original` or one of `mp3_192`, `mp3_320`, `mp3_v2`, `aac_128`,
`lame_320`, `vorbis_q3`); worker `id`, `ok`, `error`; `echolot` (Echolot's `spectrum()` dict); `asis` and
`clipfree` (`cutoff_hz` Hz, `drop_db` dB, `verdict`, optional `flicker`, `frames` used of the 480 FFT frames,
`clipped_frames`; as Echolot measures, and without the clipped frames; `clipfree.verdict` is `unknown` with
`reason` "too few frames" on 42 items, without cutoff and drop); `same_as_echolot` (`asis` equals `spectrum()`).

## 5. results/analysis/

Producer: `scripts/analyze.py` (from `results/phase{1,2,3}.jsonl`, `results/clipfree.jsonl`, `corpus/jobs.jsonl`,
`corpus/jobs_ctl48.jsonl`, `corpus/inventory.jsonl`). Flags are `True` / `False`, empty where the detector gave no
output.

| File | Content |
|---|---|
| `summary.md` | all tables with Wilson 95% intervals: completeness, reproduction check, false positives by group and stratum, bait, recall per encoding and by source format, 48 kHz control, combined rules with the 41 originals flagged by two detectors, spectrum threshold grid, held-out halves, clip-free experiment, lossprint threshold sweep, flicker quantiles. Verified cell by cell ([results.md](results.md), Verification) |
| `originals.csv` (2,500 rows) | per original: `path, variant, subtier, spectrum_mark, strata, peak_db, rms_db, flat_factor`; flags `spectrum, lossprint, flaccheck`; raw values `sp_verdict, sp_cutoff` (Hz), `sp_drop` (dB), `sp_flicker, sp_flicker_at_edge, sp_source, lp_p, lp_encoder, lp_kbps, fc_verdict, fc_conf, fc_codec, fc_cutoff` (Hz), `fc_brick_wall` |
| `variants.csv` (4,266 rows) | per phase-2 variant line (rejected variants included with empty flags): `path, variant, subtier`, flags and raw values as above (no loudness, mark or strata columns) |
| `disagreements.csv` (397 rows) | the originals on which the three detectors' flags differ; columns as `originals.csv`. Input of `scripts/spectrograms.py` |
| `reproduction_mismatches.csv` (header only) | originals whose harness spectrum verdict differs from Echolot's stored label: none. Columns `path, stored`, then the raw values as above |

## 6. results/capture-check/

The ten songs captured from Spotify Lossless, compared with their library copies ([results.md](results.md),
Stream-capture ground truth).

| File | Producer | Content |
|---|---|---|
| `align.jsonl` (10) | `scripts/align_diff.py` on the list of (capture, library copy) pairs | `song` (artist – title), `lag` (samples, library copy against capture), `overlap_s` (s), `bits` (the coarser bit depth of the two), `identical` (share of identical samples at that depth, 0–1), `residual_db` (residual RMS relative to the capture, dB; −300 means none), `gain` (least-squares gain of the library copy), `residual_db_gain` (residual after that gain, dB) |
| `recs_scan.jsonl` (10) | Echolot's spectrum check and lossprint on the 10 captures, in the Echolot image (scan script not in this repository) | `path` (file name of the capture), `spectrum` (Echolot's `spectrum()` dict), `lossprint` (`p`, `encoder`, `kbps`), `spectrum_fake` (spectrum verdict lossy), `combined_fake` (Echolot's combined verdict at the time: spectrum lossy or p ≥ 0.5), `source` (estimated lossy source, empty if none), `s_spec`, `s_lp` (seconds per check) |

## 7. Other files

| Path | What |
|---|---|
| `README.md` | summary of the study and its results |
| `TOOLS.md` | setup, invocation and output formats of lossprint and flaccheck |
| `docs/methods.md`, `docs/results.md`, `docs/reproducing.md`, `docs/data.md` | methods, results, reproduction, this dictionary |
| `report/` | groundwork for a written report |
| `scripts/run.py`, `spectrum_worker.py` | the benchmark run (phases 1–3) |
| `scripts/chain.sh`, `after_chain.sh`, `memguard.sh` | run sequencing: reproduction gate before phase 2, then phase 3 and the clip-free experiment; graceful stop on low memory |
| `scripts/select_ctl48.py` | selection of the 48 kHz control |
| `scripts/clipfree.py`, `clipfree_worker.py` | clip-free experiment |
| `scripts/analyze.py` | analysis, writes `results/analysis/` |
| `scripts/spectrograms.py` | spectrogram PNGs of the disagreement list |
| `scripts/check_integrity.py`, `audio_md5.py` | integrity check and decoded-audio MD5 of library files |
| `scripts/align_diff.py` | sample-aligned comparison of a capture and a library copy |
| `scripts/verify/` | independent re-computation (`v1_benchmark.py`, `v2_clipfree.py`, helpers `common.py`, `summary_tables.py`) and `manifest.py` |

## 8. Not in this repository

| What | Why | How to regenerate or obtain |
|---|---|---|
| Audio: the library FLACs, the transcodes and bait (deleted per job during the run), the 10 stream captures | copyright | the transcodes and bait from the audio with `scripts/run.py` |
| `results/analysis/spectrograms/`: 397 PNGs of the disagreement list and `index.csv` (`png, path, error`) | renderings of copyrighted recordings; 559 MB | `python3 scripts/spectrograms.py --workers 1` (needs the audio) |
| `tools/`, `bin/`: lossprint and flaccheck builds | third-party binaries | versions and build steps in [TOOLS.md](TOOLS.md) and [methods.md](methods.md) |
| `scratch/` | run scratch | regenerated by the scripts |
| The inventory export from Echolot's database, the corpus selection script, the capture-comparison input, the maintenance passes behind `corpus/evidence/` | tied to the local installation (database, absolute paths) | the rules they implement are in [methods.md](methods.md) |
