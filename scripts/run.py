#!/usr/bin/env python3
"""The benchmark run: score library originals (phase 1) and the variants made of them (phase 2) with three lossy
detectors. Read-only on the library; everything it makes lives in scratch/run/ and is deleted per job.

  phase 1  every set A file as it is: sha256, decoded-audio MD5, astats (peak, RMS, flat factor, peak count),
           then lossprint, flaccheck and Echolot's spectrum() (in the echolot:prod image).
  phase 2  per source file, the variants of its sets (B: 12 ffmpeg and 6 standalone-encoder transcodes; processed:
           MP3 320 with -1.3 dB or upsampled to 48 kHz; bait: soxr round trips via 32/38/40 kHz), each encoded,
           decoded back to FLAC and checked (rate, channels, flac -t, sample count within its tolerance), then
           scored by the three detectors in one batch per source.

Output: results/phase<N>.jsonl, one line per (job, variant, detector) plus one "meta" line per variant and a final
"job_done" line per job. A job without its job_done line counts as not done (its lines are ignored by the analysis
and it runs again). Stop: Ctrl+C, or `touch results/STOP` (running jobs finish first). Resume: run the same command.

Usage: run.py --phase 1|2 [--workers N] [--lp-threads N] [--only paths.txt] [--out FILE] [--limit N]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = Path(os.environ.get("LOSSY_BENCH_LIB", "tracks"))  # the library's track directory
SCRATCH = ROOT / "scratch" / "run"
RESULTS = ROOT / "results"
BIN = ROOT / "bin"
NICE = ["nice", "-n", "19", "ionice", "-c3"]
IMAGE = "echolot:prod"
MIN_FREE = 8 * 2**30  # bytes free on the scratch disk before a job starts
SOXR = "resampler=soxr:precision=28"

# variant -> how it is made. kind: the decoded sample count against the source's (tolerance below)
FFMPEG = {
    "mp3_128": (["-c:a", "libmp3lame", "-b:a", "128k"], "mp3", "ffmp3"),
    "mp3_192": (["-c:a", "libmp3lame", "-b:a", "192k"], "mp3", "ffmp3"),
    "mp3_320": (["-c:a", "libmp3lame", "-b:a", "320k"], "mp3", "ffmp3"),
    "mp3_v0": (["-c:a", "libmp3lame", "-q:a", "0"], "mp3", "ffmp3"),
    "mp3_v2": (["-c:a", "libmp3lame", "-q:a", "2"], "mp3", "ffmp3"),
    "aac_128": (["-c:a", "aac", "-b:a", "128k"], "m4a", "aac"),
    "aac_256": (["-c:a", "aac", "-b:a", "256k"], "m4a", "aac"),
    "opus_96": (["-c:a", "libopus", "-b:a", "96k"], "opus", "opus"),
    "opus_160": (["-c:a", "libopus", "-b:a", "160k"], "opus", "opus"),
    "vorbis_q3": (["-c:a", "libvorbis", "-q:a", "3"], "ogg", "exact"),
    "vorbis_q6": (["-c:a", "libvorbis", "-q:a", "6"], "ogg", "exact"),
    "vorbis_q9": (["-c:a", "libvorbis", "-q:a", "9"], "ogg", "exact"),
}
CLI = {  # standalone encoders, from a WAV of the source (their own defaults otherwise)
    "lame_320": (["lame", "--quiet", "-b", "320"], "mp3", "exact"),
    "lame_v0": (["lame", "--quiet", "-V", "0"], "mp3", "exact"),
    "fdkaac_256": (["fdkaac", "--silent", "-b", "256000"], "m4a", "fdk"),
    "fdkaac_vbr5": (["fdkaac", "--silent", "-m", "5"], "m4a", "fdk"),
    "opusenc_160": (["opusenc", "--quiet", "--bitrate", "160"], "opus", "opus"),
    "oggenc_q6": (["oggenc", "--quiet", "-q", "6"], "ogg", "exact"),
}
BAIT = {"bait_32k": 32000, "bait_38k": 38000, "bait_40k": 40000}
PROCESSED = ("mp3_320_gain", "mp3_320_up48")
TOLERANCE = {  # decoded samples - expected: allowed range
    # measured in the dry run: ffmpeg's libmp3lame is exact at 44.1 kHz but 46 samples long at 48 kHz (lame CLI:
    # exact at both); AAC (ffmpeg's and FDK alike) pads to the next 1024-sample frame
    "exact": (0, 0), "ffmp3": (0, 0), "ffmp3_48k": (0, 64), "opus": (-2, 2), "aac": (0, 1024), "fdk": (0, 1024),
    "bait": (-4, 4), "up48": (-2, 2), "ctl48": (-4, 4),
}
STOP = threading.Event()


def run(cmd, timeout=1800, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout, **kw)


def versions() -> dict:
    def first(cmd):
        try:
            r = run(cmd, 60)
            return (r.stdout or r.stderr).decode(errors="replace").strip().splitlines()[0][:120]
        except Exception as e:
            return f"unknown: {e}"
    pkg = run(["dpkg-query", "-W", "-f=${Package} ${Version}\\n", "fdkaac", "lame", "opus-tools", "vorbis-tools",
               "flac", "ffmpeg"]).stdout.decode().strip().splitlines()
    img = run(["docker", "inspect", IMAGE, "--format", "{{.Id}} {{range .Config.Env}}{{println .}}{{end}}"]).stdout.decode()
    return {
        "ffmpeg_host": first(["ffmpeg", "-hide_banner", "-version"]),
        "ffmpeg_spectrum": first(["docker", "run", "--rm", "--entrypoint", "ffmpeg", IMAGE, "-hide_banner", "-version"]),
        "echolot_image": " ".join([img.split()[0][:19]] + re.findall(r"ECHOLOT_(?:VERSION|COMMIT)=\S+", img)),
        "lossprint": first([str(BIN / "lossprint"), "--version"]),
        "flaccheck": first([str(BIN / "flaccheck"), "--version"]),
        "lame": first(["lame", "--version"]), "opusenc": first(["opusenc", "--version"]),
        "oggenc": first(["oggenc", "--version"]), "packages": pkg,
    }


class Spectrum:
    """One echolot:prod container running spectrum_worker.py for one job worker (requests one at a time)."""

    def __init__(self):
        mounts = ["-v", f"{LIB.parent}:{LIB.parent}:ro", "-v", f"{SCRATCH}:{SCRATCH}:ro",
                  "-v", f"{ROOT / 'scripts'}:/bench:ro"]
        self.p = subprocess.Popen(
            ["docker", "run", "--rm", "-i", "--network", "none", "--cpu-shares", "128", *mounts,
             "--entrypoint", "nice", IMAGE, "-n", "19", "ionice", "-c3", "python", "-u", "/bench/spectrum_worker.py"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.n = 0

    def __call__(self, path: Path) -> dict:
        self.n += 1
        self.p.stdin.write(json.dumps({"id": self.n, "path": str(path)}) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("spectrum worker ended")
        out = json.loads(line)
        if out["id"] != self.n:
            raise RuntimeError(f"spectrum worker answered {out['id']} for {self.n}")
        return out

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(30)
        except Exception:
            self.p.kill()


class Writer:
    def __init__(self, path: Path):
        self.f = open(path, "a", encoding="utf-8")
        self.lock = threading.Lock()

    def write(self, lines: list[dict]) -> None:  # one job's lines at once, then flushed
        text = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines)
        with self.lock:
            self.f.write(text)
            self.f.flush()
            os.fsync(self.f.fileno())


def probe(path: Path) -> dict:
    r = run([*NICE, "ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
             "stream=codec_name,sample_rate,channels,duration_ts,sample_fmt,bits_per_raw_sample", "-of", "json",
             str(path)], 120)
    s = (json.loads(r.stdout or b"{}").get("streams") or [{}])[0]
    return {"codec": s.get("codec_name"), "rate": int(s.get("sample_rate") or 0), "channels": int(s.get("channels") or 0),
            "samples": int(s.get("duration_ts") or 0), "bits": int(s.get("bits_per_raw_sample") or 0) or None,
            "sample_fmt": s.get("sample_fmt")}


def stat(p: Path) -> tuple[int, int]:
    st = p.stat()
    return st.st_size, int(st.st_mtime)


def original_meta(src: Path) -> dict:
    """sha256 of the file, MD5 of the decoded audio (pcm_s32le, tag-independent) and astats, in two reads."""
    h = hashlib.sha256()
    with open(src, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    md5 = SCRATCH / f"md5-{uuid.uuid4().hex}.txt"
    stats = "astats=metadata=0:measure_perchannel=none:measure_overall=Peak_level+RMS_level+Flat_factor+Peak_count"
    r = run([*NICE, "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "info", "-nostats", "-i", str(src),
             "-map", "0:a:0", "-c:a", "pcm_s32le", "-f", "md5", str(md5), "-map", "0:a:0", "-af", stats, "-f", "null", "-"])
    try:
        audio_md5 = md5.read_text().strip().removeprefix("MD5=") if r.returncode == 0 else None
    finally:
        md5.unlink(missing_ok=True)
    err = r.stderr.decode(errors="replace")
    def num(name):
        m = re.findall(rf"{name}: (-?[\d.]+|-?inf)", err)
        return float(m[-1]) if m else None
    return {"sha256": h.hexdigest(), "audio_md5_s32le": audio_md5, "peak_db": num("Peak level dB"),
            "rms_db": num("RMS level dB"), "flat_factor": num("Flat factor"), "peak_count": num("Peak count"),
            "ffmpeg_rc": r.returncode, "ffmpeg_err": None if r.returncode == 0 else err.strip()[-300:]}


def make_variants(job: dict, src: Path, wd: Path) -> tuple[list[tuple[str, Path]], list[dict]]:
    """The job's variants as FLACs in wd (each checked), and a meta line per variant (also for failures)."""
    rate, n = job["rate"], job["samples"]
    made, meta = [], []

    def finish(variant, kind, tmp, extra, expected=n, exp_rate=rate):
        line = {"variant": variant, "detector": "meta", "ok": False, "error": None, "out": extra}
        try:
            info = probe(tmp)
            t = run([*NICE, "flac", "-t", "-s", str(tmp)], 900)
            delta = info["samples"] - expected
            lo, hi = TOLERANCE["ffmp3_48k" if kind == "ffmp3" and exp_rate == 48000 else kind]
            extra |= {"decoded": info, "expected_samples": expected, "delta_samples": delta, "flac_t": t.returncode == 0}
            problems = []
            if t.returncode != 0:
                problems.append("flac -t failed: " + t.stderr.decode(errors="replace").strip()[-150:])
            if info["rate"] != exp_rate:
                problems.append(f"rate {info['rate']}, expected {exp_rate}")
            if info["channels"] != job["channels"]:
                problems.append(f"channels {info['channels']}, expected {job['channels']}")
            if not lo <= delta <= hi:
                problems.append(f"samples {info['samples']} ({delta:+d}), allowed {lo:+d}..{hi:+d}")
            if problems:
                line["error"] = "; ".join(problems)
                tmp.unlink(missing_ok=True)
            else:
                final = wd / f"{variant}.flac"
                os.replace(tmp, final)  # (only a checked file gets its final name)
                made.append((variant, final))
                line["ok"] = True
        except Exception as e:
            line["error"] = f"check: {type(e).__name__}: {e}"[:300]
            tmp.unlink(missing_ok=True)
        meta.append(line)

    def decode(enc, tmp, filters, fmt, out_rate):
        af = ["-af", ",".join(filters)] if filters else []
        return run([*NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(enc), "-map", "0:a:0",
                    "-map_metadata", "-1", *af, "-ar", str(out_rate), "-sample_fmt", fmt, "-c:a", "flac", str(tmp)])

    def encode_decode(variant, enc_cmd, ext, kind, from_wav=None):
        enc = wd / f"{variant}.enc.{ext}"
        tmp = wd / f"{variant}.tmp.flac"
        extra = {"encode": " ".join(enc_cmd)}
        if from_wav is None:
            e = run([*NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-map_metadata",
                     "-1", *enc_cmd, str(enc)])
        else:
            e = run([*NICE, *enc_cmd, "-o", str(enc), str(from_wav)] if enc_cmd[0] in ("fdkaac", "oggenc")
                    else [*NICE, *enc_cmd, str(from_wav), str(enc)])
        if e.returncode != 0 or not enc.is_file() or enc.stat().st_size == 0:
            meta.append({"variant": variant, "detector": "meta", "ok": False, "out": extra,
                         "error": "encode failed: " + e.stderr.decode(errors="replace").strip()[-200:]})
            enc.unlink(missing_ok=True)
            return None
        extra["encoded_bytes"] = enc.stat().st_size
        filters = [f"aresample={rate}:{SOXR}"] if kind == "opus" else []  # (Opus decodes at 48 kHz)
        d = decode(enc, tmp, filters, "s16", rate)
        if d.returncode != 0:
            meta.append({"variant": variant, "detector": "meta", "ok": False, "out": extra,
                         "error": "decode failed: " + d.stderr.decode(errors="replace").strip()[-200:]})
            enc.unlink(missing_ok=True)
            tmp.unlink(missing_ok=True)
            return None
        finish(variant, kind, tmp, extra)
        return enc

    sets = job["sets"]
    if "B" in sets:
        keep_mp3_320 = "processed" in sets
        for variant, (args, ext, kind) in FFMPEG.items():
            enc = encode_decode(variant, args, ext, kind)
            if enc is not None:
                if variant == "mp3_320" and keep_mp3_320:
                    for pv in PROCESSED:  # from this very MP3 320
                        tmp = wd / f"{pv}.tmp.flac"
                        if pv == "mp3_320_gain":
                            d = decode(enc, tmp, ["volume=-1.3dB"], "s16", rate)
                            kind_p, exp, exp_rate = "exact", n, rate
                        else:
                            d = decode(enc, tmp, [f"aresample=48000:{SOXR}"], "s32", 48000)
                            kind_p, exp, exp_rate = "up48", round(n * 48000 / rate), 48000
                        extra = {"encode": "mp3_320 (ffmpeg libmp3lame 320k), then " +
                                 ("volume=-1.3dB, s16" if pv == "mp3_320_gain" else "soxr to 48 kHz, s32")}
                        if d.returncode != 0:
                            meta.append({"variant": pv, "detector": "meta", "ok": False, "out": extra,
                                         "error": "decode failed: " + d.stderr.decode(errors="replace").strip()[-200:]})
                            tmp.unlink(missing_ok=True)
                        else:
                            finish(pv, kind_p, tmp, extra, exp, exp_rate)
                enc.unlink(missing_ok=True)
        wav = wd / "source.wav"
        fmt = "pcm_s24le" if (job.get("bps") or 16) > 16 else "pcm_s16le"
        w = run([*NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-map_metadata", "-1",
                 "-c:a", fmt, str(wav)])
        if w.returncode != 0:
            for variant in CLI:
                meta.append({"variant": variant, "detector": "meta", "ok": False, "out": {},
                             "error": "WAV failed: " + w.stderr.decode(errors="replace").strip()[-200:]})
        else:
            for variant, (args, ext, kind) in CLI.items():
                enc = encode_decode(variant, args, ext, kind, from_wav=wav)
                if enc is not None:
                    enc.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)
    if "bait" in sets:
        for variant, mid in BAIT.items():
            tmp = wd / f"{variant}.tmp.flac"
            f = f"aresample={mid}:{SOXR},aresample={rate}:{SOXR}"
            d = run([*NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-map_metadata",
                     "-1", "-af", f, "-sample_fmt", "s16", "-c:a", "flac", str(tmp)])
            extra = {"encode": f"genuine, soxr round trip {rate} -> {mid} -> {rate} Hz, s16"}
            if d.returncode != 0:
                meta.append({"variant": variant, "detector": "meta", "ok": False, "out": extra,
                             "error": "resample failed: " + d.stderr.decode(errors="replace").strip()[-200:]})
                tmp.unlink(missing_ok=True)
            else:
                finish(variant, "bait", tmp, extra)
    if "ctl48" in sets:  # (phase 3: the 48 kHz control, see select_ctl48.py)
        exp = round(n * 48000 / rate)
        to48 = [] if rate == 48000 else [f"aresample=48000:{SOXR}"]
        tmp = wd / "ctl48_40k.tmp.flac"
        f = ",".join([f"aresample=40000:{SOXR}", f"aresample=48000:{SOXR}"])
        d = run([*NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-map_metadata",
                 "-1", "-af", f, "-sample_fmt", "s16", "-c:a", "flac", str(tmp)])
        extra = {"encode": f"genuine, soxr round trip {rate} -> 40000 -> 48000 Hz, s16"}
        if d.returncode != 0:
            meta.append({"variant": "ctl48_40k", "detector": "meta", "ok": False, "out": extra,
                         "error": "resample failed: " + d.stderr.decode(errors="replace").strip()[-200:]})
            tmp.unlink(missing_ok=True)
        else:
            finish("ctl48_40k", "ctl48", tmp, extra, exp, 48000)
        enc = wd / "ctl48_opus160.enc.opus"
        tmp = wd / "ctl48_opus160.tmp.flac"
        extra = {"encode": ("soxr to 48 kHz, then " if to48 else "") + "libopus 160k, decoded at 48 kHz, s16"}
        e = run([*NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-map_metadata",
                 "-1", *(["-af", to48[0]] if to48 else []), "-c:a", "libopus", "-b:a", "160k", str(enc)])
        if e.returncode != 0 or not enc.is_file() or enc.stat().st_size == 0:
            meta.append({"variant": "ctl48_opus160", "detector": "meta", "ok": False, "out": extra,
                         "error": "encode failed: " + e.stderr.decode(errors="replace").strip()[-200:]})
        else:
            extra["encoded_bytes"] = enc.stat().st_size
            d = run([*NICE, "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(enc), "-map", "0:a:0",
                     "-map_metadata", "-1", "-ar", "48000", "-sample_fmt", "s16", "-c:a", "flac", str(tmp)])
            if d.returncode != 0:
                meta.append({"variant": "ctl48_opus160", "detector": "meta", "ok": False, "out": extra,
                             "error": "decode failed: " + d.stderr.decode(errors="replace").strip()[-200:]})
                tmp.unlink(missing_ok=True)
            else:
                finish("ctl48_opus160", "ctl48", tmp, extra, exp, 48000)
        enc.unlink(missing_ok=True)
    return made, meta


def score(files: list[tuple[str, Path]], wd: Path, spectrum: Spectrum, lp_threads: int) -> list[dict]:
    """lossprint, flaccheck and spectrum() for every (variant, path): exactly one line per detector each."""
    lines = []
    paths = {str(p): v for v, p in files}
    # lossprint: the files explicitly (it doesn't follow symlinks in a directory)
    lp = run([*NICE, str(BIN / "lossprint"), "-j", str(lp_threads), "-t", "0", "-o", "jsonl", "--", *paths], 3600)
    got = {}
    for line in lp.stdout.decode(errors="replace").splitlines():
        try:
            d = json.loads(line)
            got[d["path"]] = d
        except (ValueError, KeyError):
            pass
    for p, v in paths.items():
        d = got.get(p)
        lines.append({"variant": v, "detector": "lossprint", "ok": d is not None, "out": d,
                      "error": None if d else "no output: " + lp.stderr.decode(errors="replace").strip()[-300:]})
    # flaccheck: a directory of the files (links for library files; it follows them)
    fd = wd / "fc"
    fd.mkdir(exist_ok=True)
    for v, p in files:
        (fd / f"{v}.flac").symlink_to(p)
    out = wd / "flaccheck.json"
    fc = run([*NICE, str(BIN / "flaccheck"), "scan", str(fd), "--mode", "balanced", "--format", "json", "--explain",
              "--quiet", "--color", "never", "--workers", str(lp_threads), "-o", str(out)], 3600)
    res, skipped, errors = {}, {}, {}
    try:
        data = json.loads(out.read_text())
        for r in data.get("results", []):
            res[Path(r.get("path", "")).stem] = r
        for kind, bucket in (("skipped", skipped), ("errors", errors)):
            for r in data.get(kind, []):
                key = Path(r.get("path", "") if isinstance(r, dict) else str(r)).stem
                bucket[key] = r
    except Exception as e:
        errors["*"] = f"flaccheck output unreadable: {e} (rc {fc.returncode}: {fc.stderr.decode(errors='replace')[-200:]})"
    for v, _ in files:
        r = res.get(v)
        err = None if r else f"{'skipped' if v in skipped else 'error'}: {skipped.get(v) or errors.get(v) or errors.get('*') or 'no output'}"
        lines.append({"variant": v, "detector": "flaccheck", "ok": r is not None, "out": r, "error": err and str(err)[:300]})
    shutil.rmtree(fd, ignore_errors=True)
    out.unlink(missing_ok=True)
    # Echolot's spectrum(), one at a time
    for v, p in files:
        try:
            s = spectrum(p)
            lines.append({"variant": v, "detector": "spectrum", "ok": s["ok"], "out": s, "error": s.get("error")})
        except Exception as e:
            lines.append({"variant": v, "detector": "spectrum", "ok": False, "out": None,
                          "error": f"{type(e).__name__}: {e}"[:300]})
    return lines


def do_job(job: dict, phase: int, spectrum: Spectrum, lp_threads: int) -> list[dict]:
    src = LIB / job["path"]
    jid = f"p{phase}:{job['path']}"
    base = {"job": jid, "phase": phase}
    t0 = time.monotonic()
    if not src.is_file() or stat(src) != (job["size"], job["mtime"]):
        now = stat(src) if src.is_file() else None
        return [base | {"variant": "-", "detector": "job_done", "ok": False,
                        "error": f"changed_before_run: listed {job['size']}/{job['mtime']}, now {now}"}]
    wd = SCRATCH / f"job-{uuid.uuid4().hex[:12]}"
    wd.mkdir(parents=True)
    lines = []
    try:
        if phase == 1:
            meta = original_meta(src)
            lines.append({"variant": "original", "detector": "meta", "ok": meta["audio_md5_s32le"] is not None,
                          "error": meta.get("ffmpeg_err"), "out": meta})
            files = [("original", src)]
        else:
            files, metas = make_variants(job, src, wd)
            lines += metas
        if files:
            lines += score(files, wd, spectrum, lp_threads)
    finally:
        shutil.rmtree(wd, ignore_errors=True)
    changed = not src.is_file() or stat(src) != (job["size"], job["mtime"])
    lines.append({"variant": "-", "detector": "job_done", "ok": not changed,
                  "error": "changed_during_run" if changed else None, "seconds": round(time.monotonic() - t0, 1)})
    return [base | x for x in lines]


def done_jobs(path: Path) -> set:
    done = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue  # (a line cut by a kill: its job has no job_done line and runs again)
                if d.get("detector") == "job_done":
                    done.add(d["job"])
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, choices=(1, 2, 3), required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--lp-threads", type=int, default=2)
    ap.add_argument("--only", type=Path, help="file with set paths (one per line) to run only these")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = a.out or RESULTS / f"phase{a.phase}.jsonl"
    jobs = [json.loads(line) for line in open(ROOT / "corpus" / ("jobs_ctl48.jsonl" if a.phase == 3 else "jobs.jsonl"),
                                              encoding="utf-8")]
    if a.phase == 2:
        jobs = [j for j in jobs if {"B", "bait", "processed"} & set(j["sets"])]
    if a.only:
        wanted = [line.rstrip("\n") for line in open(a.only, encoding="utf-8") if line.strip()]
        by_path = {j["path"]: j for j in jobs}
        missing = [w for w in wanted if w not in by_path]
        if missing:
            sys.exit(f"--only: not in this phase's jobs: {missing}")
        jobs = [by_path[w] for w in wanted]
    done = done_jobs(out)
    todo = [j for j in jobs if f"p{a.phase}:{j['path']}" not in done]
    if a.limit:
        todo = todo[: a.limit]
    print(f"phase {a.phase}: {len(jobs)} jobs, {len(jobs) - len(todo) if not a.limit else len(done)} done, "
          f"{len(todo)} to run -> {out}", flush=True)
    tools = versions()
    writer = Writer(out)
    writer.write([{"job": "-", "phase": a.phase, "variant": "-", "detector": "run_start", "ok": True,
                   "out": {"tools": tools, "args": vars(a) | {"only": str(a.only), "out": str(out)}, "todo": len(todo)},
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}])
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    progress = {"phase": a.phase, "total": len(todo), "done": 0, "failed_lines": 0, "started": time.time()}
    lock = threading.Lock()
    queue = list(reversed(todo))

    def worker():
        spectrum = Spectrum()
        try:
            while not STOP.is_set() and not (RESULTS / "STOP").exists():
                with lock:
                    if not queue:
                        return
                    job = queue.pop()
                while shutil.disk_usage(SCRATCH).free < MIN_FREE and not STOP.is_set():
                    time.sleep(30)  # (the scratch disk is low: wait rather than fill it)
                try:
                    lines = do_job(job, a.phase, spectrum, a.lp_threads)
                except Exception as e:
                    lines = [{"job": f"p{a.phase}:{job['path']}", "phase": a.phase, "variant": "-",
                              "detector": "job_error", "ok": False, "error": f"{type(e).__name__}: {e}"[:300]}]
                    if "spectrum worker" in str(e):
                        spectrum.close()
                        spectrum = Spectrum()
                writer.write(lines)
                with lock:
                    progress["done"] += any(x["detector"] == "job_done" for x in lines)
                    progress["failed_lines"] += sum(not x["ok"] for x in lines)
                    el = time.time() - progress["started"]
                    progress["eta_min"] = round(el / max(progress["done"], 1) * (progress["total"] - progress["done"]) / 60, 1)
                    (RESULTS / f"progress_phase{a.phase}.json").write_text(json.dumps(progress))
        finally:
            spectrum.close()

    with ThreadPoolExecutor(a.workers) as ex:
        for f in [ex.submit(worker) for _ in range(a.workers)]:
            f.result()
    print(f"phase {a.phase}: {progress['done']} of {progress['total']} jobs done, {progress['failed_lines']} failed lines",
          flush=True)


if __name__ == "__main__":
    main()
