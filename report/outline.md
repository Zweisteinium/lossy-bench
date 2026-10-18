# Report outline

Working title: *Detecting lossy-sourced FLAC files in a real-world library: a benchmark of spectral, learned and
fused detectors, with ground truth from bit-exact stream captures*

Target forms, from least to most effort:
1. A technical report (arXiv, eess.AS or cs.SD), with this repository as its artefact.
2. A short paper or late-breaking demo (ISMIR LBD, AES convention e-Brief, DAFx).
3. A full paper. This needs the gaps under "Before a paper" closed.

## Sections and where the material is

| Section | Content | Source in this repo |
|---|---|---|
| Abstract | Question, corpus, three detectors, headline numbers, the master finding | README, docs/results.md |
| 1 Introduction | Why lossy-sourced "lossless" files matter (archives, stores, streaming masters); what detectors exist; contribution | to write |
| 2 Related work | Spectral cutoff detection (spek/Fakin' The Funk/auCDtect style), learned detectors (lossprint), codec forensics literature | to write |
| 3 Detectors | spectrum(), lossprint, flaccheck: algorithm, constants, invocation | docs/methods.md |
| 4 Corpus and labels | Inventory, integrity evidence, trust tiers, strata, deterministic selection; why labels come from provenance only | docs/methods.md, corpus/selection_summary.txt |
| 5 Experimental design | Transcodes (12 ffmpeg + 6 standalone encoders), bait, processed, 48 kHz control, guards, statistics | docs/methods.md |
| 6 Results | False positives, bait, recall per encoding, threshold sweeps, combined rules, held-out check | docs/results.md, results/analysis/summary.md |
| 7 Clipping hides encoder edges | The clip-free experiment as its own finding | docs/results.md |
| 8 Ground truth from stream captures | 10 bit-exact Spotify captures; lossy masters; copy vs master | docs/results.md |
| 9 Decision rule | The combined rule that follows from the data | docs/results.md |
| 10 Limitations | Label noise, single library, genre skew, lossprint flags as upper bounds, set B at 48 kHz | docs/results.md |
| 11 Conclusion | Rules that follow from the data | docs/results.md |
| Artefact appendix | Scripts, data dictionary, versions, how to reproduce | docs/reproducing.md, docs/data.md |

## Figures and tables to make

- Recall per encoding × detector (bar chart with CIs); the central figure.
- FP rate per tier and format × detector (with CIs).
- Bait FP vs resampler edge frequency.
- lossprint probability distribution: originals vs transcodes (log scale; shows how bimodal it is).
- Spectrum edge drop as Echolot measures it vs clip-free, per encoding (paired plot).
- Example spectrograms: an MP3 shelf on a bit-exact Spotify capture (Marti Fischer – Chabos), an Opus 20 kHz ceiling
  at 48 kHz, a 32 kHz bait edge, flaccheck's false positive on a CD-master edge.
- Corpus table: tiers × sets; strata × sets.

## Before a paper

Things a reviewer would ask for that the study does not have yet:
- **Independent ground truth for the lossprint-only flags.** About 56 originals at 44.1 kHz have no visible lowpass;
  a second source (store download or CD rip) for a sample of them would turn the upper bound into a measured false
  positive rate.
- **A second, public corpus**, so the results are not one person's library. Candidates: a CC-licensed set (Free
  Music Archive full-length lossless, Jamendo, MUSDB18-HQ stems mixed down), transcoded the same way. Only this part
  can be published with audio.
- **lossprint's training data.** Overlap between its training set and this corpus, or the same encoders, would
  inflate its recall. Ask the authors or read the model card.
- **Pinned artefacts:** a tagged release of this repo, a frozen data release (Zenodo DOI), and the exact binaries'
  hashes.
- **More stream captures:** 10 is a case series, not a rate. A random sample of library songs captured bit-exact
  would estimate how common lossy masters are on Spotify.
- **Clip-free on the bait**, and the clip-free ≥ 36 dB refinement confirmed on a sample larger than 60 songs.
- **Authorship and licence:** the author list, and a licence for code (e.g. MIT) and data (e.g. CC BY 4.0,
  metadata only).
