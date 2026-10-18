# Reproducing the study

`docs/methods.md` explains what each step does and why; this document says how to run it. Commands are run from the
repository root unless stated. There are two paths:

1. **Re-analysis from the published data** ([section 1](#1-re-analysis-from-the-published-data)): recomputes every
   table of `results/analysis/` from the raw detector output in `results/` and the corpus files in `corpus/`. It
   needs Python 3 and no audio.
2. **Re-measurement on another library** ([section 2](#2-re-measurement-on-another-library)): runs the detectors
   again on a library of your own. It needs the audio, the tools and an inventory and job list built to the
   specification below.

## 1. Re-analysis from the published data

### 1.1 Requirements

Python 3.10 or newer, standard library only (3.13.5 was used). No audio, no detector, no container.

### 1.2 Commands

```sh
python3 scripts/analyze.py                  # -> results/analysis/summary.md and the four CSVs; about 1 s
python3 scripts/select_ctl48.py             # -> corpus/jobs_ctl48.jsonl, corpus/set_ctl48.csv
(cd scripts/verify && python3 v1_benchmark.py && python3 v2_clipfree.py)
```

- `analyze.py` overwrites `results/analysis/`. The published outputs were regenerated this way from the published
  corpus (with the reduced `corpus/inventory.jsonl` and the neutral reason strings of [methods 3.1 and
  3.3](methods.md#31-inventory)) and reproduce `results/analysis/` byte for byte:

  | File | sha256 |
  |---|---|
  | `summary.md` | `e04aadb9356efdb58e3ce2eb94b52f8580cc45dff41ba32ce9f6ffb8cfa04d24` |
  | `originals.csv` | `13954ac44bbfe528d2cacb3d9be27112b13300435e0f1209b8284422f7f1c23b` |
  | `variants.csv` | `c49f35cb1b2af206e8a0fe3f89a68633cc84fafe2524f99c13e4eb1023bda60b` |
  | `disagreements.csv` | `16f202b2eaaef3b308a71161bd14b39940e9b139ae6c66958a7a16939568064e` |
  | `reproduction_mismatches.csv` | `2a42167f78fd96c8c04252cbe66f5cdf88a0e22ca771b8421cbe0d7ca0bb513e` |

- `select_ctl48.py` reproduces the 48 kHz control's job list byte for byte (`ctl48: 4 native 48 kHz tier 1, 30 bait
  sources -> 34 jobs`).
- `scripts/verify/` recomputes the headline numbers independently of `analyze.py` (its own loader, flags and Wilson
  intervals) and compares them cell by cell with `summary.md`; `v1_benchmark.py` ends with "all compared cells agree
  with results/analysis/summary.md".

Checks in `summary.md`:

| Line | Expected |
|---|---|
| Completeness | phase 1 2500 of 2500 jobs complete, phase 2 212 of 212, no incomplete or changed jobs |
| Reproduction check | `agree 860`, no mismatch |
| spectrum() threshold sweep | the replay "reproduces the real verdict: 6579 agree, 3 differ" (the 3 are stored as exactly 30.0 dB with an unrounded drop just below 30) |
| Clip-free experiment | self-check "1470 same, 1 differ" |

### 1.3 What the re-analysis cannot redo

| Item | Why |
|---|---|
| Spectrograms (`scripts/spectrograms.py`) | they render the library files |
| The selection itself | it needs the full inventory and the capture record; the published corpus holds its result (tiers, reasons, strata, sets) |
| The stream-capture comparison | it needs the captures and the library copies; `results/capture-check/` holds its outputs |
| The detector runs | they need the audio |

## 2. Re-measurement on another library

### 2.1 Hardware and system

| Resource | Used here | Needed |
|---|---|---|
| CPU | i3-10105F, 4 cores / 8 threads | any x86-64; wall times below scale with cores |
| RAM | 32 GB | about 1 GB per worker (lossprint ~435-470 MB per process, flaccheck up to ~700 MB for a 5 min track, linear in duration) plus headroom; the memory guard stops the run below 2,500 MB available |
| Scratch | NVMe, `scratch/run/` | 8 GiB free at all times (jobs wait below that) plus ~0.5 GB per worker; peak 2.5 GB at 5 workers |
| Results | | ~0.7 GB including spectrograms |
| OS | Debian 13 (trixie) | Linux with Docker; Debian 13 gives the same encoder packages |

### 2.2 Host packages

Versions used (recorded in every `run_start` line):

| Package | Version | Source |
|---|---|---|
| ffmpeg | 7:7.1.5-0+deb13u1 | Debian main |
| flac | 1.5.0+ds-2 | Debian main |
| lame | 3.100-6+b3 | Debian main |
| fdkaac | 1.0.6-0.1 | Debian contrib (needs `libfdk-aac2` from non-free) |
| opus-tools | 0.2-1+b3 (libopus 1.5.2) | Debian main |
| vorbis-tools | 1.4.3-1 | Debian main |
| docker.io | 26.1.5+dfsg1-9+deb13u1 | Debian main |
| python3 | 3.13.5 | Debian main |

On Debian 13 with `contrib` and `non-free` enabled:

```sh
sudo apt install ffmpeg flac lame fdkaac opus-tools vorbis-tools docker.io python3
```

To pin exact versions, append `=<version>` from the table. `scripts/run.py` reads the versions with `dpkg-query`
(`run.py:89-90`); on a system without dpkg that field is empty and the run still works.

The host Python needs no third-party packages for the run and the analysis. `align_diff.py` (stream-capture check
only) needs numpy and scipy; use a throwaway environment, for example
`uv run --no-project --with numpy --with scipy python -I scripts/align_diff.py …` (numpy 2.5.4 and scipy 1.18.1 were
used).

### 2.3 lossprint 1.1.0

```sh
curl https://sh.rustup.rs -sSf | sh          # if no Rust toolchain; rustc 1.99.0 was used
cargo install lossprint --version 1.1.0 --locked --features cli --root "$PWD"
bin/lossprint --version                       # lossprint 1.1.0
```

`--features cli` is required for the binary. sha256 of the binary used:
`c240754cacb6fb93008c5af4d4adf1cae0397822382c15f3dd0daa57cd0be993` (a rebuild with another rustc may differ
bitwise without changing results). Tool behaviour and output format: `TOOLS.md`.

### 2.4 flaccheck 0.1.2

```sh
git clone https://github.com/dasunNimantha/flaccheck.git tools/flaccheck
git -C tools/flaccheck checkout v0.1.2
git -C tools/flaccheck rev-parse HEAD        # c05e68526973efce9dc32423b2e1dd9cc5274857
cargo build --release -p flaccheck --manifest-path tools/flaccheck/Cargo.toml
cp tools/flaccheck/target/release/flaccheck bin/
bin/flaccheck --version                       # flaccheck 0.1.2
```

Default features only (no `--features ml`). sha256 of the binary used:
`4836e2114e12510b011f801483093d74c46f1986b64807237af0a79842631d0b`. The exact build command of that binary was
not recorded; the cargo fingerprints show a release build with default features.

### 2.5 Echolot image (spectrum check)

The spectrum check runs as Echolot's own code in an image of the commit that was measured:

```sh
git clone https://github.com/Zweisteinium/echolot.git && git -C echolot checkout e9f0bf9
docker build -t echolot:bench-e9f0bf9 echolot
```

Set `IMAGE = "echolot:bench-e9f0bf9"` in `scripts/run.py:40` (`clipfree.py` uses the same constant). The image
measured had the id `sha256:eff56d10aed8b942feb9b73b9350ad2c168ae9b8f63130882adce1699131183c`. The Dockerfile pins
ffmpeg 7.1.5 by checksum and the Python packages by `uv.lock` (numpy 2.5.3, mutagen 1.48.1), but its base images
(`python:3.13-slim`, `ghcr.io/astral-sh/uv:0.9`) are moving tags, so the Python patch level can differ (3.13.16 was
used) and the image id will differ. The image needs `nice` and `ionice` (present). Check:

```sh
docker run --rm --network none --entrypoint python echolot:bench-e9f0bf9 \
  -c "import numpy, mutagen, sys; print(sys.version.split()[0], numpy.__version__, mutagen.version_string)"
```

Expected: `3.13.16 2.5.3 1.48.1`.

### 2.6 What was specific to the original setup

| Item | Where | What to do for another library |
|---|---|---|
| Library path | `LIB` in `run.py:35`, `spectrograms.py:17`, `audio_md5.py:5`, set by the environment variable `LOSSY_BENCH_LIB` | the library's track directory (an absolute path); job paths are relative to it. The spectrum container mounts `LIB.parent` read-only at the same path (`run.py:107`), so `LIB` must have a parent that can be mounted |
| Container library path `/music/tracks` | `check_integrity.py:19` | mount the track directory there, or edit the constant |
| Repository path `~/dev/lossy-bench` | `chain.sh:3`, `after_chain.sh:3`, `memguard.sh:3` | the clone's location |
| Spectrum image tag | `run.py:40` | see 2.5 |
| Inventory from the library manager's database | `corpus/inventory.jsonl` | build one to the specification in 2.7 |
| Provenance tiers from tags, vendor string, import record and capture record | [methods 3.3-3.4](methods.md#33-provenance-tiers) | define tiers that fit the library's sources (2.8) |
| Integrity evidence from a maintenance re-encode pass and a partial damage scan | `corpus/evidence/` | not reproducible from this repository; use `check_integrity.py` on every file (2.10) |
| Stream captures (tier 2, bits24_fade, the capture check) | `corpus/evidence/capture_*`, `results/capture-check/` | only with captures of your own; otherwise no tier 2 |
| Stored spectrum verdicts (labels for `spectrum_mark` and the reproduction check) | `quality`, `lossy_sourced`, `filed.ts` in the inventory; `REPRO_SINCE` in `analyze.py:29`; `chain.sh:7-11` | only meaningful where the library manager stores the spectrum check's verdicts. Elsewhere set `spectrum_mark` empty and `filed` null: the check then compares 0 files and reports 0 mismatches, and `chain.sh` proceeds. `REPRO_SINCE` must be the time from which the stored verdicts come from the measured code |
| Set sizes and caps | [methods 3.7](methods.md#37-deterministic-selection); `chain.sh:11` (`2500`) | scale to the library; `chain.sh` must expect the new set-A size |
| Pausing the library manager's background jobs | | anything that renames, retags or replaces library files must be stopped during the run |

### 2.7 Inventory: required content

`corpus/inventory.jsonl`, one JSON object per line, keyed by `path`. The public scripts read:

| Field | Type | Read by | Used for |
|---|---|---|---|
| `path` | path relative to `LIB` | `analyze.py`, `select_ctl48.py` | identity |
| `quality` | string; `"fake"` if the stored spectrum verdict is lossy | `analyze.py:158` | reproduction check |
| `lossy_sourced` | any; truthy if the library marks the file as made from lossy | `analyze.py:158` | reproduction check |
| `filed` | `{"ts": "YYYY-MM-DDTHH:MM:SS"}` (import time) or null | `analyze.py:155` | which files enter the reproduction check (`ts ≥ REPRO_SINCE`) |
| `tags` | object; any value containing `youtube.com` or `youtu.be` marks a YouTube URL in the file's own tags | `analyze.py:115-119`, `select_ctl48.py:23-25` | YouTube group, 48 kHz control |

For the selection, the inventory also needs what the tier, stratum and exclusion rules read ([methods
3.1](methods.md#31-inventory)): size, mtime, duration, header facts (bits per sample, rate, channels, total samples,
STREAMINFO MD5 set, vendor), the tags of methods 3.3 and 3.5, and whatever provenance record the library has.

### 2.8 Tiers and selection

The selection script is not part of this repository; [methods 3.3-3.7](methods.md#33-provenance-tiers) specify the
tier rules, strata, exclusions, caps, order key and `pick()` algorithm completely enough to reimplement them. For
another library, replace the tier rules with provenance rules that fit its sources and keep three properties of the
design:

- the rules use provenance and integrity only, never a detector's output;
- the reasons are stored per file;
- the order is a hash of the path (`sha256(path).hexdigest()`), so the selection is deterministic and free of judgement.

The analysis reads two sub-tier names: `"1"` and `"2_proven"` form the most trusted group of the lossprint sweep
(`analyze.py:426`), and `select_ctl48.py:31` takes native 48 kHz sources of sub-tier `"1"`. Map your most trusted
provenance to these names or edit those lines.

### 2.9 Job list: required content

`corpus/jobs.jsonl`: one object per set-A source file, in run order. Fields:

| Field | Read by | Notes |
|---|---|---|
| `path` | all | relative to `LIB` |
| `size`, `mtime` | `run.py:398`, `:418`; `clipfree.py:103` | the live-library guard; must equal `os.stat()` (`int(st_mtime)`) at run time |
| `rate`, `samples`, `channels`, `bps` | `run.py:188`, `:204`, `:278`; `analyze.py` | expected sample counts, WAV depth, pooling (`rate == 44100`) |
| `sets` | `run.py:253-304`, `:452-453`; `analyze.py`; `clipfree.py:88`, `:91` | subset of `A`, `B`, `bait`, `processed`; every job is in `A`. `processed` requires `B` (its variants reuse B's `mp3_320` encode). Bait and processed sources must be 44.1 kHz: the pooled tables count only 44.1 kHz sources (`analyze.py:220`) |
| `tier`, `subtier`, `strata` | `analyze.py`, `select_ctl48.py` | analysis groups |
| `spectrum_mark` | `analyze.py:186`, `:208` | non-empty string if the stored spectrum verdict is lossy (reported apart); empty otherwise |

Phase 3 reads `corpus/jobs_ctl48.jsonl` from `select_ctl48.py`, which derives it from `jobs.jsonl` and the inventory.

### 2.10 Integrity evidence

Every file in the sets needs evidence that its audio decodes completely and correctly ([methods
3.2](methods.md#32-integrity-evidence)). Without an earlier re-encode pass, check every inventory file with
`check_integrity.py`. It needs Echolot's `audio` module, so it runs in the image of 2.5, with the track directory
mounted where the script expects it (`check_integrity.py:19`) and the paths on stdin:

```sh
python3 -c "import json; [print(json.loads(l)['path']) for l in open('corpus/inventory.jsonl')]" \
  > corpus/evidence/to_check.txt
docker run --rm -i --network none -v /path/to/tracks:/music/tracks:ro -v "$PWD/scripts:/bench:ro" \
  --entrypoint nice echolot:bench-e9f0bf9 -n 19 ionice -c3 python /bench/check_integrity.py \
  < corpus/evidence/to_check.txt > corpus/evidence/integrity_check.tsv
```

Output: `result <TAB> size <TAB> path` per file; `ok` or the reason. The invocation in the script's docstring
(`check_integrity.py:6`) does not work, because stdin must carry the paths. Runtime: two full decodes per file (276
files took about 2 minutes here). A file counts as verified only while its size equals the size in this output.

### 2.11 Pilot run

Pick a handful of set-A paths that cover special cases (non-ASCII and special characters, 24-bit, 48 kHz, the most
trusted tier, a spectrum-marked file) and run them into separate files:

```sh
python3 scripts/run.py --phase 1 --workers 3 --lp-threads 1 --only pilot_p1.txt --out results/pilot_phase1.jsonl
python3 scripts/run.py --phase 2 --workers 3 --lp-threads 2 --only pilot_p2.txt --out results/pilot_phase2.jsonl
```

`--only` takes one path per line; every path must be a job of that phase. Check: every job has a `job_done` line
with `ok: true`; every variant has a `meta` line, and every `ok` variant has one `spectrum`, `lossprint` and
`flaccheck` line; no `job_error`. Compare a few values with manual calls of the tools (`TOOLS.md`, "Recommended
invocations"). Check the sample-count deltas in the `meta` lines against the tolerances ([methods
5.4](methods.md#54-checks-and-sample-count-tolerances)) before the main run; do not widen them afterwards. Here, 6
phase-2 sources (121 variants) took about 6 minutes.

### 2.12 The run

Stop everything that writes to the library. Then start, detached:

```sh
rm -f results/STOP
setsid nohup python3 scripts/run.py --phase 1 --workers 5 --lp-threads 1 > results/phase1.log 2>&1 < /dev/null &
setsid nohup scripts/memguard.sh > results/memguard.log 2>&1 < /dev/null &
setsid nohup scripts/chain.sh > results/chain.log 2>&1 < /dev/null &
setsid nohup scripts/after_chain.sh > results/after_chain.log 2>&1 < /dev/null &
```

`chain.sh` waits for phase 1, runs `analyze.py --partial`, and starts phase 2 and then phase 3 (both
`--workers 5 --lp-threads 2`) only if the reproduction check has 0 mismatches and phase 1 has 2,500 complete jobs
(`chain.sh:11`; adapt it to your set-A size). `after_chain.sh` then runs the clip-free experiment with 4 workers.
Stop gracefully with `touch results/STOP` (running jobs finish); resume by starting the same command again (jobs
with a `job_done` line are skipped). Progress: `results/progress_phase<N>.json`.

Measured on the host above (all tool calls at nice 19 / idle I/O, other services running):

| Step | Work | Workers | Wall time | Output lines |
|---|---|---|---|---|
| Phase 1 | 2,500 originals | 5 | 81 min | `phase1.jsonl` 12,501 |
| Phase 2 | 212 sources, 4,266 variants | 5 | 3 h 08 min | `phase2.jsonl` 17,115 |
| Phase 3 | 34 sources, 68 variants | 5 | 3 min | `phase3.jsonl` 307 |
| Clip-free | 1,111 originals + 60 × 6 variants | 4 | 13 min | `clipfree.jsonl` 1,471 |

Median job: 9.6 s (phase 1), 263 s (phase 2, max 577 s), 24 s (phase 3). Expected completeness: every job complete,
0 changed files, and in phase 2 only rejected variant `meta` lines from the two ffmpeg length behaviours of [methods
5.4](methods.md#54-checks-and-sample-count-tolerances) (54 here); phases 1 and 3: 0 failed lines.

### 2.13 Analysis and spectrograms

```sh
python3 scripts/analyze.py                      # -> results/analysis/summary.md and CSVs; seconds
setsid nohup python3 scripts/spectrograms.py --workers 1 > results/spectrograms.log 2>&1 < /dev/null &
```

`spectrograms.py` renders one PNG per row of `results/analysis/disagreements.csv` (397 here, 29 min with one
worker, ~535 MB), so it runs after `analyze.py`. `analyze.py` reads `clipfree.jsonl` if present. `scripts/verify/` (as in 1.2) recomputes the
new `summary.md` from the new raw data; it has its own copy of `REPRO_SINCE` (`v1_benchmark.py:75`), which must match
`analyze.py:29`.

### 2.14 Stream-capture check (optional)

Needs bit-exact captures of the official lossless stream for the songs in question, verified by decoded-audio MD5
(`ffmpeg -v error -i F -map 0:a -c:a pcm_s32le -f md5 -`), and the library copies. `align_diff.py` handles 44.1 kHz
stereo files only (`align_diff.py:17`, `:20`, `:47`).

1. Build `compare.json`, a JSON list with `song`, `rec` (capture path), `lib` (library path), `rec_info` and
   `lib_info` (ffprobe stream fields; `align_diff.py` reads `bits_per_raw_sample`):

   ```sh
   python3 - <<'EOF' > compare.json
   import json, subprocess
   pairs = [("Artist - Title", "/path/to/captures/Artist - Title.flac", "/path/to/tracks/Artist/Artist - Title.flac")]
   def info(p):
       out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                             "stream=sample_rate,bits_per_raw_sample,duration_ts,duration", "-of", "json", p],
                            capture_output=True, check=True).stdout
       return json.loads(out)["streams"][0]
   print(json.dumps([{"song": s, "rec": r, "lib": l, "rec_info": info(r), "lib_info": info(l)} for s, r, l in pairs]))
   EOF
   ```

2. Align and compare (seconds per song):

   ```sh
   nice -n 19 uv run --no-project --with numpy --with scipy python -I scripts/align_diff.py compare.json > align.jsonl
   ```

3. Detectors on the captures, as in the main run: lossprint with `bin/lossprint -j 1 -t 0 -o jsonl -- FILE...`, and
   the spectrum check through `spectrum_worker.py` in the image of 2.5:

   ```sh
   ls /path/to/captures/*.flac \
     | python3 -c "import json, sys; [print(json.dumps({'id': i, 'path': l.strip()})) for i, l in enumerate(sys.stdin)]" \
     | docker run --rm -i --network none -v /path/to/captures:/path/to/captures:ro -v "$PWD/scripts:/bench:ro" \
         --entrypoint python echolot:bench-e9f0bf9 -u /bench/spectrum_worker.py
   ```

   The published `recs_scan.jsonl` came from a scan wrapper in an image of a later Echolot commit with identical
   spectrum code and the upstream lossprint 1.1 release binary ([methods 10](methods.md#10-stream-capture-ground-truth-check));
   the spectrum code is the same, and lossprint is the same version in a different build.

4. The drift and per-band residual check for songs that are not the same audio has no script; [methods
   10](methods.md#10-stream-capture-ground-truth-check) gives its windows, bands and Welch parameters.

## 3. Reproducibility risks

| Risk | Effect | Mitigation |
|---|---|---|
| `IMAGE` in `run.py:40` is a tag | a re-run measures whatever image carries it | build e9f0bf9 under its own tag (2.5); compare `run_start` |
| The library is live | files renamed or replaced after the job list was made are skipped as `changed_before_run` | stop all writers; rebuild the job list right before the run |
| Inputs not reproducible from this repository | the re-encode pass, the damage scan, the capture record and low-bit list, and the full inventory were made outside it | the files that are published hold their results; regenerating them needs your own equivalents |
| Hard-coded paths | see 2.6 | edit before running |
| Base images and toolchains | `python:3.13-slim`, `uv:0.9`, rustc versions move | record `run_start`; compare with [methods 12](methods.md#12-computing-environment) |
| Encoder determinism | assumed, not verified bitwise across runs (libopus, libvorbis, LAME and FDK are deterministic for a fixed build and input) | compare `meta.out.encoded_bytes` with the recorded run |
| Thread scheduling | the order of lines in `phase*.jsonl` differs between runs | the analysis keys by (path, variant); results do not depend on order |
| `chain.sh` expects 2,500 jobs | phase 2 never starts for another set size | edit `chain.sh:11` |
| Script docstrings | `run.py:16` and `analyze.py:2` name phases 1 and 2 only; `check_integrity.py:6` gives an invocation that cannot work | the code accepts phase 3 (`run.py:440`) and reads it (`analyze.py:133`); use the invocation of 2.10 |
