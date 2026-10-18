"""Sample-aligned comparison of two recordings of a song (a stream capture and a library copy): decoded to
float64 at full scale, offset by the lag of the best cross-correlation (first 30 s), then over the overlap: share
of bit-identical samples (at the coarser of the two bit depths), residual RMS relative to the signal (dB) and
gain. Usage: align_diff.py compare.json  (rows with "rec" and "lib"); prints one JSON line per row."""

import json
import subprocess
import sys

import numpy as np
from scipy.signal import fftconvolve


def pcm(path: str) -> np.ndarray:
    raw = subprocess.run(["nice", "-n", "19", "ffmpeg", "-v", "error", "-i", path, "-map", "0:a", "-f", "s32le",
                          "-acodec", "pcm_s32le", "-"], capture_output=True, check=True).stdout  # fmt: skip
    return np.frombuffer(raw, dtype="<i4").reshape(-1, 2).astype(np.float64) / 2**31


def lag(a: np.ndarray, b: np.ndarray, sr: int = 44100) -> int:
    """Offset of b against a (b[i + lag] ~ a[i]), from the mono mix of the first 30 s; within +-2 s."""
    n = 30 * sr
    x, y = a[:n].mean(1), b[: n + 4 * sr].mean(1)
    c = fftconvolve(y, x[::-1], mode="full")
    zero = len(x) - 1
    window = c[zero - 2 * sr : zero + 2 * sr + 1]
    return int(np.argmax(window)) - 2 * sr


for row in json.load(open(sys.argv[1])):
    a, b = pcm(row["rec"]), pcm(row["lib"])
    k = lag(a, b)
    if k >= 0:
        b2, a2 = b[k:], a
    else:
        a2, b2 = a[-k:], b
    n = min(len(a2), len(b2))
    a2, b2 = a2[:n], b2[:n]
    bits = min(int(row["rec_info"]["bits_per_raw_sample"]), int(row["lib_info"]["bits_per_raw_sample"]))
    q = 2.0 ** (bits - 1)
    same = float(np.mean(np.round(a2 * q) == np.round(b2 * q)))
    gain = float(np.dot(a2.ravel(), b2.ravel()) / np.dot(b2.ravel(), b2.ravel()))
    res = a2 - b2
    rel = 10 * np.log10(np.mean(res**2) / np.mean(a2**2) + 1e-30)
    res_g = a2 - gain * b2
    rel_g = 10 * np.log10(np.mean(res_g**2) / np.mean(a2**2) + 1e-30)
    out = {"song": row["song"], "lag": k, "overlap_s": round(n / 44100, 2), "bits": bits, "identical": round(same, 6),
           "residual_db": round(float(rel), 1), "gain": round(gain, 5), "residual_db_gain": round(float(rel_g), 1)}
    print(json.dumps(out), flush=True)
