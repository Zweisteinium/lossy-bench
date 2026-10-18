"""Experiment (measurement only, Echolot unchanged): spectrum() with clipped frames left out, inside echolot:prod.

Found in phase 2: a loud master's lossy decode clips, and the clipping distortion fills the band above the encoder's
edge (MP3 320 measured ~28 dB, the same MP3 with -1.3 dB ~50 dB). Here the edge search of audio.spectrum() runs
twice on the same excerpts: as Echolot does it, and without the FFT frames that contain a clipped sample (|x| >= CLIP
in either channel). The excerpts are decoded in stereo and mixed to mono here (Echolot decodes with -ac 1, which can
hide a clipped channel); "asis" is checked against audio.spectrum() itself on every file (same_as_echolot).

stdin: {"id", "path"} per line; stdout: {"id", "ok", "error", "echolot", "asis", "clipfree", "same_as_echolot",
"clipped_frames", "frames"} per line. Verdicts use Echolot's own thresholds and _flicker() at the edge.
"""

import json
import sys
from pathlib import Path

import numpy as np
from echolot.library import audio

CLIP = 0.999


def excerpts(path: Path, dur: float) -> list[np.ndarray]:
    out = []
    for pos in (0.3, 0.5, 0.7):
        raw = audio._run(["ffmpeg", "-v", "error", "-ss", f"{dur * pos:.1f}", "-t", "15", "-i", str(path),
                          "-ac", "2", "-f", "f32le", "-"], 120).stdout
        out.append(np.frombuffer(raw, dtype=np.float32).reshape(-1, 2))
    return out


def edge(pieces: list[np.ndarray], sr: int, skip_clipped: bool) -> dict:
    nfft, hop = 8192, 4096
    win = np.hanning(nfft).astype(np.float32)
    acc, frames, clipped = np.zeros(nfft // 2 + 1), 0, 0
    monos = []
    for st in pieces:
        x = st.mean(axis=1)
        monos.append(x)
        for i in range(0, len(x) - nfft, hop):
            if np.abs(st[i: i + nfft]).max() >= CLIP:
                clipped += 1
                if skip_clipped:
                    continue
            acc += np.abs(np.fft.rfft(x[i: i + nfft] * win)) ** 2
            frames += 1
    if frames < 20:
        return {"verdict": "unknown", "reason": "too few frames", "frames": frames, "clipped_frames": clipped}
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    db = 10 * np.log10(acc / frames + 1e-20)
    if db[(freqs > 1000) & (freqs < 8000)].mean() < -90:
        return {"verdict": "unknown", "reason": "too quiet", "frames": frames, "clipped_frames": clipped}

    def band(lo, hi):
        return float(db[(freqs >= lo) & (freqs < hi)].mean())

    best_cut, best_drop = 0, 0.0
    for cut in range(12000, int(min(sr / 2 - 1600, 23000)), 100):
        drop = band(cut - 1500, cut - 300) - band(cut + 300, cut + 1500)
        if drop > best_drop:
            best_cut, best_drop = cut, drop
    res = {"cutoff_hz": best_cut, "drop_db": round(best_drop, 1), "verdict": "ok", "frames": frames,
           "clipped_frames": clipped}
    if best_drop >= audio.DROP_DB and best_cut < audio.MAX_LOSSY_CUT:
        fl = audio._flicker(monos, sr, best_cut) if best_cut >= audio.TRACES_FROM else None
        if fl is not None:
            res["flicker"] = fl
        if not (fl is not None and fl <= audio.FLICKER):
            res["verdict"] = "lossy"
    return res


for line in sys.stdin:
    req = json.loads(line)
    out = {"id": req["id"], "ok": False, "error": None}
    try:
        p = Path(req["path"])
        r = audio._run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                        "stream=sample_rate,channels:format=duration", "-of", "json", str(p)], 60)
        info = json.loads(r.stdout or b"{}")
        st = (info.get("streams") or [{}])[0]
        sr, ch, dur = int(st.get("sample_rate") or 0), int(st.get("channels") or 0), float(
            (info.get("format") or {}).get("duration") or 0)
        out["echolot"] = audio.spectrum(p)
        if sr and dur >= 20 and ch == 2:
            pieces = excerpts(p, dur)
            out["asis"] = edge(pieces, sr, False)
            out["clipfree"] = edge(pieces, sr, True)
            e = out["echolot"]
            out["same_as_echolot"] = (e.get("cutoff_hz"), e.get("verdict")) == (out["asis"].get("cutoff_hz"),
                                                                                out["asis"].get("verdict"))
            out["ok"] = True
        else:
            out["error"] = f"skipped: sr {sr}, channels {ch}, duration {dur:.1f}"
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"[:300]
    print(json.dumps(out), flush=True)
