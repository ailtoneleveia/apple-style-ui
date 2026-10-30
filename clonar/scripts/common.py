# Copyright (c) 2026 Nikolas Faria. Licença MIT, texto completo em LICENCAS-DE-TERCEIROS.md.
"""Shared helpers: ffprobe, frame streaming, small stats utilities."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

VERSION = "0.1.0"


def need(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise SystemExit(f"[sharingan] missing dependency: {binary} (install ffmpeg)")
    return path


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def _ratio(s: str | None) -> float:
    if not s or s in ("0/0", "N/A"):
        return float("nan")
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b) if float(b) else float("nan")
    return float(s)


def probe(path: str | Path) -> dict:
    """Container/stream facts every later step depends on."""
    need("ffprobe")
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout
    data = json.loads(out)
    v = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    if v is None:
        raise SystemExit(f"[sharingan] no video stream in {path}")
    fps = _ratio(v.get("avg_frame_rate"))
    if not math.isfinite(fps) or fps <= 0:
        fps = _ratio(v.get("r_frame_rate"))
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        w, h = h, w
    dur = float(v.get("duration") or data["format"].get("duration") or 0)
    nb = int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else int(round(dur * fps))
    return {
        "file": Path(path).name,
        "width": w,
        "height": h,
        "aspect": round(w / h, 4),
        "orientation": "landscape" if w > h else ("portrait" if h > w else "square"),
        "fps": round(fps, 4),
        "vfr_suspect": abs(_ratio(v.get("r_frame_rate")) - fps) > 0.01,
        "duration_s": round(dur, 3),
        "frames": nb,
        "codec": v.get("codec_name"),
        "pix_fmt": v.get("pix_fmt"),
        "bit_rate": int(data["format"].get("bit_rate", 0) or 0),
        "has_audio": a is not None,
        "audio": None if a is None else {
            "codec": a.get("codec_name"),
            "sample_rate": int(a.get("sample_rate", 0) or 0),
            "channels": int(a.get("channels", 0) or 0),
        },
    }


def iter_frames(path: str | Path, width: int | None = None, gray: bool = True):
    """Yield (index, frame) sequentially. Sequential decode is frame-exact; seeking is not."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise SystemExit(f"[sharingan] cannot open {path}")
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if width and f.shape[1] != width:
            h = int(round(f.shape[0] * width / f.shape[1]))
            f = cv2.resize(f, (width, h), interpolation=cv2.INTER_AREA)
        if gray:
            f = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        yield i, f
        i += 1
    cap.release()


def shot_of(frame: int, shots: list[dict]) -> int:
    for s in shots:
        if s["start_frame"] <= frame < s["end_frame"]:
            return s["index"]
    return shots[-1]["index"]


def r(x, n=2):
    """Round floats for JSON; keep None/NaN as None."""
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return x
    if not math.isfinite(xf):
        return None
    return round(xf, n)


def pct(a, q):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    return float(np.percentile(a, q)) if a.size else float("nan")


def med(a):
    return pct(a, 50)


def dump(obj, path: str | Path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load(path: str | Path):
    with open(path) as f:
        return json.load(f)


def tc(seconds: float) -> str:
    """Seconds -> compact timecode 00:03.50"""
    m, s = divmod(max(0.0, seconds), 60)
    return f"{int(m):02d}:{s:05.2f}"
