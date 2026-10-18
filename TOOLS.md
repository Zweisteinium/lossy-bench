# Lossy-detection tools

Setup and smoke test (October 2026) on an i3-10105F (4 cores / 8 threads).

## Status

| Tool | Version | Binary | Build |
|------|---------|--------|-------|
| lossprint | 1.1.0 (crates.io, model 1.0 embedded) | `~/dev/lossy-bench/bin/lossprint` (33 MB) | `cargo install lossprint --version 1.1.0 --locked --features cli --root ~/dev/lossy-bench`, ok first try (rustc 1.99.0). Only warning: `chacha20 v0.10.1` in Cargo.lock is yanked. Install log in `scratch/setup/lossprint-install.log` |
| flaccheck | 0.1.2 (tag v0.1.2, commit c05e6852, clean tree) | `~/dev/lossy-bench/bin/flaccheck` (6 MB, copied from `tools/flaccheck/target/release/`) | Already built; no rebuild needed. Built without the `ml` feature (`--ml` does nothing) |

Neither binary needs ffmpeg for FLAC. flaccheck calls `ffmpeg`/`ffprobe` from PATH only for .ape/.wv/.opus.

## Recommended invocations (one file per call, JSON on stdout)

```sh
# lossprint: one JSONL line on stdout, errors on stderr, exit 1 on any failure
~/dev/lossy-bench/bin/lossprint -j 1 -t 0 -o jsonl -- "$f"

# flaccheck: one pretty-printed JSON object on stdout; per-file failures go into .errors, exit stays 0
~/dev/lossy-bench/bin/flaccheck scan "$f" --format json --quiet --workers 1 --color never
```

- `-t 0` makes lossprint report its encoder and bitrate guesses for every file. With the default `-t 0.5`, clean files get `null` for both. With `-t 0`, `verdict` is always `"transcode"` and means nothing: apply your own threshold to `transcode_probability`. The encoder and bitrate guesses for clean files are noise (for example `musepack` at 430 kbps).
- flaccheck prints the JSON with no trailing newline. Pipe it through `jq -c '.results[0]'` to get one line per file.
- Run several files in parallel by running several processes (about 4 on this box). Each call scores one file on one thread.

## lossprint 1.1.0

CNN on spectrograms at the file's own sample rate. ONNX model, run CPU-only on the pure-Rust `tract` runtime.

**Usage:** `lossprint [-t THRESHOLD] [-j JOBS] [-o table|jsonl] PATH...`. Takes files or directories (directories are scanned recursively, symlinks not followed). Files are processed in sorted path order, and all output is written after every file has finished.

**Output schema** (`-o jsonl`, one object per successfully scored file):

| Field | Type | Meaning |
|-------|------|---------|
| `transcode_probability` | float 0..1 | Raw P(transcode): mean of the per-window model outputs. 0.5 is the default cut-off (README: 0.24% false positives on untouched masters) |
| `verdict` | `"clean"` / `"transcode"` | `transcode_probability >= threshold` |
| `encoder` | string or null | Argmax of the encoder-family head: `mp3`, `ffmpeg_aac` (stands for every AAC encoder), `vorbis`, `opus`, `wma`, `mp2`, `musepack`. Null when below the threshold |
| `bitrate_kbps` | float or null (1 decimal) | Estimated source bitrate: geometric mean of the per-window regression outputs. Null when below the threshold |
| `path` | string | The path as given. A path that is not valid UTF-8 counts as a failure in jsonl mode |

The per-encoder probabilities are only available through the library (`TrackScore::encoder_probabilities()`, see `examples/score.rs` in the crate), not the CLI.

**Threading:** `-j 0` (the default) gives Rayon one worker per logical CPU. Parallelism is across files only: one file always runs on one thread (99% CPU in the tests). Scoring 6 files took 19.0 s wall with `-j 1` and 8.1 s with `-j 0` (36 s of CPU time, because hyperthreads inflate it).

**Input:** only the extensions `.flac`, `.wav`, `.aif` and `.aiff` (case-insensitive). Any other extension is rejected before decoding (`.mp3` fails with `unsupported audio file`, exit 1). WAV/AIFF must be integer or float PCM; A-law and mu-law are rejected. Limits:

- Mono or stereo only. 3 or more channels fail with `N channels; only mono and stereo are supported`. Example from the library: `Billie Eilish - bad guy.flac` is 7.1.
- Sample rate 8 to 384 kHz, analysed at the native rate with no resampling. The FFT size depends on the rate family (up to 50 kHz, up to 100 kHz, above). The model was evaluated on 44.1 to 192 kHz.
- Bit depth makes no difference (decoded to f32).
- At least 2 s long, otherwise `audio is shorter than the 2-second minimum`. Up to 14.5 s the whole track is scored as one window. Longer tracks are scored on 6 evenly spaced 14.5 s windows taken from the middle 92% of the file.

**Reads the file:** it decodes sequentially up to the end of the last window, which is about 96% of the file. It keeps only the window samples in memory. A truncated or corrupt FLAC fails (`could not decode audio: unexpected end of file`).

**Cost:** about 2.7 to 3.2 s of CPU time and 3.0 to 3.5 s wall for any track longer than about 16 s (always 6 windows). Peak RSS about 435 MB, 470 MB at 48 kHz. A 4 s clip takes 0.17 s.

**Exit codes:** 0 when every file was scored. 1 when any file failed: rows for the files that did succeed are still printed, followed by `lossprint: PATH: reason` on stderr per failure and then `Error: could not scan N file(s)`. Also 1 when the path is missing (`path is not a file or directory`), the extension is unsupported, no files were found, or the threshold is outside 0..1.

## flaccheck 0.1.2

Hand-tuned DSP heuristics, with no ML in this build:
- Tier 1: spectral cutoff, brick wall and codec signatures
- Tier 2: quantization (MDCT residual / MP3 PQMF), run only on suspects in `balanced` mode
- Tier 3: artifacts (noise floor, pre-echo, phase, joint stereo)
- Tier 4: fake hi-res (upsampling, padded bit depth)

The evidence is fused into a verdict using the thresholds compiled into `flaccheck-core/src/calibration.rs`. `thresholds.calibrated.json` is not read.

**Usage:** `flaccheck scan PATH [--mode fast|balanced|max] [--format text|json|csv|html] [-o FILE] [--workers N] [--explain] [-q] [--color WHEN]`. PATH is a file or a directory. A directory scan picks up `flac wav wave aiff aif m4a alac ape wv opus`. A single file of any type symphonia can decode is accepted, MP3 included. `--explain` has no effect on JSON: the evidence is always included.

**Output schema** (`--format json`): `{"results": [AnalysisResult], "skipped": [string], "errors": [string]}`.

| Field | Meaning |
|-------|---------|
| `path` | Path as given |
| `transcode_verdict` | `GENUINE` / `SUSPICIOUS` / `TRANSCODED` / `INCONCLUSIVE` (too band-limited to judge) |
| `hires_verdict` | `GENUINE_HIRES` / `UPSAMPLED` / `PADDED_DEPTH` / `UNKNOWN`. `GENUINE_HIRES` only means that no fake-hi-res indicator was found. It appears on every 16/44.1 file |
| `confidence` | 0..1, confidence in the verdict. It is **not** P(transcode): a genuine file gets about 0.9. Inconclusive gets 0 or 0.1 |
| `codec_guess` | Free text: `"MP3 ~128 kbps"`, `"AAC ~256 kbps"`, `"Opus ..."`, `"Vorbis (soft rolloff)"`, or null. Matched from the cutoff frequency against fixed tables (MP3 128/160/192/256/320 kbps = 16/17.5/19/19.5/20 kHz; AAC 96/128/192/256 kbps = 15.5/17/19/20 kHz; Opus edges) |
| `est_source_bitrate_kbps` | int or null, from the same table lookup |
| `spectral_info_score` | 0..1 HF-content score. Came out about 0.002 on all real music tested, so it carries no information |
| `mode` | `fast` / `balanced` / `max` |
| `duration_secs`, `sample_rate`, `channels` | Decoded stream properties |
| `bits_per_sample` | Always `null` for FLAC (symphonia does not set `bits_per_coded_sample`). Side effect: the padded-depth detector never runs on FLAC |
| `evidence[]` | `{detector, signal, value, weight, note}`: the raw scores |

Evidence signals (present only when noted):

| detector | signal | value |
|----------|--------|-------|
| spectral | `spectral_info_score` | 0..1, see above |
| spectral | `cutoff_hz` | Detected cutoff in Hz. Equals Nyquist when there is no cliff |
| spectral | `brick_wall` | 0..1 cliff strength. 0.55 or more counts as a definitive lossy fingerprint (`TRANSCODED`) |
| spectral | `rolloff_steepness` | dB/oct at the cutoff. 0 when there is no cliff, about 85 to 110 on the MP3 transcodes |
| spectral | `rolloff_hz` | 95% energy rolloff frequency |
| spectral | `edge_hz` | Highest frequency with content (72 dB dynamic range) |
| spectral | `full_band` | 1.0, present only if the content reaches 92% of Nyquist and there is no cliff |
| spectral | `early_rolloff` | 0..0.3, only for a gradual early rolloff |
| spectral | `codec_guess` | Codec certainty 0..1 (the note holds the codec text). Only if above 0.3 |
| spectral | `est_bitrate_kbps` | kbps. Only together with `codec_guess` |
| spectral | `aac_shelf` | 0..1. Only if above 0.3. 0.65 or more with a cutoff of 22 kHz or less forces `TRANSCODED` |
| spectral | `sbr_mirroring` | 0..1. Only if above 0.3. It also fired on genuine files (0.6 to 0.8) |
| hires | `upsampled` | 0..1. Only if above 0. 0.7 or more gives `UPSAMPLED` |
| hires | `resampler_imaging` | 0..1. Only if above 0.3 |
| hires | `padded_depth` | 0.5 or 0.9. Only if above 0 (never on FLAC, see above) |
| hires | `genuine_hires` | 1.0, present when none of the above are |
| artifacts | `noise_floor` | 0..1 |
| artifacts | `pre_echo`, `phase_discontinuity` | 0..1. Not in `fast` mode |
| artifacts | `joint_stereo` | 0..1, stereo only. Not in `fast` mode. Hit 0.6 on a genuine track as well |
| quant | `aac_mdct_residual`, `mp3_pqmf` | 0..1. Only in `max` mode, or in `balanced` when spectral suspicion is above 0.25 or artifact suspicion above 0.35, and only if above 0.15 |
| abstention | `abstain_band_limited` | 1.0 when the content ends below min(0.62 × Nyquist, 13 kHz) with no cliff |

For a continuous "lossy" score, use `brick_wall`, `cutoff_hz` and `codec_guess` from the evidence array rather than `confidence`.

**Threading:** `--workers N` (default 4) is a Rayon pool across files. A single file runs on one thread.

**Reads the file:** it decodes the whole file into memory as interleaved f32. Peak RSS is about 680 MB for a 4:46 stereo track in balanced/max mode and 160 MB in fast mode. Spectral analysis uses the **left channel only**, over windows: fast 2 × 8 s, balanced 3 × 10 s, max 5 × 15 s, placed at the start, middle and end. Hi-res and artifact analysis use the whole left channel.

**Cost per file** (wall, single thread, 2:12 to 4:46 tracks): fast 0.2 to 0.5 s, balanced 0.7 to 1.5 s, max 0.7 to 1.6 s. On these files max took about as long as balanced.

**Input handling:**
- **Sample rate:** any. Above 48 kHz the lossy-codec gate turns off cutoff, AAC-shelf, SBR and codec matching, so a hi-res file can never be flagged on spectral grounds. A 128k MP3 transcode upsampled to 96k/24 came out `INCONCLUSIVE` (and not `UPSAMPLED`). 48 kHz works normally.
- **24-bit:** decodes fine. Padded-depth detection does not work on FLAC because `bits_per_sample` is null. A 16-bit track padded to 24 bits came out `GENUINE` / `GENUINE_HIRES`.
- **Mono:** works (`channels: 1`, no `joint_stereo`).
- **More than 2 channels: broken.** The decoder keeps only L/R but still reports N channels, so the duration is wrong (the 7.1 file gave 48.5 s for a 194 s track) and the verdict is meaningless. Skip files with more than 2 channels.
- **Short files:** no minimum. A 1 s file is analysed (the window shrinks to the file length).
- **Truncated/corrupt files:** decoding stops at the first I/O error and the part read so far is analysed with no warning (a FLAC truncated to 3 MB gave a result with `duration_secs` 29.8). Fully unreadable files appear in `errors[]`. To catch truncation, compare `duration_secs` with the duration in the header.

**Exit codes:** 0 whenever the scan ran, even if every file ended up in `errors[]` or `skipped[]`. 1 only for top-level failures (path missing, no supported files, I/O writing `-o`). The error message goes to stderr (`✗ ...`). Always check `.errors` and `.results | length`.

## Smoke test

Originals were read from the library (read-only, via symlinks in the scratch dir). Each transcode was made with `ffmpeg -c:a libmp3lame -b:a 128k` and decoded back with `-c:a flac -sample_fmt s16`. flaccheck was run in balanced mode with `--workers 1`, lossprint with `-j 1`. Timings were taken on an idle box.

| File | Format | lossprint P(transcode) | lossprint enc/kbps | lp wall | flaccheck verdict (conf) | fc codec | fc brick_wall / cutoff | fc wall |
|------|--------|------------------------|--------------------|---------|--------------------------|----------|------------------------|---------|
| BYORN - Bass Fusion (4:46) | 44.1/16 | 8.9e-8 | - | 3.34 s | GENUINE (0.92) | - | 0 / 22050 | 1.47 s |
| same, MP3 128k | 44.1/16 | 1.0 | mp3 / 130.0 | 3.13 s | TRANSCODED (0.88) | MP3 ~128 kbps | 0.88 / 16500 | 1.33 s |
| Rolf Zuckowski - Stups (2:12) | 44.1/16 | 1.8e-6 | - | 3.05 s | GENUINE (0.91) | - | 0 / 22050 | 0.70 s |
| same, MP3 128k | 44.1/16 | 1.0 | mp3 / 129.7 | 3.02 s | TRANSCODED (1.00) | MP3 ~128 kbps | 1.0 / 16400 | 0.74 s |
| Tones And I - Dance Monkey (3:29) | 48/24 | 3.5e-8 | - | 3.52 s | GENUINE (0.92) | - | 0 / 24000 | 1.42 s |
| same, MP3 128k | 48/16 | 1.0 | mp3 / 127.3 | 3.45 s | TRANSCODED (0.98) | MP3 ~128 kbps | 0.98 / 16500 | 1.40 s |
| beslik - pferdeenergie (2:26) | 44.1/24 | 5.6e-7 | - | 3.00 s | GENUINE (0.92) | - | - | 0.76 s |
| Rolf MP3 128k, upsampled to 96k/24 | 96/24 | 0.99999 | mp3 / 127.3 | - | INCONCLUSIVE (0.1) | - | 0 / 48000 | - |
| Rolf padded 16 to 24-bit | 44.1/24 | 1.8e-6 | - | - | GENUINE, GENUINE_HIRES | - | - | - |
| BYORN mono 30 s clip | 44.1/16/1ch | 4.0e-5 | - | 2.75 s | GENUINE (0.92) | - | - | 0.25 s |
| BYORN 4 s clip (at 60 s) | 44.1/16 | 6.0e-8 | - | 0.17 s | **TRANSCODED (0.85)** | AAC ~256 kbps | 0.06 / 19800 | 0.11 s |
| BYORN 1 s clip | 44.1/16 | error: shorter than 2 s minimum (exit 1) | | | TRANSCODED (0.85) | AAC ~256 kbps | | 0.12 s |
| Billie Eilish - bad guy | 44.1/16/**7.1** | error: 8 channels (exit 1) | | | GENUINE, duration wrong (48.5 s instead of 194 s) | | | 0.90 s |
| 4 s clip of the Rolf MP3 transcode | 44.1/16 | 1.0 | mp3 / 129.7 | | TRANSCODED (1.0) | MP3 ~128 kbps | | |

Both tools separate originals from 128k MP3 transcodes cleanly at 44.1 and 48 kHz. lossprint's bitrate estimate is within 2 kbps.

Example output, lossprint (default threshold):
```json
{"transcode_probability":1.0,"verdict":"transcode","encoder":"mp3","bitrate_kbps":129.7,"path":"b_back.flac"}
{"transcode_probability":0.0000017881393,"verdict":"clean","encoder":null,"bitrate_kbps":null,"path":"b_orig.flac"}
```

Example output, flaccheck (transcode, evidence abbreviated):
```json
{"results":[{"path":"b_back.flac","transcode_verdict":"TRANSCODED","hires_verdict":"GENUINE_HIRES","confidence":1.0,
 "evidence":[
  {"detector":"spectral","signal":"spectral_info_score","value":0.00218,"weight":0.0,"note":"HF content score 0.00"},
  {"detector":"spectral","signal":"cutoff_hz","value":16400.0,"weight":0.2,"note":"detected cutoff 16400 Hz"},
  {"detector":"spectral","signal":"brick_wall","value":1.0,"weight":1.0,"note":"sharp spectral cliff near 16400 Hz"},
  {"detector":"spectral","signal":"rolloff_steepness","value":100.45,"weight":0.8,"note":"rolloff steepness 100.5 dB/oct"},
  {"detector":"spectral","signal":"rolloff_hz","value":5092.6,"weight":0.1,"note":"95% energy rolloff at 5093 Hz"},
  {"detector":"spectral","signal":"edge_hz","value":16602.1,"weight":0.1,"note":"content extends to 16602 Hz"},
  {"detector":"spectral","signal":"codec_guess","value":0.733,"weight":0.3,"note":"MP3 ~128 kbps"},
  {"detector":"spectral","signal":"est_bitrate_kbps","value":128.0,"weight":0.2,"note":"estimated source 128 kbps"},
  {"detector":"spectral","signal":"sbr_mirroring","value":0.629,"weight":0.5,"note":"SBR-like HF mirroring of low band"},
  {"detector":"hires","signal":"genuine_hires","value":1.0,"weight":0.0,"note":"no fake hi-res indicators"},
  {"detector":"artifacts","signal":"noise_floor","value":0.0,"weight":0.6,"note":"digital silent floor above cutoff"},
  {"detector":"artifacts","signal":"pre_echo","value":0.0017,"weight":0.7,"note":"pre-transient smear before attacks"},
  {"detector":"artifacts","signal":"phase_discontinuity","value":0.0005,"weight":0.6,"note":"phase jumps at frame-like boundaries"},
  {"detector":"artifacts","signal":"joint_stereo","value":0.0,"weight":0.5,"note":"mid/side correlation pattern suggestive of joint stereo"}],
 "codec_guess":"MP3 ~128 kbps","est_source_bitrate_kbps":128,"spectral_info_score":0.00218,"mode":"balanced",
 "duration_secs":132.12,"sample_rate":44100,"channels":2,"bits_per_sample":null}],
 "skipped":[],"errors":[]}
```

Mode comparison for flaccheck, as verdict/confidence% (fast / balanced / max): every original came out GENUINE in all three modes (84 to 95%), and every transcode came out TRANSCODED MP3 ~128 in all three (70 to 100%).

## Caveats

- **flaccheck false positive on segments:** a 4 to 20 s stereo excerpt starting at 60 s of the genuine BYORN track came out `TRANSCODED / AAC ~256 kbps`, with `aac_shelf=1.0` and `full_band=1` both set. The whole track came out GENUINE. The verdict depends on which windows the analysis picks, and the AAC-shelf rule overrides `full_band`. Expect some false positives of this kind across a library.
- **flaccheck is blind above 48 kHz and to padded depth on FLAC**, and broken on files with more than 2 channels (see above). lossprint handles 96 kHz (it caught the upsampled MP3) and rejects files with more than 2 channels cleanly.
- **flaccheck `confidence` is not a probability of being lossy**, and its exit code does not show per-file failures.
- **lossprint needs `.flac`/`.wav`/`.aif(f)` extensions, at least 2 s and at most 2 channels.** It exits 1 on any failure, so in a pipeline judge success by parsing stdout and stderr, not by the exit code alone.
- **lossprint memory:** about 435 MB per process, so 4 parallel processes need about 1.8 GB. flaccheck peaks at about 700 MB per process for a 5 min track (whole file decoded to f32). Long files scale linearly, so a 20 min file needs about 3 GB.
- Scratch outputs (JSON and timings) are kept in `scratch/setup/out/`. The transcodes and clips were deleted.
