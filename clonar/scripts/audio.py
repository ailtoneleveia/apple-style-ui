#!/usr/bin/env python3
# Copyright (c) 2026 Nikolas Faria. Licença MIT, texto completo em LICENCAS-DE-TERCEIROS.md.
"""audio: music vs SFX, onsets, tempo, and whether cuts / UI events land on sound.

Pure numpy (no librosa): mono 22.05 kHz via ffmpeg -> STFT -> log spectral flux
onset envelope -> peak picking; tempo from the onset autocorrelation (with a
mild prior around 120 BPM), beat phase by comb search.

Classification heuristics:
  silent      peak < -60 dBFS
  music       steady bed (low silence) and periodic onsets (beat strength)
  sfx-only    mostly silence, sparse transients, no periodicity
  + "sfx accents": onsets clearly off the beat grid while music plays

Sync checks (needs shots.json / camera.json):
  cuts      -> distance to nearest onset and nearest beat; fraction within 1 frame,
               compared with the chance rate for that onset density
  UI events -> distance from each UI micro-animation to the nearest onset (SFX sync)

usage: audio.py video.mp4 [--shots shots.json] [--camera camera.json] [-o audio.json]
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import dump, load, need, probe, r  # noqa: E402

SR = 22050
NFFT = 1024
HOP = 256


def load_audio(path):
    need("ffmpeg")
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(p.stdout, np.float32).copy()


def stft_mag(y):
    if y.size < NFFT:
        y = np.pad(y, (0, NFFT - y.size))
    n = 1 + (y.size - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    win = np.hanning(NFFT).astype(np.float32)
    return np.abs(np.fft.rfft(y[idx] * win, axis=1)).astype(np.float32)


def onsets_from(mag, y):
    lm = np.log1p(100 * mag)
    flux = np.maximum(0, np.diff(lm, axis=0)).sum(1)
    flux = np.r_[0, flux]
    env = flux / (flux.max() + 1e-9)
    hop_t = HOP / SR
    w = int(0.25 / hop_t)
    peaks = []
    last = -1e9
    for i in range(1, len(env) - 1):
        lo, hi = max(0, i - w), min(len(env), i + w)
        loc = env[lo:hi]
        md = np.median(loc)
        thr = md + max(0.03, 4 * np.median(np.abs(loc - md)))
        if env[i] >= env[i - 1] and env[i] > env[i + 1] and env[i] > thr and (i - last) * hop_t > 0.05:
            peaks.append(i)
            last = i
    # refine each onset in the time domain: the STFT flags an attack ~20 ms early (when it
    # enters the window tail). Find the sharpest rise of 2 ms log-energy inside that window.
    times = []
    yh = np.r_[0, np.diff(y)]  # pre-emphasis: tonal beds (pads, bass) stop masking the attack
    for p in peaks:
        a0 = max(0, (p - 1) * HOP)
        seg = yh[a0:a0 + NFFT + 2 * HOP]
        blk, hop = int(0.002 * SR), int(0.001 * SR)
        if seg.size < blk * 3:
            times.append(p * hop_t + NFFT / 2 / SR)
            continue
        e = np.array([np.log10(np.mean(seg[k:k + blk] ** 2) + 1e-10) for k in range(0, seg.size - blk, hop)])
        k = int(np.argmax(np.diff(e))) + 1
        times.append((a0 + k * hop) / SR)
    return env, np.array(times), np.array([env[p] for p in peaks])


def tempo(env):
    hop_t = HOP / SR
    e = env - env.mean()
    if np.allclose(e, 0):
        return None, 0.0, None
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    ac /= ac[0] + 1e-9
    lags = np.arange(len(ac))
    bpm = 60 / (np.maximum(lags, 1) * hop_t)
    ok = (bpm >= 60) & (bpm <= 200)
    if not ok.any():
        return None, 0.0, None
    prior = np.exp(-0.5 * (np.log2(bpm / 120) / 0.9) ** 2)
    score = np.where(ok, ac * prior, -1)
    L = int(np.argmax(score))
    # parabolic refinement
    if 1 <= L < len(ac) - 1:
        a, b, c = ac[L - 1], ac[L], ac[L + 1]
        off = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    else:
        off = 0.0
    period = (L + off) * hop_t
    strength = float(ac[L])
    # phase: comb search
    P = L + off
    best, ph = -1, 0.0
    for k in np.linspace(0, P, int(max(8, P * 4)), endpoint=False):
        idx = np.round(np.arange(k, len(env), P)).astype(int)
        idx = idx[idx < len(env)]
        v = env[idx].sum()
        if v > best:
            best, ph = v, k
    return 60 / period, strength, ph * hop_t + NFFT / 2 / SR - hop_t / 2


def analyze(path, shots=None, camera=None):
    info = probe(path)
    if not info["has_audio"]:
        return {"has_audio": False, "class": "silent", "note": "no audio stream"}
    y = load_audio(path)
    if y.size == 0:
        return {"has_audio": False, "class": "silent"}
    fps = info["fps"]
    frame_t = 1 / fps
    peak = float(np.max(np.abs(y)) + 1e-12)
    peak_db = 20 * math.log10(peak)
    blk = int(0.05 * SR)
    nb = y.size // blk
    rms = np.sqrt(np.mean(y[: nb * blk].reshape(nb, blk) ** 2, axis=1) + 1e-12)
    rms_db = 20 * np.log10(rms)
    silence = float(np.mean(rms_db < max(-60, peak_db - 45)))
    integrated = 20 * math.log10(float(np.sqrt(np.mean(y ** 2))) + 1e-12)
    if peak_db < -60:
        return {"has_audio": True, "class": "silent", "peak_dbfs": r(peak_db, 1)}
    mag = stft_mag(y)
    env, on_t, on_s = onsets_from(mag, y)
    bpm, strength, phase = tempo(env)
    loud = mag[(20 * np.log10(np.sqrt((mag ** 2).mean(1)) + 1e-9)) > peak_db - 40 - 20]
    flat = float(np.mean(np.exp(np.mean(np.log(loud + 1e-9), 1)) / (np.mean(loud, 1) + 1e-9))) if len(loud) else None
    dur = y.size / SR
    density = len(on_t) / dur if dur else 0
    beat_grid = None
    off_grid = []
    if bpm and strength > 0.2 and on_t.size >= 4:
        per = 60 / bpm
        # refine phase on the time-domain-refined onsets (circular mean of the strongest half)
        strong = on_s >= np.median(on_s)
        ang = 2 * np.pi * (on_t[strong] % per) / per
        phase = (math.atan2(np.sum(on_s[strong] * np.sin(ang)), np.sum(on_s[strong] * np.cos(ang))) % (2 * np.pi)) / (2 * np.pi) * per
        beat_grid = np.arange(phase % per, dur, per)
        for t in on_t:
            dist = np.min(np.abs(beat_grid - t)) if beat_grid.size else 1
            if dist > 0.07 and dist < per - 0.07:
                off_grid.append(float(t))
    music = strength >= 0.3 and silence < 0.35
    sfx_only = (not music) and (silence >= 0.35 or strength < 0.2)
    cls = "music" if music else ("sfx-only" if sfx_only else "ambient/unclear")
    if music and off_grid:
        cls = "music+sfx"
    res = {
        "has_audio": True,
        "class": cls,
        "peak_dbfs": r(peak_db, 1),
        "rms_dbfs": r(integrated, 1),
        "silence_fraction": r(silence, 3),
        "spectral_flatness": r(flat, 3),
        "tempo_bpm": r(bpm, 1) if strength > 0.2 else None,
        "beat_strength": r(strength, 3),
        "beat_phase_s": r(phase, 3) if strength > 0.2 else None,
        "onset_count": int(len(on_t)),
        "onsets_per_s": r(density, 2),
        "onsets_s": [r(t, 3) for t in on_t],
        "off_beat_onsets_s": [r(t, 3) for t in off_grid],
        "heuristics": "music = steady bed + periodic onsets; sfx = sparse transients / off-grid accents. Verify by ear.",
    }
    tol = max(frame_t, 0.045)
    chance = 1 - math.exp(-density * 2 * tol)
    if shots:
        rows = []
        for c in shots.get("cuts", []):
            t = c["time_s"]
            d_on = float(np.min(np.abs(on_t - t))) if on_t.size else None
            d_beat = float(np.min(np.abs(beat_grid - t))) if beat_grid is not None and beat_grid.size else None
            rows.append({"cut_s": t, "nearest_onset_ms": r(d_on * 1000, 1) if d_on is not None else None,
                         "nearest_beat_ms": r(d_beat * 1000, 1) if d_beat is not None else None,
                         "on_onset": bool(d_on is not None and d_on <= tol),
                         "on_beat": bool(d_beat is not None and d_beat <= tol)})
        n = len(rows)
        res["cuts"] = {
            "tolerance_ms": r(tol * 1000, 1),
            "per_cut": rows,
            "on_beat_fraction": r(sum(x["on_beat"] for x in rows) / n, 3) if n else None,
            "on_onset_fraction": r(sum(x["on_onset"] for x in rows) / n, 3) if n else None,
            "chance_on_onset": r(chance, 3),
            "verdict": None if not n else (
                "cuts are cut to the music (on beat)" if beat_grid is not None and sum(x["on_beat"] for x in rows) / n >= 0.6 else
                "cuts land on sound events above chance" if sum(x["on_onset"] for x in rows) / n > max(0.5, 2 * chance) else
                "cuts are not synced to audio"),
        }
    if camera and camera.get("ui_events"):
        ev = []
        for e in camera["ui_events"]:
            d = float(np.min(np.abs(on_t - e["time_s"]))) if on_t.size else None
            ev.append({"ui_event_s": e["time_s"], "nearest_onset_ms": r(d * 1000, 1) if d is not None else None,
                       "synced": bool(d is not None and d <= tol)})
        res["ui_events"] = {"per_event": ev, "synced_fraction": r(sum(x["synced"] for x in ev) / len(ev), 3),
                            "chance": r(chance, 3)}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--shots")
    ap.add_argument("--camera")
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    res = analyze(a.video, load(a.shots) if a.shots else None, load(a.camera) if a.camera else None)
    if a.out:
        dump(res, a.out)
    show = {k: v for k, v in res.items() if k not in ("onsets_s",)}
    print(json.dumps(show, indent=1))


if __name__ == "__main__":
    main()
