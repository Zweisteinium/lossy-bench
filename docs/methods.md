# Methods

This document describes how the benchmark was designed and measured (October 2026), in enough detail to repeat it.
The public scripts in `scripts/` are the ground truth for the run and the analysis; constants and commands below are
copied from them and cited as `file:line` (a bare `:line` refers to the file named last before it in the same
paragraph, list or table). Echolot code is cited at the commit that ran, as `audio.py@e9f0bf9:line`
(`src/echolot/library/audio.py` in the Echolot repository). The corpus selection is described in full in prose and
tables (section 3); its script is not part of this repository. Results are in `docs/results.md`; step-by-step
reproduction is in `docs/reproducing.md`.

The study only measured. No library file was changed; the library manager's background jobs were paused during the
runs so that no file was renamed or replaced.

## Contents

1. [Research questions](#1-research-questions)
2. [Detectors under test](#2-detectors-under-test)
3. [Corpus](#3-corpus)
4. [Labels and their limitations](#4-labels-and-their-limitations)
5. [Transcode generation](#5-transcode-generation)
6. [Bait, processed and 48 kHz control](#6-bait-processed-and-48-khz-control)
7. [Run harness and per-job integrity guards](#7-run-harness-and-per-job-integrity-guards)
8. [Scoring and statistics](#8-scoring-and-statistics)
9. [Clip-free experiment](#9-clip-free-experiment)
10. [Stream-capture ground-truth check](#10-stream-capture-ground-truth-check)
11. [Decision rule derived from the data](#11-decision-rule-derived-from-the-data)
12. [Computing environment](#12-computing-environment)
13. [Design facts that affect interpretation](#13-design-facts-that-affect-interpretation)

## 1. Research questions

The benchmark asks how well three detectors tell genuine lossless FLACs from FLACs decoded from a lossy file
("transcodes", "fakes"):

| # | Question | Data |
|---|---|---|
| RQ0 | Harness validity: does the harness reproduce the stored verdicts of the library manager's spectrum check exactly? | phase 1, files imported since the current check |
| RQ1 | How often does each detector flag presumed-genuine library FLACs, overall and by provenance tier, content stratum, format and measured loudness/clipping? (specificity) | set A originals |
| RQ2 | What share of synthetic transcodes does each detector flag, per codec, bitrate or quality, encoder implementation (ffmpeg vs standalone encoder) and source format? (sensitivity) | set B variants |
| RQ3 | Are genuine files behind a steep resampler edge flagged (bait)? Are transcodes still caught after a gain change or upsampling to 48 kHz (processed)? | bait, processed |
| RQ4 | At 48 kHz, does lossprint react to Opus coding or to any steep edge near 20 kHz? | 48 kHz control (phase 3) |
| RQ5 | Can the spectrum check be improved by other thresholds, or by leaving clipped frames out of its measurement, without new false positives? | threshold replay, held-out halves, clip-free experiment |
| RQ6 | What do combinations of the detectors achieve? | all of the above |
| RQ7 | For nine disputed lossprint flags and one control: is the library copy the same audio as the official lossless stream (the master itself is lossy) or a lossy copy of it? | 10 bit-exact stream captures, `align_diff.py` |
| RQ8 | Which combined decision rule do RQ1-RQ7 support? | section 11 |

## 2. Detectors under test

| Detector | Version | Type | Where it ran |
|---|---|---|---|
| Spectrum check of Echolot, a self-hosted library manager: `spectrum()` and `_flicker()` | Echolot commit e9f0bf9, image `sha256:eff56d10aed8…` | hand-written DSP rule | throwaway containers of that image (`run.py:103-112`) |
| lossprint | 1.1.0 (crates.io, model 1.0 embedded) | CNN on spectrograms (ONNX, `tract` runtime, CPU) | host binary `bin/lossprint` |
| flaccheck | 0.1.2 (tag v0.1.2, commit c05e68526973efce9dc32423b2e1dd9cc5274857) | DSP heuristics, no ML in this build | host binary `bin/flaccheck` |

### 2.1 Echolot spectrum check

Code: `audio.py@e9f0bf9:206-296`.

Constants (`audio.py@e9f0bf9:208-211`):

| Constant | Value | Meaning (code comment) |
|---|---|---|
| `DROP_DB` | 30.0 | dB fall within about 1 kHz that counts as an encoder low-pass |
| `MAX_LOSSY_CUT` | 20400 | Hz; edges above this are ordinary anti-alias filters of genuine masters |
| `TRACES_FROM` | 19000 | Hz; an edge from here up may be a mastering filter: lossy only with the encoder's traces |
| `FLICKER` | 0.03 | traces: share of bins below the edge switching between hole and content from frame to frame |

**`spectrum(path)`** (`audio.py@e9f0bf9:214-268`):

1. `ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate:format=duration -of json PATH` (timeout
   60 s). If the sample rate is 0 or the container duration is below 20 s: verdict `unknown`, reason "too short or
   unreadable" (`:225-231`).
2. Three excerpts at 30 %, 50 % and 70 % of the duration, 15 s each, decoded by ffmpeg to mono float32 at the
   native rate (`:235-237`):
   `ffmpeg -v error -ss {dur*pos:.1f} -t 15 -i PATH -ac 1 -f f32le -` (input seek; the downmix is ffmpeg's).
3. STFT: `nfft = 8192`, `hop = 4096`, Hann window (`np.hanning(8192)` as float32); frames at
   `i in range(0, len(x) - nfft, hop)` per excerpt; the power `|rfft|²` of every frame of all three excerpts is summed
   (`:232-242`). Fewer than 20 frames in total: `unknown`, "no audio decoded" (`:243-244`).
4. Mean power spectrum in dB: `10·log10(acc/frames + 1e-20)`; bin spacing `sr/8192` (5.38 Hz at 44.1 kHz) (`:245-246`).
5. Loudness gate: mean dB over bins with 1000 < f < 8000 Hz below −90: `unknown`, "too quiet" (`:247-248`).
6. Edge search (`:250-257`): for every candidate `cut` in `range(12000, int(min(sr/2 − 1600, 23000)), 100)`,
   `drop = band(cut−1500, cut−300) − band(cut+300, cut+1500)`, where `band(lo, hi)` is the mean dB over bins with
   `lo ≤ f < hi`. The first candidate with the largest drop wins (strict `>`, starting from cut 0 / drop 0.0).
   Candidate range: 12,000-20,400 Hz at 44.1 kHz, 12,000-22,300 Hz at 48 kHz.
7. Result `{"sr", "cutoff_hz", "drop_db": round(drop, 1), "verdict": "ok"}` (`:258`).
8. Decision (`:259-267`): if `drop ≥ DROP_DB` and `cut < MAX_LOSSY_CUT`:
   - if `cut ≥ TRACES_FROM`, `flicker = _flicker(excerpts, sr, cut)` (stored in the result), else no flicker;
   - if a flicker was computed and `flicker ≤ FLICKER`: stays `ok`, reason "a steep edge without an encoder's
     traces (a mastering filter)";
   - otherwise `lossy`, including the case where `_flicker()` returns `None` (too few loud frames). Source label by
     the edge: `< 16800` "~128 kbps", `< 19300` "~160-192 kbps", else "~256 kbps / V0".
   The comparison uses the unrounded drop; the stored `drop_db` is rounded to 0.1 dB.

**`_flicker(pieces, sr, cut)`** (`audio.py@e9f0bf9:271-296`), on the same three mono excerpts:

| Step | Value |
|---|---|
| FFT | `nfft = 1024`, Hann, hop 512 (`sliding_window_view(x, 1024)[::512]`) |
| Band below the edge | bins with `cut − 2500 ≤ f < cut − 300` (2.2 kHz) |
| Reference band | 1000 ≤ f < 8000 Hz |
| Rounding floor | `10·log10(1024/4 · 1e-10)` = −75.9 dB per bin ("16-bit rounding noise per bin, about") |
| Loud frame | reference-band dB > (90th percentile of that excerpt's reference-band dB − 15) **and** mean band power in dB > floor + 30 |
| Hole | a bin whose power is below the frame's mean band power × 10^−2.5 (25 dB under it) |
| Flips | hole/content changes per bin between consecutive loud frames (consecutive in the loud subsequence, not necessarily adjacent in time) |
| Skipped excerpt | shorter than 4 × 1024 samples, or fewer than 2 loud frames |
| Result | `round(flips / (frames · n_bins), 4)` with `frames = Σ(loud − 1)`; `None` if `frames < 30` |

**Harness worker** (`scripts/spectrum_worker.py`): calls `audio.spectrum()` unchanged (`:40`). If the stored drop is
≥ 25 dB (`:42`), a second call runs with three module constants widened, `DROP_DB 25.0`, `TRACES_FROM 0`,
`MAX_LOSSY_CUT 10**9` (`:21`), and restores them afterwards (`:24-32`); only its `flicker` is kept, as
`flicker_at_edge`. The edge search does not use these constants, so the second call finds the same edge;
`edge_check` records that cutoff and drop are identical (`:45`). A line is `ok` when the verdict is `ok`, `lossy` or
`unknown` (`:46`). This gives the flicker at every edge with a drop of at least 25 dB, which the threshold replay
needs ([8.5](#85-spectrum-threshold-replay)).

### 2.2 lossprint 1.1.0

A convolutional network on spectrograms at the file's native rate, CPU-only (`TOOLS.md`, section "lossprint
1.1.0"): FLAC/WAV/AIFF input only; mono or stereo; at least 2 s; up to 14.5 s scored as one window, longer tracks on
6 evenly spaced 14.5 s windows from the middle 92 % of the file; `transcode_probability` is the mean of the
per-window outputs; it also reports an encoder family (`mp3`, `ffmpeg_aac` for any AAC encoder, `vorbis`, `opus`,
`wma`, `mp2`, `musepack`) and a bitrate estimate.

Invocation (`run.py:345`), once per job with all of the job's files as explicit arguments:

```
nice -n 19 ionice -c3 bin/lossprint -j <lp_threads> -t 0 -o jsonl -- FILE...
```

- `-t 0` makes lossprint report its encoder and bitrate guesses for every file; its own `verdict` field is then
  always "transcode" and is ignored. The analysis applies its own threshold to `transcode_probability`
  (default 0.5, swept; [8.4](#84-lossprint-threshold-sweep)).
- Output lines are mapped back by the `path` field; a file without an output line gets an error line with the tail
  of stderr (`run.py:346-356`). Exit codes are not used (lossprint exits 1 if any file fails).
- Files are passed explicitly, never as a directory: lossprint does not follow symlinks inside a directory, and one
  missing path aborts the batch.

### 2.3 flaccheck 0.1.2

Hand-tuned DSP heuristics in four tiers (spectral cutoff/brick wall/codec signatures; quantization; artifacts;
fake hi-res), fused with thresholds compiled into `flaccheck-core/src/calibration.rs`; built without the `ml`
feature. Spectral analysis uses the left channel only; in `balanced` mode over 3 × 10 s windows at start, middle and
end; above 48 kHz its lossy-codec gate is off (`TOOLS.md`, section "flaccheck 0.1.2").

Invocation (`run.py:358-364`), once per job on a directory of symlinks named `<variant>.flac` (flaccheck follows
them):

```
nice -n 19 ionice -c3 bin/flaccheck scan <job>/fc --mode balanced --format json --explain --quiet \
    --color never --workers <lp_threads> -o <job>/flaccheck.json
```

- Results, `skipped` and `errors` are mapped back by file stem (= variant name); a variant missing from all three
  gets an error line (`run.py:365-379`). The exit code is not used (flaccheck exits 0 even when files fail).
- Output mapping in the analysis (`analyze.py:85-86`): flag = `transcode_verdict == "TRANSCODED"`; a second,
  wider reading `flaccheck_wide` also counts `SUSPICIOUS`. `GENUINE` and `INCONCLUSIVE` count as not flagged and stay
  in the denominator. `confidence` is not used (it is confidence in the verdict, not P(lossy)).

## 3. Corpus

### 3.1 Inventory

The inventory is the library database's view of the library, not a file-system walk: one record per FLAC file the
library manager's database lists (5,092), read with the database opened read-only. Per file:

| Group | Fields |
|---|---|
| From the database | path (relative to the library's track directory), size, mtime, duration and kbps as stored; the stored spectrum verdict (`quality`, and the `lossy_sourced` mark) |
| From the FLAC header (mutagen) | bits per sample, sample rate, channels, total samples, whether the STREAMINFO MD5 is set, vendor string, picture count |
| Tags (lower-cased names, values truncated to 300 characters) | those used by the rules below (`artist`, `albumartist`, `album`, `title`, `date`, `year`, `originaldate`, `originalyear`, `genre`, `encoder`, `encoded_by`, `encodedby`, `comment`, `description`, `copyright`, `media`, `tracknumber`, `tracktotal`, `barcode`, `catalognumber`, `musicbrainz_albumid`, `url`, `purl`, `www`) plus descriptive tags no rule uses |
| Import record | the file's last import event: time, how the file was matched to the release (`exact`, `by hand`, `review`, `probable`, `close`), the audio-identity method, the file name at import |
| Songs and history | the songs linked to the file (release date, close-match flag); the set of event actions in the file's history |

Result: 5,092 FLACs, 4,943 at 44.1 kHz and 149 at 48 kHz, 5,091 stereo and one 8-channel file.

**Published form.** `corpus/inventory.jsonl` is reduced to what the public analysis reads: `path`, `size`, `mtime`,
`duration`, `kbps`, `bps`, `rate`, `channels`, `samples`, `md5_set`, `quality`, `lossy_sourced`, `filed.ts` (the
import time; absent for the 453 files without an import record) and `tags`, which holds only
`provenance_url: "youtube.com"` for the 121 files with a YouTube URL in their own tags and is empty otherwise. The
per-file tiers, reasons, strata, integrity results and set memberships that the selection derived from the full
inventory are published in `corpus/library_tiers.jsonl`, `corpus/jobs.jsonl` and `corpus/set_*.csv`; their reason
strings are neutral descriptions of the rule that applied ([3.3](#33-provenance-tiers)).

### 3.2 Integrity evidence

A file enters the sets only with evidence that its audio decodes completely and correctly. Sources, in
`corpus/evidence/`:

| Source | File | Used as |
|---|---|---|
| Re-encode pass over the whole library (a maintenance pass before the study): every library FLAC decoded and re-encoded with `flac -8`, decoded audio compared by MD5 | `reencode_results.jsonl` (4,888 lines), `reencode_results_id3.jsonl` (32 ID3v2-prefixed files); `corrupt.txt` (the 53 files whose re-encode failed with a FLAC decode error) | evidence: a file counts as clean if `audio_same` is true, `enc_error` and `error` are empty, **and** its size at selection equals its size in the pass |
| Partial damage scan from the same maintenance work | `damage_scan_partial.tsv` (3,579 lines) | only to pick files for a re-check (below); not evidence by itself |
| Integrity check for this study | `integrity_check.tsv` (276 lines), input `to_check.txt` | evidence, overriding the re-encode pass: `ok` adds the file, any other result removes it and marks it failed at that size |

The 276 files checked (`to_check.txt`) were every inventory file without a clean re-encode result at its current
size, plus every file the partial damage scan reported as anything but `ok` or `MISSING`.

`scripts/check_integrity.py` (runs in the Echolot image, which has Echolot's `audio` module, ffmpeg and mutagen; the
paths come on stdin):

1. mutagen must read the header (`check_integrity.py:23-26`);
2. Echolot's `audio.damage()` (`check_integrity.py:27-29`, `audio.py@e9f0bf9:123-152`): a full decode of only the
   FLAC stream bytes (past a leading ID3v2 tag, before a trailing ID3v1/APE tag; `_stream_bytes`,
   `audio.py@e9f0bf9:103-120`) with
   `ffmpeg -nostats -loglevel level+info -err_detect crccheck+bitstream+buffer -i subfile,,start,S,end,E,,:PATH -map 0:a:0 -af volumedetect -f null -`;
   a CRC error, or any decoding error together with missing samples, is "damaged"; more than `SHORT = 0.5` s missing
   is "cut-off";
3. a second decode of the stream bytes without `-err_detect` (`check_integrity.py:31-32`): decoded samples
   (volumedetect `n_samples` / channels) must equal the header's total samples **exactly** (`:34-37`), and any
   `[error]` line fails the file as "trailing data after the last frame" (`:38-39`).

Result: 273 `ok`, 2 "samples differ", 1 "damaged FLAC (18 decoding errors: invalid sync code)". In
`corpus/library_tiers.jsonl`: 5,089 verified, 3 failed, 0 unverified.

### 3.3 Provenance tiers

Tiers use provenance and integrity only: the file's own tags, its vendor string, its import record and the record of
the stream captures. A detector's output is never used to select or drop a file. The library manager's stored
spectrum verdict (`quality == "fake"` or a `lossy_sourced` mark) is carried as `spectrum_mark = "lossy_sourced"` and
those files are reported apart in the analysis ([4](#4-labels-and-their-limitations)).

| Tier | Name | Meaning |
|---|---|---|
| 1 | store-tagged | the file's own tags name a store or streaming service, or a vendor string of a store client; no doubt |
| 2 | stream capture, hash-proven | a bit-exact capture of the official lossless stream, matched to the library file by decoded-audio MD5; sub-tiers `2_proven`, `2_fade`, `2_altered` ([3.4](#34-tier-2-stream-capture-hash-match)) |
| 3 | corroborated | no store or stream provenance, at least three corroborating signs and no doubt; also store-tagged files with a doubt (rule 4 below) |
| 4 | doubtful | everything else; not in the sets |

**Store hits.** Every match of the regex (applied to lower-cased tag values)

```
qobuz|tidal|deezer|bandcamp|beatport|amazon|apple music|itunes|7digital|junodownload
```

in the tags `url`, `purl`, `www`, `comment`, `description`, `encoder`, `encoded_by`, `encodedby`, `copyright`; plus a
FLAC vendor string that matches (case-insensitive) one of six store-client names.

**Corroborating signs:**
- matched to the release at import by exact match, by ISRC tag or by the audio of the release (audio identity);
- STREAMINFO MD5 set;
- complete album tags: `album`, `tracknumber` and `tracktotal` all present;
- release ids: `musicbrainz_albumid`, `barcode` or `catalognumber`;
- reference encoder vendor: `reference libflac|cuetools|flac \d` in the lower-cased vendor string plus `encoder` tag.

**Doubts:**
- no import record (the file predates the import log);
- matched at import only `by hand`, after `review`, as `probable` or as `close`;
- any of the file's songs is a close match;
- `recheck` in the event history (sent back to review once);
- no STREAMINFO MD5 and `lavf` in the vendor string (re-encoded by ffmpeg).

**Rules, in order:**

| Order | Condition | Result |
|---|---|---|
| 1 | decoded-audio MD5 equals that of a stream capture ([3.4](#34-tier-2-stream-capture-hash-match)) | tier 2; `2_proven` if the capture is bit-exact, has the capture tool's verdict `info` and is not `faded`; else `2_fade` if `faded`; else `2_altered` |
| 2 | file imported from the capture tool without a hash match | the doubt "matched by hand" is dropped (every capture import is matched by hand) and "stream capture without a hash match" is **added** as a corroborating sign; continue with rule 3 |
| 3 | store hit and no doubt | tier 1 |
| 4 | store hit with a doubt | tier 3 |
| 5 | at least 3 corroborating signs and no doubt | tier 3 |
| 6 | anything else | tier 4 |

Rule 1 takes precedence over everything (a hash-matched file is tier 2 even with store tags or doubts). The
sub-tier of a tier-2 file is its first reason; for the other tiers it is the tier number.

Reason strings in the published files and the rule they record:

| Reason (first) | Rule | Files |
|---|---|---|
| `tagged as store/stream file (tags only, not proven): <names>` | 3 | 278 |
| `2_proven` / `2_fade` / `2_altered`, followed by `stream capture (decoded-audio hash match)` and the capture's verdict, exactness and fade flags | 1 | 124 / 8 / 9 |
| `store/stream hint (<names>) but doubts` | 4 | 39 |
| `no store or stream provenance, at least three corroborating signs` | 5 | 3,367 |
| a doubt or a sign, or `few provenance signs` | 6 | 1,267 |

`<names>` lists the store names found; a vendor-string hit appears as a fixed label instead of a name. Further
reasons list each sign and doubt; `stream capture judged lossy-sourced (kept, marked)` marks the 7 hash-matched
captures that the capture tool's own checks judged lossy; `stream capture without a hash match (judged on its own
signs)` marks the 51 capture imports of rule 2.

Library counts (`corpus/selection_summary.txt:2`): tier 1 278, 2_proven 124, 2_fade 8, 2_altered 9, tier 3 3,406,
tier 4 1,267.

### 3.4 Tier 2: stream-capture hash match

Stream captures are captures of Spotify's lossless stream made with a capture tool that keeps a record per capture
(174 captures): the decoded-audio MD5, whether the capture is bit-exact, whether its start was faded (`faded`), the
tool's verdict (`info` or `altered`) and a lossy flag from the tool's own checks. The 192 library files imported
from the capture tool (identified by their import source or the tool's `encoder` tag) were hashed with
`scripts/audio_md5.py`:

```
ffmpeg -nostdin -v error -i FILE -map 0:a -c:a pcm_s32le -f md5 -        (audio_md5.py:13)
```

Output: `corpus/evidence/capture_library_md5.tsv` (`md5 <TAB> path`). A library file whose hash equals a capture's
hash is tier 2; this is the only proof that a file is that capture. A capture the tool judged lossy stays in, marked
in the reasons.

`bits24_fade`: the files in `corpus/evidence/capture_lowbits.jsonl` (28 24-bit capture imports, from the low-bit
analysis of the re-encode pass) whose low 8 bits are non-zero in exactly `off_frames == 440` sample frames: 24-bit
only because of the stream's 10 ms fade-in (440 frames = 9.98 ms at 44.1 kHz), 16-bit audio after it.

### 3.5 Strata

Multi-label, from tags, the header and the stored duration:

| Stratum | Rule |
|---|---|
| `era_pre1990`, `era_1990s` … `era_2020s`, `era_unknown` | year from the first of `originaldate`, `originalyear`, `date`, `year` that starts with 4 digits and lies in 1901-2099, else the first linked song's release date |
| `old_master` | year < 2000 |
| `genre_<group>` | first group whose regex matches the lower-cased `genre` tag, in the order below; else `genre_unknown` |
| `live` | `\blive\b` in title, album or the file name at import |
| `vinyl` | `vinyl\|\blp\b rip\|\bvinyl\b` in those plus `media` and `comment` |
| `remaster` | "remaster" in title, album or the file name at import |
| `short` | stored duration < 120 s |
| `bits24` / `bits24_fade` | bits per sample > 16 (`bits24_fade` if in the fade list of [3.4](#34-tier-2-stream-capture-hash-match)) |
| `rate48000` | sample rate ≠ 44100 (only 48000 occurs) |
| `mono` | one channel (none occur) |

Genre regexes (Python `re.search`, in this order):

```
classical_acoustic  classical|baroque|opera|orchestra|symphon|chamber|piano|acoustic|folk|singer-songwriter|jazz|
                    ambient|soundtrack|score|chanson|neoclassical|instrumental|lo-fi|lofi|blues|country
electronic          dance|electro|techno|trance|house|edm|hardstyle|hard dance|psy|drum and bass|dnb|dubstep|
                    bass|hardcore|gabber|synth|electronic|club|rave|eurodance|hands up|uk garage|breakbeat
hiphop              hip hop|hip-hop|rap|trap|drill|grime
rock_metal          rock|metal|punk|grunge|emo
pop                 pop|r&b|soul|schlager|disco|funk
```

(Each regex is one line; it is wrapped here.) The groups are broader than their names: `classical_acoustic` also
matches blues, country, chanson, instrumental, singer-songwriter, lo-fi; `electronic` matches "bass", "synth",
"club" etc. No stratum is derived from the FLAC bitrate: a FLAC made from a lossy file compresses better, and
selecting by bitrate would tilt the sets. Loudness and clipping are measured in the run and used only as analysis
groups ([8.2](#82-false-positives)).

### 3.6 Exclusions

A file is not eligible if its integrity check failed (at its current size), its header is unreadable, it has more
than 2 channels, its rate is neither 44,100 nor 48,000 Hz, or its stored duration is below 20 s (too short for the
detectors). Result (`corpus/selection_summary.txt:1`, `:7`): 5 excluded, 5,087 eligible.

| File | Reason (as recorded) |
|---|---|
| Billie Eilish – bad guy | 8 channels |
| Discobitch – C'est beau la bourgeoisie (Radio Edit) | samples differ: decoded 9265152, header 9269203 |
| Simon & Garfunkel – The Sound of Silence | samples differ: decoded 8100864, header 8101464 |
| Funk Tribu – Keep Up | damaged FLAC (18 decoding errors: invalid sync code) |
| Lorenz Maierhofer – Have a Nice Day | shorter than 20 s |

Files without evidence either way (`unverified`) are not excluded by the rules; there were none.

### 3.7 Deterministic selection

Order key: `stable(path) = sha256(path.encode("utf-8")).hexdigest()`. Artist key: the `albumartist` tag (else
`artist`), lower-cased, runs of non-word characters (`\W+`) replaced by one space, stripped; album key: the pair
(artist key, `album` tag treated the same way). Files without such tags share the empty key.

```
pick(rows, target, caps, rare_first, min_per_stratum = 0):
    order = rows sorted by (tier, stable(path))        # tier 1 first; the tier-2 sub-tiers share tier 2
    take(r): refuse if r is already taken, or its artist already has caps.artist files, or its album
             already has caps.album files; else take it and count it for its artist and album
    for s in rare_first:                               # stratum pass, ignores target
        n = 0
        for r in order:
            if s in strata(r) and (min_per_stratum == 0 or n < min_per_stratum) and take(r): n += 1
    for r in order:                                    # fill pass
        if taken >= target: stop
        take(r)
```

The stratum pass does not check the target, so a set can exceed it. Stratum lists: rare = `genre_classical_acoustic,
live, vinyl, old_master, era_pre1990, short, mono, rate48000, bits24, bits24_fade, remaster`; common =
`genre_electronic, genre_hiphop, genre_rock_metal, genre_pop, genre_unknown, era_1990s, era_2000s, era_2010s,
era_2020s`.

| Set | Pool | Target | Caps (artist / album) | Stratum pass | Size |
|---|---|---|---|---|---|
| A, presumed genuine (negatives) | eligible, tiers 1-3 (tier 4 only if A stays below target, which did not happen) | 2,500 | 8 / 4 | rare, `min_per_stratum` 0 (all of them) | 2,500 |
| B, to transcode (positives) | A, tiers 1-3 | 200 | 3 / 2 | rare + common, 8 each | 200 |
| bait (negatives) | A, tier 1 or `2_proven`, 44.1 kHz | 150 | 3 / 2 | rare + common, 10 each | 150 |
| processed (positives) | B, 44.1 kHz | 100 | 3 / 2 | rare + common, 6 each | 108 |

B is not restricted to 44.1 kHz; because `rate48000` is a rare stratum with a minimum of 8, B holds 11 sources at
48 kHz (8 × 24/48, 3 × 16/48) and 189 at 44.1 kHz (154 × 16-bit, 35 × 24-bit). Those 11 are kept out of every pooled
recall number ([8.3](#83-recall)). Processed has 108 members because its stratum pass ignores the target of 100.

Composition (`corpus/selection_summary.txt`, `corpus/jobs.jsonl`, `corpus/jobs_ctl48.jsonl`):

| Sub-tier | Library | A | B | Bait | Processed | 48 kHz control |
|---|---|---|---|---|---|---|
| 1 | 278 | 270 | 148 | 140 | 79 | 33 |
| 2_proven | 124 | 124 | 4 | 10 | 2 | 1 |
| 2_fade | 8 | 8 | 0 | 0 | 0 | 0 |
| 2_altered | 9 | 9 | 8 | 0 | 6 | 0 |
| 3 | 3,406 | 2,089 | 40 | 0 | 21 | 0 |
| 4 | 1,267 | 0 | 0 | 0 | 0 | 0 |
| **Total** | 5,092 | **2,500** | **200** | **150** | **108** | **34** |

Format of A: 16/44.1 2,112; 24/44.1 299; 24/48 63; 16/48 26. Spectrum-marked: A 47, B 4, bait 2, processed 2.
Set overlaps (`jobs.jsonl`): A only 2,288; A+B 34; A+B+bait 58; A+B+processed 28; A+B+bait+processed 80; A+bait 12.
Phase 2 therefore has 212 source files. Per-stratum counts are in `corpus/selection_summary.txt:9-29`; the maximum
per artist is 8 in A and 3 in B and bait.

Outputs: `corpus/library_tiers.jsonl` (every library FLAC: `path, size, mtime, duration, bps, rate, channels,
samples, kbps, md5_set, vendor, tier, subtier, reasons, strata, integrity, excluded, spectrum_mark, sets`),
`corpus/jobs.jsonl` (the same fields for set A, one job per source file, in `stable()` order, which is also the run
order), `corpus/set_a.csv`, `set_b.csv`, `set_bait.csv`, `set_processed.csv` (sorted by path) and the printed summary
`corpus/selection_summary.txt`. The selection is deterministic for a given inventory and evidence.

## 4. Labels and their limitations

| Item | Label | Basis |
|---|---|---|
| Set A original | negative ("presumed genuine") | provenance tier 1-3 and integrity, not proof |
| Set B variant, processed variant, `ctl48_opus160` | positive | made by the harness from a lossy encode, by construction |
| Bait variant, `ctl48_40k` | negative | genuine audio through a resampler, by construction (genuine only if its source is) |

**Circularity of the spectrum check's false-positive rate.** The library manager's stored mark (`spectrum_mark`) is
the spectrum check's own verdict. The 47 set-A originals marked lossy were labelled by the spectrum check itself;
they are reported apart ("Echolot-marked fake (circular, apart)") and in no other group. The remaining 2,453 unmarked
originals are therefore, by selection, files the spectrum check had passed, and the harness runs the same code
(RQ0: 860 of 860 stored verdicts reproduced). Spectrum's 0 false positives on those 2,453 originals hold by
construction: they are a consistency check of the harness, not an estimate of its false-positive rate. Spectrum's
false-positive evidence comes from the bait set and the 48 kHz control (`ctl48_40k`) only. For lossprint and
flaccheck the unmarked originals are a negative set already filtered by the spectrum check, so their false-positive
rates there are conditional on a spectrum pass.

Further limitations:

- **Tier 1 is tags only.** Store or streaming-service names in tags are copied onto transcodes; the tier does not
  prove a store purchase.
- **Tier 3 may hold real fakes.** Its signs describe a careful release match, not the audio.
- **A bit-exact stream capture proves the stream, not a lossless master.** The stream carries what the label
  delivered; the stream-capture check ([10](#10-stream-capture-ground-truth-check)) found lossy masters among such
  captures.
- **YouTube URLs.** 77 set-A files carry a YouTube URL in their own tags (76 tier 3, 1 tier 1; 5 of them
  spectrum-marked). This provenance sign was measured, not used to select: the files were not moved between tiers;
  the analysis reports them as a group and leaves them out of some negative sets ([8.2](#82-false-positives),
  [13](#13-design-facts-that-affect-interpretation)).
- Consequently every false-positive rate on originals is an **upper bound**: a flagged "genuine" file may be a real
  fake.
- **Positives are synthetic.** They cover 18 encodings by current encoders (ffmpeg's libmp3lame, native AAC,
  libopus, libvorbis; LAME, FDK, opusenc, oggenc). Real fakes may come from other or older encoders (e.g. Musepack,
  WMA, Xing), several generations, or extra processing. If a source in A is itself lossy, its variants are
  transcodes of a transcode; they remain correct positives.
- **Bit depth differs between classes for 24-bit sources:** every variant except `mp3_320_up48` is decoded to 16
  bit ([5.3](#53-decoding-back)), while its 24-bit original stays 24-bit (35 of 189 pooled B sources; 28 bait
  sources).
- **Bait covers soxr resampling only**, not other mastering low-pass filters.
- **The "doubted" bait subgroup is defined with detector output**: bait of sources that carry `spectrum_mark` or
  that lossprint flagged (p ≥ 0.5) in their original form is reported apart ([8.3](#83-recall)). This uses one
  detector's output to define a negative set.

## 5. Transcode generation

All variants are made in a fresh per-job directory `scratch/run/job-<uuid12>/` on the NVMe disk, at nice 19 and
idle I/O priority (`run.py:39`, `:402-403`), and deleted with it (`:416-417`). Every command is an argument list
(no shell), metadata is dropped (`-map_metadata -1`) and only the first audio stream is used (`-map 0:a:0`).
`SOXR = "resampler=soxr:precision=28"` (`run.py:42`).

### 5.1 ffmpeg encodes (set B)

Code: `run.py:45-58`. Encode (`run.py:231-232`), from the original FLAC:

```
nice -n 19 ionice -c3 ffmpeg -nostdin -v error -y -i SRC -map 0:a:0 -map_metadata -1 <ARGS> OUT.<ext>
```

| Variant | `<ARGS>` | Container | Tolerance kind |
|---|---|---|---|
| `mp3_128` | `-c:a libmp3lame -b:a 128k` | mp3 | `ffmp3` |
| `mp3_192` | `-c:a libmp3lame -b:a 192k` | mp3 | `ffmp3` |
| `mp3_320` | `-c:a libmp3lame -b:a 320k` | mp3 | `ffmp3` |
| `mp3_v0` | `-c:a libmp3lame -q:a 0` | mp3 | `ffmp3` |
| `mp3_v2` | `-c:a libmp3lame -q:a 2` | mp3 | `ffmp3` |
| `aac_128` | `-c:a aac -b:a 128k` | m4a | `aac` |
| `aac_256` | `-c:a aac -b:a 256k` | m4a | `aac` |
| `opus_96` | `-c:a libopus -b:a 96k` | opus | `opus` |
| `opus_160` | `-c:a libopus -b:a 160k` | opus | `opus` |
| `vorbis_q3` | `-c:a libvorbis -q:a 3` | ogg | `exact` |
| `vorbis_q6` | `-c:a libvorbis -q:a 6` | ogg | `exact` |
| `vorbis_q9` | `-c:a libvorbis -q:a 9` | ogg | `exact` |

Encoder sample formats are left to ffmpeg's automatic negotiation; libopus resamples to 48 kHz internally.

### 5.2 Standalone encoders (set B)

Code: `run.py:59-66`, `:277-290`. First a WAV of the source (`run.py:278-280`), 24-bit if the source has more than
16 bits, else 16-bit:

```
nice -n 19 ionice -c3 ffmpeg -nostdin -v error -y -i SRC -map 0:a:0 -map_metadata -1 -c:a pcm_s24le|pcm_s16le source.wav
```

Then, with the encoders' defaults otherwise (`run.py:234-235`: `fdkaac` and `oggenc` take `-o OUT IN`, the others
`IN OUT`):

| Variant | Command | Tolerance kind |
|---|---|---|
| `lame_320` | `lame --quiet -b 320 source.wav OUT.mp3` | `exact` |
| `lame_v0` | `lame --quiet -V 0 source.wav OUT.mp3` | `exact` |
| `fdkaac_256` | `fdkaac --silent -b 256000 -o OUT.m4a source.wav` | `fdk` |
| `fdkaac_vbr5` | `fdkaac --silent -m 5 -o OUT.m4a source.wav` | `fdk` |
| `opusenc_160` | `opusenc --quiet --bitrate 160 source.wav OUT.opus` | `opus` |
| `oggenc_q6` | `oggenc --quiet -q 6 -o OUT.ogg source.wav` | `exact` |

An encode counts as failed if the encoder exits non-zero or the output is missing or empty (`run.py:236-240`).

### 5.3 Decoding back

Code: `run.py:221-224`, `:242-243`.

```
nice -n 19 ionice -c3 ffmpeg -nostdin -v error -y -i ENC -map 0:a:0 -map_metadata -1 \
    [-af aresample=<rate>:resampler=soxr:precision=28] -ar <rate> -sample_fmt s16 -c:a flac OUT.tmp.flac
```

`<rate>` is the source's rate. The `aresample` filter is added for Opus only (Opus decodes at 48 kHz). The decoder is
ffmpeg's default for each codec. All variants of 5.1-5.2 are 16-bit FLACs at the source rate; no dither is requested
(ffmpeg's default conversion).

### 5.4 Checks and sample-count tolerances

Code: `run.py:69-74`, `:191-219`. Each decoded FLAC is checked before it gets its final name `<variant>.flac` (atomic
`os.replace`, `:212-215`):

- `ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels,duration_ts,sample_fmt,bits_per_raw_sample -of json` (`:148-155`);
- `flac -t -s` must succeed (`:195`);
- sample rate equals the expected rate; channel count equals the source's;
- `delta = duration_ts − expected`, where `expected` is the source's STREAMINFO total samples (or
  `round(n · 48000 / rate)` for 48 kHz outputs), must lie in the tolerance range of its kind.

| Kind | Allowed delta (samples) | Applies to | Basis |
|---|---|---|---|
| `exact` | 0 … 0 | Vorbis (ffmpeg, oggenc), LAME CLI, `mp3_320_gain` | measured exact in the pilot run |
| `ffmp3` | 0 … 0 | ffmpeg MP3 at 44.1 kHz | measured exact in the pilot run |
| `ffmp3_48k` | 0 … +64 | ffmpeg MP3 at 48 kHz (`:197`) | ffmpeg's libmp3lame decoded 46 samples long at 48 kHz in the pilot run |
| `aac`, `fdk` | 0 … +1024 | ffmpeg AAC, FDK | padding to the next 1024-sample frame |
| `opus` | −2 … +2 | libopus, opusenc | libopus round trips with soxr land up to 2 samples off (measured) |
| `bait` | −4 … +4 | bait round trips | two soxr conversions |
| `up48` | −2 … +2 | `mp3_320_up48` | one soxr conversion |
| `ctl48` | −4 … +4 | 48 kHz control | up to two soxr conversions |

A pilot run of the harness before the main run (7 sources in phase 1; 6 sources with 121 variants in phase 2; 2 in
phase 3; chosen to cover non-ASCII paths, 24-bit, 48 kHz, a tier-2 file and a spectrum-marked file) fixed these
tolerances; its output is not part of the results.

A variant failing any check gets a `meta` line with `ok: false` and the reason, is deleted and is not scored
(`:208-210`). The main run met two ffmpeg length behaviours outside these tolerances: libmp3lame decodes
47 − (n mod 1152) samples long whenever n mod 1152 is 1-46 (8 sources at 44.1 kHz lost their ffmpeg MP3 and
processed variants; one 48 kHz source passed within 0 … +64), and ffmpeg's native AAC dropped the last partial frame
on 2 sources (−1 and −28). 54 `meta` lines were rejected in total. The tolerances were not widened after the fact.

## 6. Bait, processed and 48 kHz control

### 6.1 Bait (negatives)

Code: `run.py:67`, `:291-303`. Genuine audio behind a steep resampler edge, from the bait sources (all 44.1 kHz):

```
ffmpeg -nostdin -v error -y -i SRC -map 0:a:0 -map_metadata -1 \
    -af aresample=<mid>:resampler=soxr:precision=28,aresample=44100:resampler=soxr:precision=28 \
    -sample_fmt s16 -c:a flac OUT.tmp.flac
```

with `<mid>` = 32000 (`bait_32k`), 38000 (`bait_38k`), 40000 (`bait_40k`); tolerance `bait`.

### 6.2 Processed (positives)

Code: `run.py:68`, `:254-276`. For B sources that are also in the processed set, the very `mp3_320` encode of 5.1 is
decoded twice more before it is deleted:

| Variant | Decode filter and format | Expected samples | Tolerance |
|---|---|---|---|
| `mp3_320_gain` | `-af volume=-1.3dB`, `-sample_fmt s16`, source rate | n | `exact` |
| `mp3_320_up48` | `-af aresample=48000:resampler=soxr:precision=28`, `-sample_fmt s32`, `-ar 48000` (written as 24-bit FLAC) | round(n · 48000 / 44100) | `up48` |

### 6.3 48 kHz control (phase 3)

Code: `scripts/select_ctl48.py`, `run.py:304-336`. In phase 1, lossprint flagged 6 of 15 unmarked 48 kHz originals as
Opus, 5 of them with a YouTube URL in their tags (`select_ctl48.py:4-8`). The control, defined after phase 1 and run
as phase 3, asks whether lossprint reacts to Opus or to any 48 kHz file with a steep 20 kHz edge. Sources, chosen by
provenance only:

- every set-A file at 48 kHz with sub-tier 1 and no YouTube URL in its tags (`:31`; 4 files);
- 30 bait sources, ordered by unsalted `sha256(path)`, at most one per artist (artist = first path component,
  case-folded; `:20`, `:32-41`): 29 tier 1, 1 `2_proven`.

Output: `corpus/jobs_ctl48.jsonl`, `corpus/set_ctl48.csv` (34 jobs). Two variants per source, both at 48 kHz:

| Variant | Label | Command |
|---|---|---|
| `ctl48_40k` | negative | `ffmpeg … -af aresample=40000:<SOXR>,aresample=48000:<SOXR> -sample_fmt s16 -c:a flac` (`:308-310`) |
| `ctl48_opus160` | positive | `ffmpeg … [-af aresample=48000:<SOXR>] -c:a libopus -b:a 160k ENC.opus` (resample only for 44.1 kHz sources), then `ffmpeg … -i ENC.opus -map 0:a:0 -map_metadata -1 -ar 48000 -sample_fmt s16 -c:a flac` (`:321-329`) |

Expected samples `round(n · 48000 / rate)`, tolerance `ctl48`.

## 7. Run harness and per-job integrity guards

`scripts/run.py --phase 1|2|3` (`:438-510`). Jobs come from `corpus/jobs.jsonl` (phases 1, 2) or
`corpus/jobs_ctl48.jsonl` (phase 3); phase 2 keeps the jobs whose sets include B, bait or processed (`:452-453`).
Workers are threads; each owns one spectrum container. Jobs are taken in file order (`:476`).

| Phase | Per job |
|---|---|
| 1 | the original as it is: `original_meta()` then the three detectors on the library file |
| 2 | `make_variants()` (sections 5 and 6) then the detectors on all checked variants of the source, in one batch |
| 3 | the two control variants, then the detectors |

**`original_meta()`** (`run.py:163-183`, phase 1 only): sha256 of the file; then one ffmpeg pass that writes the
decoded-audio MD5 (`-map 0:a:0 -c:a pcm_s32le -f md5`) and runs
`astats=metadata=0:measure_perchannel=none:measure_overall=Peak_level+RMS_level+Flat_factor+Peak_count` (`:170-172`),
recording peak (dB), RMS (dB), flat factor and peak count from the last values ffmpeg prints.

**Spectrum container** (`run.py:106-112`):

```
docker run --rm -i --network none --cpu-shares 128 \
  -v <LIB.parent>:<LIB.parent>:ro -v <repo>/scratch/run:<repo>/scratch/run:ro -v <repo>/scripts:/bench:ro \
  --entrypoint nice <IMAGE> -n 19 ionice -c3 python -u /bench/spectrum_worker.py
```

Requests and answers are JSON lines with a running id; an id mismatch or a closed pipe raises an error, and the
worker restarts the container (`:115-125`, `:493-495`). The library and the scratch directory are mounted read-only
at their host paths, so the worker sees the same absolute paths as the host.

**Guards:**

| Risk | Guard | Code |
|---|---|---|
| live library (files may be renamed or replaced) | size and mtime compared with the job entry before the job (`changed_before_run`, job not scored) and after it (`changed_during_run`, `job_done ok: false`); the library manager's background jobs paused | `run.py:398-401`, `:418-420` |
| stale or partial variant | fresh uuid directory per job; `.tmp` names; final name only after all checks | `:402`, `:212-213` |
| silently skipped file | exactly one line per (variant, detector), or an error line | `:340-390` |
| scored twice or never | `job_done` per job; resume skips jobs with a `job_done` line; a line cut by a kill is skipped and its job runs again | `:424-435`, `:461-462` |
| lost output | one job's lines written at once, flushed and fsynced | `:135-145` |
| full scratch disk | a job waits while less than 8 GiB (`MIN_FREE = 8 * 2**30`) are free on the scratch disk | `:41`, `:486-487` |
| host memory | `scripts/memguard.sh` touches `results/STOP` if MemAvailable drops below 2,500 MB (checked every 10 s while the run is active); it never triggered | `memguard.sh:4-8` |
| stop | `results/STOP`, SIGINT or SIGTERM: running jobs finish, no new job starts | `run.py:472-473`, `:481` |
| harness drift from the stored verdicts | the spectrum check runs in the image of the commit whose verdicts are stored; phase 2 only starts after `analyze.py --partial` reports 0 reproduction mismatches and 2,500 complete phase-1 jobs | `chain.sh:4-11` |

**Output** `results/phase<N>.jsonl`: one line per (job, variant, detector) with `job` (`p<N>:<path>`), `phase`,
`variant`, `detector` (`run_start`, `meta`, `spectrum`, `lossprint`, `flaccheck`, `job_done`, `job_error`), `ok`,
`error`, `out` (the tool's raw output). `run_start` records the tool versions (`versions()`, `:82-100`), the arguments
and the number of jobs; `job_done` the job's wall time. Progress goes to `results/progress_phase<N>.json`.

**Orchestration and workers:**

| Step | Command | Workers | Wall time |
|---|---|---|---|
| phase 1 | `python3 scripts/run.py --phase 1 --workers 5 --lp-threads 1` | 5 | 81 min |
| chain | `scripts/chain.sh`: waits for phase 1, `analyze.py --partial`, checks 0 mismatches and 2,500 complete, then `run.py --phase 2 --workers 5 --lp-threads 2`, then `run.py --phase 3 --workers 5 --lp-threads 2` | 5 | phase 2: 3 h 08 min; phase 3: 3 min |
| memory guard | `scripts/memguard.sh`, alongside phases 1-3 | | |
| clip-free | `scripts/after_chain.sh`: waits for the chain, then `nice -n 19 python3 scripts/clipfree.py --workers 4` | 4 | 13 min |
| spectrograms | `python3 scripts/spectrograms.py --workers 1` (397 PNGs) | 1 | 29 min |
| analysis | `python3 scripts/analyze.py` | | seconds |

Wall times are measured from the `run_start` lines, the logs and file modification times. Median job wall time:
phase 1 9.6 s, phase 2 263 s (max 577 s), phase 3 24 s; median `spectrum()` call 0.2 s (originals) to 0.5 s
(variants). No job had `job_error`, `changed_before_run` or `changed_during_run`.

## 8. Scoring and statistics

Line numbers in this section refer to `scripts/analyze.py` unless another file is named. `analyze.py` reads
`results/phase{1,2,3}.jsonl`, `results/clipfree.jsonl` (if present), `corpus/jobs.jsonl` and
`corpus/inventory.jsonl`, and writes `results/analysis/summary.md`, `originals.csv`, `variants.csv`,
`disagreements.csv`, `reproduction_mismatches.csv`.

### 8.1 Basics

- **Complete jobs only** (`:43-73`): a job counts only with a `job_done` line with `ok: true`; if a job ran more than
  once, its last complete attempt counts.
- **Flags** (`:76-87`): spectrum = verdict `lossy` (None if the spectrum line is not ok); lossprint =
  `transcode_probability ≥ threshold` (0.5 unless swept); flaccheck = `TRANSCODED`; flaccheck_wide = `TRANSCODED` or
  `SUSPICIOUS`. A detector without valid output for an item is left out of that item's denominator. A spectrum
  `unknown` verdict counts as not flagged (none occurred).
- **Rates** are k/n with a Wilson score 95 % interval (`:34-40`), z = 1.96:
  `c = (p + z²/2n) / (1 + z²/n)`, `h = z·sqrt(p(1−p)/n + z²/4n²) / (1 + z²/n)`, interval `[max(c−h, 0), min(c+h, 1)]`,
  printed as `p% [lo–hi] (k/n)` with one decimal. The replay and held-out tables print `p% (k/n)` without an interval.
  Items are treated as independent; variants of the same source are not (no clustering correction), and no
  multiple-comparison correction is applied.

### 8.2 False positives

Negatives are the set-A originals (`:177-204`). A **false positive** is a flagged original. Files with
`spectrum_mark` go into their own group "Echolot-marked fake (circular, apart)" and into no other group
([4](#4-labels-and-their-limitations)). Every other original counts in "all (unmarked)", its sub-tier, each of its
strata, its format (`bits/rate`), its measured loudness groups, and either "provenance YouTube URL in tags" or
"all (unmarked, no YouTube URL in tags)".

Measured loudness groups (`:103-112`, from phase-1 astats): `loud_rms>-9dB` (RMS > −9 dB), `rms_-18..-9dB`,
`quiet_rms<-18dB` (RMS < −18 dB), `clipped_flat>=1` (flat factor ≥ 1), `peak>=-0.1dBFS`. Clipping is confounded with
the label: decoding a lossy file of a loud master clips by itself.

YouTube URL: `youtube.com` or `youtu.be` anywhere in the file's inventory tags (`:115-119`).

### 8.3 Recall

Positives are the phase-2 variants other than bait (`:206-243`). **Recall** of a variant = flagged / scored
variants of that kind. Pooled tables use 44.1 kHz sources only (`:220`); set B's 11 sources at 48 kHz appear only in
"Recall by source format". Processed variants appear as their own rows.

Bait false positives are reported per round trip. Bait of a **doubted** source (its original carries
`spectrum_mark`, or lossprint flagged it at 0.5; `:208`) is reported as "doubted source: bait_…" and kept out of the
bait rows (9 sources).

48 kHz control (`:245-262`): per variant, sources doubted as above reported apart; plus the range of lossprint
probabilities.

### 8.4 lossprint threshold sweep

Code: `:423-437`. Thresholds `0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99` (`:30`). False positives on: unmarked
originals of sub-tiers 1 and 2_proven; all unmarked originals (YouTube included); all non-doubted bait. Recall on
all pooled positive variants (44.1 kHz sources, processed included).

### 8.5 spectrum threshold replay

Code: `:294-332`. `sim(r, drop_db, traces_from, flicker, max_cut)` recomputes the spectrum decision from the stored
`cutoff_hz`, `drop_db` and `flicker_at_edge`: not lossy unless `drop ≥ drop_db` and `cut < max_cut`; lossy if
`cut < traces_from`; otherwise lossy if `flicker_at_edge` is None or above `flicker`. Items with verdict `unknown` or
no drop are left out. Because `flicker_at_edge` exists for every drop ≥ 25 dB, the replay is valid for
`drop_db ≥ 25`. At the check's own constants (30, 19000, 0.03, 20400) the replay is compared with the real verdicts
(`:310`).

Grid (`:311-312`): DROP_DB ∈ {25, 27, 28, 30} × TRACES_FROM ∈ {17000, 17500, 18000, 18500, 19000} × FLICKER ∈
{0.02, 0.03, 0.05}; MAX_LOSSY_CUT fixed at 20400. Columns: false positives on unmarked originals without a YouTube
URL; on non-doubted bait plus `ctl48_40k`; recall on all positives (phase-2 variants of 44.1 kHz sources and all
`ctl48_opus160`, including those of the 4 native 48 kHz sources); and recall for `aac_128, aac_256, fdkaac_256,
fdkaac_vbr5, mp3_320, lame_320, mp3_v0, opus_160, vorbis_q6, ctl48_opus160` (`:313-314`).

### 8.6 Candidate rules on held-out halves

Code: `:334-381`. Each source path goes to one half: `half 1` if `sha256(b"heldout:" + path).digest()[0] < 128`, else
`half 2` (`:352-354`). The salt is needed because the selection filled the sets in plain sha256 order, so an unsalted
split comes out unbalanced (1,776 / 605). All variants of a source share its half. Item sets per half: unmarked
originals without a YouTube URL (FP originals); non-doubted bait and `ctl48_40k` (FP bait); phase-2 and phase-3
positives of 44.1 kHz sources (recall; this includes `ctl48_opus160` of the 30 bait sources) (`:356-369`).

Rules (`:339-350`):

| Rule | Definition |
|---|---|
| spectrum (current) | `sim(r)` |
| spectrum with TRACES_FROM 18 kHz | `sim(r, traces_from=18000)` |
| spectrum + 25-30 dB with flicker ≥ 0.05 | current, or `25 ≤ drop < 30` and `cut < 19000` and (`flicker_at_edge` None or ≥ 0.05) |
| spectrum + 48 kHz Opus band | current, or file at 48 kHz and `19800 ≤ cut ≤ 20500` and `drop ≥ 20` |
| lossprint ≥ 0.5 | `p ≥ 0.5` |
| spectrum OR lossprint | `sim(r)` or `p ≥ 0.5` |

The rules are fixed and evaluated on both halves; nothing is fitted on one half. They were, however, formulated
with the pooled results in view, so the halves are a consistency check rather than a strictly untouched test set.

### 8.7 Combined rules

Code: `:264-292`. `spectrum OR lossprint`, `spectrum AND lossprint`, `lossprint AND flaccheck`, `2 of 3` (spectrum,
lossprint, flaccheck at their default flags), on items where all three detectors have output: unmarked originals
(YouTube included), non-doubted bait, and all phase-2 positives of 44.1 kHz sources. Unmarked originals flagged by at
least two detectors are listed.

### 8.8 Other outputs

- **Reproduction check** (`:150-175`): for every phase-1 original whose import time (`filed.ts` in the inventory) is
  at or after `REPRO_SINCE` (`:29`), the time the current spectrum check went into use (Echolot commit 4ea672f), the
  harness verdict (lossy or not) is compared with the stored one (`quality == 'fake'` or a `lossy_sourced` mark).
  Mismatches go to `reproduction_mismatches.csv`.
- **Flicker below 19 kHz** (`:439-455`): distribution (n, min, p5, median, p95, max) of `flicker_at_edge` for edges
  below 19 kHz with drop ≥ 25 dB, for unmarked originals, bait (here including bait of doubted sources) and each
  codec family (variant name up to the first `_`). p5/p95 are `sorted(xs)[int(p·n)]`.
- **Disagreements** (`:457-481`): originals where the three detectors' flags differ, in `disagreements.csv`; all
  originals in `originals.csv`, all phase-2 variants in `variants.csv`.
- **Spectrograms** (`scripts/spectrograms.py`): one PNG per original in `disagreements.csv`, host ffmpeg,
  `-filter_complex [0:a:0]showspectrumpic=s=1600x600:mode=combined:scale=log:legend=1 -frames:v 1` (`:25`), into
  `results/analysis/spectrograms/` with `index.csv`.

## 9. Clip-free experiment

Motivation (from phase 2): a loud master's lossy decode clips, and the clipping distortion fills the band above the
encoder's edge (MP3 320 measured about 28 dB, the same MP3 at −1.3 dB about 50 dB; `clipfree_worker.py:3-5`). The
experiment repeats `spectrum()`'s edge search on the same excerpts with and without clipped FFT frames. Measurement
only; the check itself is unchanged.

**Items** (`scripts/clipfree.py`):

- negatives: set-A originals whose phase-1 astats peak is ≥ −0.05 dBFS or unknown (`:83-89`): 1,111 of 2,500. The
  others cannot contain a sample at the clip level, so their clip-free result equals the normal one by construction;
- positives: the first 60 set-B sources at 44.1 kHz in `sha256(b"clipfree:" + path)` order (`:91-92`), each as
  `mp3_192, mp3_320, mp3_v2, aac_128, lame_320, vorbis_q3` (`:23`).

Variants are made with `run.py`'s encoder table (`clipfree.py:52-72`), but without the checks of
[5.4](#54-checks-and-sample-count-tolerances), and the WAV for `lame_320` is always 16-bit (`:63-64`). Decoding:
`-ar <rate> -sample_fmt s16 -c:a flac`.

**Worker** (`scripts/clipfree_worker.py`, in a container of the same image with the same mounts and limits as the
spectrum worker; `clipfree.py:30-35`). Per file, stereo files of at least 20 s only (`clipfree_worker.py:85`):

1. `echolot` = `audio.spectrum()` itself;
2. the three excerpts decoded in stereo, `ffmpeg -v error -ss {dur·pos:.1f} -t 15 -i PATH -ac 2 -f f32le -`, mono =
   mean of the channels (`:23-29`, `:38-39`);
3. `edge()` (`:32-70`) = `spectrum()`'s steps 3-8 with the same constants, run twice: `asis` (all frames) and
   `clipfree`, which skips every 8192-sample frame in which any sample of either channel has `|x| ≥ CLIP = 0.999`
   (`:20`, `:41-44`). `_flicker()` runs on the unfiltered mono excerpts;
4. `same_as_echolot`: `asis` and `echolot` agree on cutoff and verdict (`:90`).

Analysis (`analyze.py:383-421`): the baseline is the check's own verdict. New flags and lost flags among unmarked
originals without a YouTube URL; how many new flags lossprint also flags (≥ 0.5) on the original; recall per variant
as the check measures vs clip-free. Output `results/clipfree.jsonl` (1,471 lines). Not measured: the bait set
clip-free.

## 10. Stream-capture ground-truth check

A detector's probability says whether audio passed through a lossy encoder, not whether the release itself was
delivered lossy. This check compares library copies with bit-exact captures of the official lossless stream
(RQ7).

**Songs.** Ten library files outside the benchmark corpus, all at 44.1 kHz and available on Spotify, that lossprint
flagged (p 0.896-1.000; MP3 or AAC family) while the spectrum check passed them: nine disputed cases without an
encoder signature visible in the spectrogram, and FindMyName – Rebel, with a visible MP3 signature, as a positive
control. The choice is purposive, not random, so the outcome is not a rate for the library.

**Captures.** Each song was captured from Spotify Lossless with a stream-capture tool that verifies its captures
against the stream. All ten captures match the decoded-audio MD5s in the tool's record
(`ffmpeg -v error -i F -map 0:a -c:a pcm_s32le -f md5 -`); Turno's capture differs from the stream only in the
stream's ~10 ms fade-in. The captures are copyrighted audio and are not published.

**Inputs of the comparison** (`compare.json`, not published because it holds local paths): per song `song`, `rec`
and `lib` (paths of capture and library copy), `rec_md5` and `lib_md5` (decoded-audio MD5 as above), `expected` (the
MD5 in the capture tool's record), `rec_info` and `lib_info` (ffprobe `sample_rate`, `bits_per_raw_sample`,
`duration_ts`, `duration`) and `lib_lp` (lossprint on the library copy: the stored result of the same lossprint 1.1
release binary and invocation as below). No library copy is MD5-identical to its capture (lengths differ by 1 to
2,305 samples).

**`scripts/align_diff.py`**, per row:

1. Decode both files to 32-bit PCM, `nice -n 19 ffmpeg -v error -i PATH -map 0:a -f s32le -acodec pcm_s32le -`, as
   float64 at full scale (÷ 2³¹), assumed stereo (`:14-17`).
2. Lag (`:20-27`): cross-correlation (`scipy.signal.fftconvolve`) of the mono mix of the capture's first 30 s
   against the library copy's first 34 s; the argmax within ±2 s gives `k` with `lib[i + k] ≈ rec[i]`. The sample
   rate is fixed at 44,100 Hz.
3. Align by `k` and cut both to the overlap (`:32-38`).
4. `bits` = the smaller of the two `bits_per_raw_sample`; `identical` = share of samples (all channels) with
   `round(rec·2^(bits−1)) == round(lib·2^(bits−1))` (`:39-41`).
5. `gain` = least-squares gain of lib onto rec; `residual_db` = `10·log10(mean((rec−lib)²) / mean(rec²) + 1e-30)`,
   and `residual_db_gain` the same after applying the gain (`:42-46`). Identical audio gives −300 dB (the floor).
6. One JSON line per song: `song, lag, overlap_s, bits, identical, residual_db, gain, residual_db_gain` (`:47-48`).

Output: `results/capture-check/align.jsonl`. Only 44.1 kHz stereo files are handled (`:17`, `:20`, `:47`).

**Drift and residual shape** (for the two songs that are not the same audio; an inline computation, not saved as a
script and not recomputable from `align.jsonl`, which keeps only scalars): lags at 5 s, 100 s and (end − 30 s) on
20 s windows (±2 s search) to rule out drift or resampling; the residual of the aligned mono mixes relative to the
capture's mono signal per band, from Welch PSDs (`nperseg = 8192`), bands 0-4, 4-12, 12-16, 16-19 and 19-22.05 kHz;
and the residual in 10 s segments every 60 s.

**Detectors on the captures** (`results/capture-check/recs_scan.jsonl`, paths reduced to file names): `spectrum()`
and lossprint, run in a container built from a later Echolot commit (87f18a8) whose `spectrum()`, `_flicker()` and
constants are identical to e9f0bf9 (compared as syntax trees), with the upstream lossprint 1.1 x86_64 release binary
called as `lossprint --jobs 1 --threshold 0 --output-format jsonl -- FILE`; container limits `--network none --cpus 1
--cpu-shares 128 --memory 2g`, nice 19, idle I/O. Fields used: `spectrum` (as in [2.1](#21-echolot-spectrum-check))
and `lossprint` (`p`, `encoder`, `kbps`); the other fields are outputs of the scan wrapper and are not used.

**Reading of a song:**

| Outcome | Criterion |
|---|---|
| same audio | `identical` = 1.0 and residual −300 dB over the aligned overlap |
| same master at a lower bit depth | `identical` ≈ 0.5 at the coarser bit depth, residual below −75 dB, gain 1.0 |
| lossy copy of the master | residual around −30 dB or higher with constant lag (no drift) and gain ≈ 1.000, residual rising with frequency (codec-shaped, not broadband) |
| lossy master | the capture itself has lossprint p ≥ 0.9 (or a spectrum `lossy` verdict) |

## 11. Decision rule derived from the data

After RQ1-RQ7, one rule combines the two usable detectors. It is derived from the data in `results/analysis/` and
`results/capture-check/`; it is not fitted and not tested on held-out data beyond the tables of section 8, from which
its rates on this corpus can be read (lossprint sweep at 0.5 and 0.9, combined rules).

| Order | Condition | Verdict | Basis |
|---|---|---|---|
| 1 | spectrum verdict `lossy` | lossy, whatever lossprint says | all 1,625 phase-2 transcodes that spectrum flagged also have lossprint ≥ 0.5, so lossprint never contradicts spectrum on synthetic positives; the synthetic positives do not cover older or unusual encoders, several generations or extra processing, which an edge detector may still see ([4](#4-labels-and-their-limitations)); the cost is spectrum's resampler-edge false positives (bait, `ctl48_40k`) |
| 2 | lossprint p ≥ 0.9 | lossy | 3,753 of 3,762 phase-2 transcodes (all source rates) score ≥ 0.9 (99.8 %; minimum 0.703, 9 in [0.7, 0.9)); raising the threshold from 0.5 to 0.9 lowers false positives on all unmarked originals from 4.9 % to 4.2 % and on bait from 0.7 % to 0.2 % |
| 3 | 0.5 ≤ p < 0.9 | doubtful: a label, no decision | 9 of 3,762 phase-2 transcodes and 17 of 2,453 unmarked originals fall in this band; too few to decide either way |
| 4 | otherwise, or no lossprint result | ok | |
| - | a bit-exact capture of the official lossless stream that rules 1-2 judge lossy | lossy master: the best available copy, not a lossy copy | in the capture check, lossprint's p does not separate master from copy (the 8 lossy masters score 0.968-1.000 on the capture itself, like lossy copies), and spectrum flags one capture (Zeph, 24-bit); only the comparison with a capture separates the two |

The spectrum improvements of RQ5 (lower `TRACES_FROM` to 18 kHz; measure without clipped frames) are separate
findings and are not part of this rule.

## 12. Computing environment

| Item | Value |
|---|---|
| Host | Intel Core i3-10105F (4 cores / 8 threads, 3.7 GHz), 32 GB RAM |
| OS | Debian GNU/Linux 13 (trixie), kernel 6.12 (amd64) |
| Library | HDD, ext4, read-only for the study |
| Scratch | `scratch/run/` in the repository, NVMe, ext4 (194 GB free at the start) |
| Docker | docker.io 26.1.5+dfsg1-9+deb13u1 |
| Host Python | 3.13.5, standard library only (run, analysis, verification) |
| ffmpeg, host (encode, decode, checks, astats, hashes, spectrograms) | 7.1.5-0+deb13u1 (Debian) |
| flac | 1.5.0+ds-2 |
| lame | 3.100-6+b3 ("LAME 64bits version 3.100") |
| fdkaac | 1.0.6-0.1 (Debian contrib) |
| opus-tools | 0.2-1+b3 (opusenc 0.2, libopus 1.5.2) |
| vorbis-tools | 1.4.3-1 (oggenc 1.4.3) |
| Echolot image (spectrum, clip-free, integrity check) | built from Echolot commit e9f0bf9 (`ECHOLOT_COMMIT=e9f0bf9`), image id `sha256:eff56d10aed8b942feb9b73b9350ad2c168ae9b8f63130882adce1699131183c`. Inside: Debian 13, Python 3.13.16, numpy 2.5.3, mutagen 1.48.1, ffmpeg 7.1.5 built from source (`/usr/local/bin`, Dockerfile at e9f0bf9) |
| lossprint | 1.1.0, `cargo install lossprint --version 1.1.0 --locked --features cli`, rustc 1.99.0 (b940084d7), target x86_64-unknown-linux-gnu; binary sha256 `c240754cacb6fb93008c5af4d4adf1cae0397822382c15f3dd0daa57cd0be993` |
| flaccheck | 0.1.2, https://github.com/dasunNimantha/flaccheck.git at tag v0.1.2 = c05e68526973efce9dc32423b2e1dd9cc5274857 (clean tree), release build with default features (no `ml`); binary sha256 `4836e2114e12510b011f801483093d74c46f1986b64807237af0a79842631d0b` |
| `align_diff.py` | numpy 2.5.4, scipy 1.18.1 (any recent versions suffice) |
| Echolot repository | https://github.com/Zweisteinium/echolot.git; spectrum check at e9f0bf9 |

Every phase's `run_start` line records the ffmpeg versions, the image id and commit, lossprint, flaccheck, lame,
opusenc and oggenc versions and the Debian package versions (`run.py:82-100`); they are identical across all phases
and the pilot run.

**Resource controls:** every host-side tool call runs under `nice -n 19 ionice -c3` (`run.py:39`); containers get
`--cpu-shares 128`, `--network none` and run their worker under `nice -n 19 ionice -c3`; 5 worker threads in phases
1-3 (lossprint and flaccheck 1 thread per job in phase 1, 2 in phases 2-3) and 4 in the clip-free experiment; a job
waits below 8 GiB free scratch; the memory guard stops the run below 2,500 MB available. Other services on the host
kept running during the measurement, so wall times include their load.

## 13. Design facts that affect interpretation

| Topic | Fact |
|---|---|
| Set B rates | B was not restricted to 44.1 kHz: 11 of its 200 sources are 48 kHz (the `rate48000` stratum minimum). They are excluded from every pooled recall figure and appear only in "Recall by source format" (`analyze.py:220`). |
| Processed set size | 108, not the target 100: the stratum pass ignores the target ([3.7](#37-deterministic-selection)). |
| Tier 3 | holds two kinds of files: corroborated files without store provenance (3,367) and store-tagged files with a doubt (39). |
| Capture imports without a hash match | count "stream capture without a hash match" as a corroborating sign, which counts toward the three of rule 5. |
| Integrity evidence | only the re-encode pass and `integrity_check.tsv` are evidence; the partial damage scan only selected files for re-checking. `unverified` files would not be excluded; there were none. |
| flaccheck invocation | per job on a symlink directory, with `--explain` and `--workers <lp_threads>` (1 in phase 1, 2 in phases 2-3) (`run.py:363-364`), not one file per call as in `TOOLS.md`. |
| Clip-free variants | made without the length, rate and `flac -t` checks of [5.4](#54-checks-and-sample-count-tolerances); the WAV for `lame_320` is always 16-bit (`clipfree.py:63-64`), while `run.py` uses 24-bit for 24-bit sources. |
| Clip-free negatives | 1,111 originals measured; the other 1,389 cannot reach the clip level and count as unchanged by construction. |
| 48 kHz control | defined after phase 1 in response to its results ([6.3](#63-48-khz-control-phase-3)). |
| Held-out rules | formulated with the pooled results in view ([8.6](#86-candidate-rules-on-held-out-halves)). |
| Denominators across sections | the bait table excludes doubted sources, the flicker table does not (`analyze.py:444-448`); the replay's "recall all" includes `ctl48_opus160` of native 48 kHz sources, the held-out recall does not (`:309`, `:325` vs `:368`); YouTube-tagged originals are in the main false-positive table, the lossprint sweep and the combined rules, but not in the replay, held-out and clip-free negatives. |
| Runtimes | as measured from the logs ([7](#7-run-harness-and-per-job-integrity-guards)): phase 1 81 min, phase 2 3 h 08 min, phase 3 3 min, clip-free 13 min, spectrograms 29 min. |
| Script docstrings | the usage line `run.py:16` names phases 1 and 2, but phase 3 is accepted (`run.py:440`); `analyze.py:2` names phases 1 and 2, but it also reads phase 3 and `clipfree.jsonl` (`:133`, `:384`); the invocation in `check_integrity.py:6` cannot pass the paths on stdin together with the script ([reproducing.md](reproducing.md) gives a working one). |
