# Other tools

What else exists for detecting lossy-sourced ("fake", transcoded, upsampled) lossless audio, why it was not part of
this benchmark, and the short test of FLAC Detective. The survey was made in October 2026 from the cited pages;
statements marked *(unverified)* could not be confirmed from a primary source. Benchmark results:
[results.md](results.md); detectors under test: [methods.md](methods.md#2-detectors-under-test),
[TOOLS.md](../TOOLS.md).

## Contents

1. [Summary](#1-summary)
2. [Tools](#2-tools)
3. [Research](#3-research)
4. [Why the other tools are not in the benchmark](#4-why-the-other-tools-are-not-in-the-benchmark)
5. [FLAC Detective 2.5.0: short test](#5-flac-detective-250-short-test)

## 1. Summary

"Batch + JSON" means it runs headless on Linux over many files and writes machine-readable output with a per-file
score or verdict.

| Tool | Method | Platform / licence | Batch + JSON | Status (October 2026) | In benchmark? / why not |
|---|---|---|---|---|---|
| Echolot spectrum check | lowpass-edge search plus a frame-to-frame "flicker" test | Python, part of [Echolot](https://github.com/Zweisteinium/echolot), AGPL-3.0 | as a library call | maintained | **yes** |
| [lossprint](https://github.com/maxdjohnson/lossprint) 1.1.0 | CRNN on mid/side spectrograms | Rust, MIT; Linux, macOS, Windows | yes (JSONL) | 1.1.0 of 2026-09-03 | **yes** |
| [flaccheck](https://github.com/dasunNimantha/flaccheck) 0.1.2 | cutoff, MDCT-residual and artefact rules, fused; optional ONNX model | Rust, MIT; built from source | yes (JSON, CSV) | active repo; v0.1.2 latest tag | **yes** |
| [FLAC Detective](https://github.com/Guillain-RDCDE/FLAC_Detective) 2.5.0 | spectral rules, MDCT grid, CNN (PyTorch) | Python ≥ 3.10, MIT; pip | yes (JSON, CSV) | very active | short test only ([section 5](#5-flac-detective-250-short-test)) |
| [fakeflac](https://github.com/mevdschee/fakeflac) | cutoff in the averaged spectrum of the first 30 s | Python + ffmpeg, MIT | prints one 0–100 score, no JSON | last push 2022 | cutoff only; no structured output |
| [fakeflac-go](https://github.com/drichline/fakeflac-go) 0.1.5 | port of fakeflac | Go, GPL-3.0; binaries, container | batch; 0–100 score on the terminal, JSON not documented | new (created September 2026) | cutoff only; README states false negatives |
| [penthy](https://github.com/gioypi/penthy) | CNN on 16.2–22 kHz spectrogram images, MP3 only | Python, MIT | directory script, float score | discontinued | unmaintained; MP3 only |
| [FakeFLac Lossless audio checker](https://github.com/Haki-22/FakeFLac-Lossless-audio-checker) | visual spectrogram comparison | Python/Kivy, GPL-3.0; Windows .exe | no (GUI) | last push 2023 | GUI only, no verdict |
| [auCDtect](https://tta.sourceforge.net/en/true-audio-checker-downloads/) 0.8.3 / Tau Analyzer 1.2 | spectral statistics for MPEG artefacts | freeware, closed source *(unverified)*; console Windows/Linux, GUI Windows | console text, no JSON | unmaintained *(unverified)* | 16/44.1 WAV only; closed; no structured output |
| Lossless Audio Checker (LAC) 2.0.7 | upsampling and upscaling detection; AAC-only transcode detection | freeware; Windows GUI, console builds *(unverified)* | text | no longer distributed | not obtainable; transcode detection AAC only |
| [Fakin' The Funk](https://www.fakinthefunk.net/en/) | cutoff and estimated bitrate; header vs frame length | commercial (free tier: 100 results); Windows, macOS; Linux via PlayOnLinux | GUI batch; CLI and JSON not documented | unknown | closed, paid, GUI only |
| [spek](https://github.com/alexkay/spek) 0.8.5 | spectrogram viewer | C++, GPL-3.0; Linux, Windows, macOS | no | 0.8.5 of January 2023 | viewer, no verdict |
| [redoflacs](https://github.com/sirjaren/redoflacs) | Bash wrapper around auCDtect or LAC, SoX spectrograms | Bash, MIT; Linux/BSD | log file | last push April 2025 | wrapper, adds no detector |
| VerifAI Audio, Spectro | web service (AI-based); macOS app (FFT classifier) | closed | no *(unverified)* | unknown | closed; no headless batch use |

## 2. Tools

### 2.1 Benchmarked

- **Echolot spectrum check** (`spectrum()` / `_flicker()`): finds the steepest edge from 12 kHz up; a drop of
  ≥ 30 dB below 20.4 kHz counts as lossy, from 19 kHz up only if the bins below the edge flicker. Details:
  [methods.md 2.1](methods.md#21-echolot-spectrum-check).
- **lossprint**: a 1.4M-parameter CRNN over long and short mid/side log spectrograms at the native rate. It reports
  P(transcode), an encoder family (MP3, AAC, Vorbis, Opus, WMA, MP2, Musepack) and a bitrate estimate. The model card
  reports training on 22,250 tracks from 11,004 releases and 0.24% false positives (6 / 2,469) on untouched masters
  ([model card](https://app.alphaneural.io/assets/maxdj/lossprint)). Published on
  [crates.io](https://crates.io/crates/lossprint) in August 2026; 1.1.0 is of 2026-09-03.
- **flaccheck**: tiered DSP detectors (cutoff and brick wall, MDCT quantisation residual, pre-echo, phase and
  joint-stereo artefacts, fake hi-res), fused into GENUINE / SUSPICIOUS / TRANSCODED / INCONCLUSIVE. An optional
  ONNX model for borderline files needs `--features ml`; the benchmark build had no ML. Also offers a local web UI
  ([README](https://github.com/dasunNimantha/flaccheck)). Repository created July 2026.

### 2.2 Command-line tools and libraries

- **FLAC Detective** (Guillain d'Erceville): verdicts AUTHENTIC / WARNING / SUSPICIOUS / FAKE_CERTAIN from numbered
  rules (cutoff, MP3 bitrate signature, cassette hiss, MDCT grid, band replication) plus a CNN rule from the `[ml]`
  extra (PyTorch, librosa). The README states that "a conviction needs two of them to agree". Output text, JSON,
  CSV or HTML; resumable scans; extras for beets and a PySide6 GUI. Options include `--deep` (CNN on every file) and
  `--repair-in-place` (replaces undecodable FLACs, off by default). By default it asks PyPI for updates once a day.
  [PyPI](https://pypi.org/project/flac-detective/) lists releases from 0.6.0 (December 2025) to 2.5.0 (October
  2026), with five minor releases (2.1.0–2.5.0) within eight days.
- **fakeflac** (Maurits van der Schee, 2013): averages the spectra of the first 30 s, sweeps down from Nyquist for the
  cutoff and prints the share of the spectrum below it as 0–100
  ([doc](https://github.com/mevdschee/fakeflac/blob/master/doc/index.md)).
- **fakeflac-go**: a Go port of fakeflac with batch processing, an embedded WASM ffmpeg and optional plots; its README
  warns that the algorithm gives false negatives ([README](https://github.com/drichline/fakeflac-go)). One star,
  created September 2026.
- **penthy**: a CNN on 128 × 128 spectrogram images of 16.2–22 kHz, trained on genuine FLACs and MP3 transcodes;
  about 90% accuracy by its README, which also says 320 kbps MP3 can fool it. Marked discontinued; needs old Python
  package versions ([README](https://github.com/gioypi/penthy)).

### 2.3 GUI and closed tools

- **auCDtect / Tau Analyzer** (Tau Software): auCDtect is a console program that judges whether a 16-bit/44.1 kHz
  WAV from a CD is original or "reconstructed" from MPEG audio, from statistics of the Fourier spectra; verdicts
  CDDA / MPEG / unknown. The developers report 1,187 / 1,284 CD tracks and 2,665 / 2,682 MP3-derived tracks
  correct ([testing results](https://tta.sourceforge.net/en/true-audio-checker-testing-results/), self-reported).
  Distribution page: 0.8.3 console for Windows and Linux, Tau Analyzer 1.2 GUI for Windows, both freeware
  ([page](https://tta.sourceforge.net/en/true-audio-checker-downloads/)). No source code is linked.
- **Lossless Audio Checker (LAC)** (Julien Lacroix, Yann Prime): implements the AES paper in [section 3](#3-research):
  upsampling, upscaling, and transcoding from AAC only. Its authors answered a report that it missed MP3 transcodes
  by calling MP3 detection a misuse of the application
  ([Hydrogenaudio thread](https://hydrogenaudio.org/index.php/topic,115787.0.html)) *(unverified: from search
  results, the thread could not be opened)*. Last packaged version 2.0.7, May 2019
  ([Chocolatey](https://community.chocolatey.org/packages/lossless-audio-checker)). As of 2024 the software is no
  longer available and its site redirects elsewhere
  ([The Well-Tempered Computer](https://thewelltemperedcomputer.com/SW/AudioTools/Detect.htm)). redoflacs can call
  a `LAC` binary on Linux, which suggests a Linux console build existed *(unverified)*.
- **Fakin' The Funk** (udse): batch GUI for DJs. It finds the cutoff, estimates the real bitrate and flags files
  whose header length does not match the scanned frames; the vendor calls the analysis "very defensive" but says
  false positives are possible. Free version shows up to 100 fake results; Windows and macOS, Linux only through
  PlayOnLinux ([site](https://www.fakinthefunk.net/en/)). No command line or export format is documented.
- **VerifAI Audio** (web, AI-based) mislabelled a 1986 lossless recording as lossy in one author's test
  ([The Well-Tempered Computer](https://thewelltemperedcomputer.com/SW/AudioTools/Detect.htm)). **Spectro** is a
  commercial macOS app with an FFT classifier (Lossless / Lossy / Fake Lossless) *(unverified: from search results
  only)*.

### 2.4 Viewers and wrappers

- **spek**: spectrogram viewer on FFmpeg and wxWidgets, GPL-3.0, 0.8.5 of January 2023
  ([repo](https://github.com/alexkay/spek)). It shows a cutoff; a person decides.
- **SoX** `spectrogram` renders spectrogram PNGs headless; it is used this way by redoflacs. No verdict.
- **redoflacs**: parallel Bash FLAC maintenance tool; its authenticity mode runs auCDtect or LAC and logs suspects,
  optionally with SoX spectrograms ([README](https://github.com/sirjaren/redoflacs)).

## 3. Research

| Work | Method | Scope | Code |
|---|---|---|---|
| Herre, Schug, "Analysis of decompressed audio – the inverse decoder", AES 109th Convention, 2000, preprint 5256 ([record](https://cris.fau.de/publications/111898424)) | recover coder parameters from decoded PCM | AAC | no |
| Moehrs, Herre, Geiger, "Analyzing decompressed audio with the 'inverse decoder' – towards an operative algorithm", AES 112th Convention, 2002, preprint 5576 ([record](https://cris.fau.de/publications/106519864)) | first working inverse decoder | MP3 | no |
| D'Alessandro, Shi, "MP3 bit rate quality detection through frequency spectrum analysis", ACM MM&Sec 2009 ([record](https://digitalcommons.njit.edu/fac_pubs/11841)) | high-band spectrum features, SVM; reports 97% over 5 MP3 classes | MP3 → MP3 | no |
| Yang, Shi, Huang, "Detecting double compression of audio signal", SPIE 7541, 2010 ([record](https://researchwith.njit.edu/en/publications/detecting-double-compression-of-audio-signal/)) | first-digit statistics of quantised MDCT coefficients, SVM | MP3 → MP3 | no |
| Bianchi et al., EURASIP J. Information Security, 2014 ([pdf](https://jis-eurasipjournals.springeropen.com/track/pdf/10.1186/1687-417X-2014-10)) | single vs double MP3 compression, first bitrate | MP3 → MP3 | no |
| Lacroix, Prime, Remy, Derrien, "Lossless Audio Checker: a software for the detection of upscaling, upsampling, and transcoding in lossless musical tracks", AES 139th Convention, 2015, paper 9416 ([record](https://aes2.org/publications/elibrary-page/?id=17972)) | reports 100% for upscaling and transcoding, 91.3% for upsampling | AAC transcodes | LAC (above) |
| Seichter, Cuccovillo, Aichroth, "AAC encoding detection and bitrate estimation using a convolutional neural network", ICASSP 2016 ([pdf](https://www.tu-ilmenau.de/fileadmin/Bereiche/IA/neurob/Publikationen/conferences_int/2016/Seichter-ICASSP-2016.pdf)) | CNN on decoded PCM, 8 bitrate classes, 94.65% on 116 ms | AAC | not found |
| Hennequin et al., "Codec independent lossy audio compression detection", ICASSP 2017 ([summary](https://newsroom-deezer.com/2017/04/codec-independent-lossy-audio-compression-detection/)) | CNN on spectrograms, several codecs and bitrates | lossy → PCM | not found |
| Derrien, "Detection of genuine lossless audio files: application to the MPEG-AAC codec", JAES 67(3), 2019 ([record](https://aes2.org/publications/elibrary-page/?id=19892)) | quantisation errors in the time-frequency domain, no ML; null false positives on 1,576 files | AAC (iTunes) | not found |
| Koops, Micchi, Quinton, "Robust lossy audio compression identification", ISMIR 2024 ([arXiv:2407.21545](https://arxiv.org/abs/2407.21545)) | CNN; a model like prior work fails on unseen codec settings; random spectrogram masks fix part of it | lossy → PCM | not stated |

The forensics line (2000–2014) works on MP3 or AAC and mostly asks whether an MP3 was compressed twice; none of it
ships a tool for FLAC. The two lossless-specific works (Lacroix 2015, Derrien 2019) cover AAC. Koops et al. show
the risk the benchmark also found: a learned detector can lean on the cutoff it saw in training.

## 4. Why the other tools are not in the benchmark

**From the study's planning notes.** The detector set was fixed when the study was planned: Echolot's spectrum check
"compared with two open-source detectors", lossprint 1.1.0 and flaccheck 0.1.2, with the raw scores of each recorded
(lossprint's P(transcode), flaccheck's JSON evidence). The notes name no other candidate and give no reason for
leaving any tool out. The only tool tried later was FLAC Detective ([section 5](#5-flac-detective-250-short-test)).

**From this survey** (not stated in the notes). The run needed a detector that runs headless on a Linux server, in
batch over thousands of files, and writes a raw per-file score. Measured against that:

| Tool | Reason it does not fit |
|---|---|
| fakeflac, fakeflac-go | cutoff search only, which the spectrum check already covers in more detail; plain score on the terminal |
| penthy | discontinued; MP3 only; old dependencies |
| FakeFLac Lossless audio checker, spek, Tau Analyzer | GUI or viewer; no verdict or no batch output |
| auCDtect | closed source *(unverified)*; 16/44.1 WAV only, so FLACs and 24-bit or 48 kHz files would need converting; text output |
| Lossless Audio Checker | no longer distributed; transcode detection for AAC only |
| Fakin' The Funk | closed, paid; GUI; no Linux build; no documented machine-readable output |
| redoflacs | wrapper around auCDtect or LAC, no detector of its own |
| VerifAI Audio, Spectro | closed web service or macOS app; no headless batch use |
| Research methods | no released code for FLAC input |

## 5. FLAC Detective 2.5.0: short test

A short test after the main run, kept under 15 minutes by design. Data: one JSON line per file and mode with FLAC
Detective's full result object and the resource use of each call.

### 5.1 Setup

- FLAC Detective 2.5.0 from PyPI with the `[ml]` extra (torch 2.14.1+cpu, model `cnn_v4_stereo`), in a Python 3.13
  venv (1.2 GB on disk).
- Run in a throwaway container: library read-only, no network (`--no-update-check`), `nice -n 19`, `ionice -c3`.
- Invocation: `flac-detective --no-update-check --workers 1 --format json --output FILE --work-dir DIR [--deep] FILE...`,
  several files per call, up to 4 calls in parallel. `--repair-in-place` was never passed.
- Two modes: default (the `[ml]` rule runs only on files the heuristics leave in doubt) and `--deep` (the CNN on
  every file).
- A file counts as flagged when the verdict is SUSPICIOUS or FAKE_CERTAIN. WARNING is reported apart.
- lossprint and spectrum values for the same files come from the benchmark (variants are made deterministically).

Files:

| Part | Originals | Variants |
|---|---|---|
| Dry run of a full-corpus harness | 7 set-A originals | all 23 variants (18 transcodes, 2 processed, 3 bait) of 2 tier-1 set-B sources at 44.1 kHz; 44 files |
| Short test | 29 set-A originals in 4 groups (table 5.3) | 6 encodings that spectrum often misses (MP3 V0, LAME 320, AAC 256, FDK-AAC 256, Opus 160, Vorbis q6) and bait via 32 and 38 kHz, of 8 set-B sources at 44.1 kHz without an Echolot mark; 64 files |

### 5.2 Variants

Flagged / n. Short test, 8 sources:

| Variant | FLAC Detective (default) | FLAC Detective `--deep` | lossprint (p ≥ 0.5) | spectrum |
|---|---|---|---|---|
| MP3 V0 (ffmpeg) | 0/8 | 0/8 | 8/8 | 1/8 |
| LAME 320 | 0/8 | 0/8 | 8/8 | 6/8 |
| AAC 256 (ffmpeg) | 7/8 | 7/8 | 8/8 | 0/8 |
| FDK-AAC 256 | 7/8 | 7/8 | 8/8 | 8/8 |
| Opus 160 | 7/8 | 7/8 | 8/8 | 1/8 |
| Vorbis q6 | 7/8 | 7/8 | 8/8 | 1/8 |
| bait 32 kHz (genuine) | 6/8 | 6/8 | 0/6 | 6/6 |
| bait 38 kHz (genuine) | 4/8 | 4/8 | 0/6 | 6/6 |

Two of the 8 sources are not in the benchmark's bait set, so their bait has no lossprint or spectrum score (n = 6).
No variant got WARNING.

Dry run, 2 sources, by codec family (default and `--deep` identical):

| Family | FLAC Detective | lossprint | spectrum |
|---|---|---|---|
| MP3: 128, 192, 320, V2, V0 (ffmpeg), LAME 320 and V0, 320 −1.3 dB, 320 at 48 kHz | 1/18 (only one MP3 128) | 18/18 | 7/18 |
| AAC: ffmpeg 128 and 256, FDK 256 and VBR 5 | 8/8 | 8/8 | 5/8 |
| Opus: 96, 160, opusenc 160 | 6/6 | 6/6 | 0/6 |
| Vorbis: q3, q6, q9, oggenc q6 | 8/8 | 8/8 | 0/8 |
| bait 32 / 38 / 40 kHz (genuine) | 1/2, 2/2, 1/2 | 0/6 | 5/6 |

Pooled over both parts: MP3 transcodes 1 / 34 flagged, AAC, Opus and Vorbis transcodes 50 / 54, genuine bait
14 / 22.

### 5.3 Originals (short test, default mode)

| Group | n | Flagged | WARNING | Notes |
|---|---|---|---|---|
| Genuine controls: 5 hash-proven stream captures (tier 2_proven), 1 store-tagged; flaccheck flagged 5 | 6 | 0 | 0 | lossprint 0 / 6 |
| Likely fakes that spectrum passes (lossprint p ≥ 0.5 on 9) | 10 | 6 | 0 | the 6: 4 at 48 kHz that lossprint calls Opus, 2 it calls AAC; all 6 cite FLAC Detective's MDCT evidence. The 3 that lossprint calls MP3: AUTHENTIC |
| lossprint p ≥ 0.5 without a visible lowpass | 5 | 2 | 0 | both lossprint calls Vorbis; MDCT evidence |
| Echolot-marked, lossprint p < 0.5 (disputed) | 8 | 2 | 2 | one FAKE_CERTAIN with a 16.25 kHz edge (flaccheck also TRANSCODED) |

Dry run: all 7 originals AUTHENTIC in both modes, including 2 Echolot-marked ones (lossprint 1.000 at 48 kHz and
0.667).

### 5.4 Cost

| | Files | CPU per file | Peak RSS per process |
|---|---|---|---|
| Short test, default | 93 | 8.5 s | 1.4 GB |
| Short test, `--deep` | 64 | 8.1 s | 1.4 GB |
| Dry run, variants (both modes) | 88 | 7.8–8.6 s | 1.7 GB |
| Dry run, originals (both modes) | 14 | 5.7–6.3 s | 0.9–1.1 GB |
| lossprint 1.1.0, for comparison ([TOOLS.md](../TOOLS.md)) | | 2.7–3.2 s | 0.44 GB |

`--deep` gave the same verdict and the same score as the default mode on all 115 files scored in both modes. Its help
text says it catches "high-bitrate MP3 and Apple AAC transcodes that leave no heuristic trace"; here it flagged no
MP3 V0 or LAME 320 file.

### 5.5 Why it was not taken further

- **Accuracy.** It missed nearly every MP3 transcode (1 / 34) and flagged most genuine bait (14 / 22), where
  lossprint caught all transcodes and flagged no bait in the same files. Its MDCT evidence agreed with lossprint on
  Opus and AAC fakes, but it found nothing lossprint had missed.
- **Cost.** About 2.5–3 times lossprint's CPU time and 3–4 times its memory per file.
- **Conclusion recorded at the time:** lossprint is superior; FLAC Detective is at most a second witness on files
  that only lossprint flags.
- A full-corpus harness (every set-A original, all variants of 60 set-B sources) was written and dry-run on the
  files above; the full run was not started.
- Packaging and release pace (from this survey, not from the notes): the `[ml]` extra pulls PyTorch, and with
  several releases a week these numbers hold for 2.5.0 only.
