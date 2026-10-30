#!/usr/bin/env python3
# Copyright (c) 2026 Nikolas Faria. Licença MIT, texto completo em LICENCAS-DE-TERCEIROS.md.
"""cuts: detect hard cuts and write a frame-exact shot list.

Three detectors, combined:
  1. ffmpeg scene score  (select='gt(scene,T)')            -> candidates
  2. adaptive threshold  (per-frame abs-diff spike vs local
     median + HSV histogram distance)                       -> candidates / fallback
  3. motion-continuity verification: a candidate is a cut only if
     (a) a similarity transform can NOT explain frame i-1 -> i (LK + RANSAC
         inlier ratio), and
     (b) the camera trajectory breaks: features do not follow the motion
         predicted from the frames before, and the motion after differs.
     This kills false cuts from UI reflows/modals/filters while the camera
     keeps moving: the #1 failure mode on UI/launch videos.

Convention: a cut at frame i means frame i is the first frame of the new shot.

usage: cuts.py video.mp4 [-o shots.json] [--method auto|ffmpeg|threshold]
                [--scene 0.3] [--cuts 3.5,7.25 | --cut-frames 84,174]
"""
import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import dump, iter_frames, need, probe, r, run  # noqa: E402

SMALL_W = 320


def ffmpeg_scene(path, fps, thr):
    need("ffmpeg")
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-an", "-vf",
             f"select='gt(scene,{thr})',metadata=print", "-f", "null", "-"], check=False)
    out = p.stderr + p.stdout
    cands = {}
    t = None
    for line in out.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            t = float(m.group(1))
        m2 = re.search(r"lavfi\.scene_score=([0-9.]+)", line)
        if m2 and t is not None:
            cands[int(round(t * fps))] = float(m2.group(1))
    return cands


def continuity(a, b):
    """Fraction of tracked features explained by one similarity transform (1 = same shot)."""
    p0 = cv2.goodFeaturesToTrack(a, 300, 0.01, 6)
    if p0 is None or len(p0) < 15:
        return None  # textureless: cannot judge
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(21, 21), maxLevel=4)
    pb, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, winSize=(21, 21), maxLevel=4)
    ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm((p0 - pb).reshape(-1, 2), axis=1) < 1.0)
    if ok.sum() < 8:
        return 0.0
    M, inl = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if M is None:
        return 0.0
    return float(inl.sum()) / len(p0)


def _sim(a, b):
    p0 = cv2.goodFeaturesToTrack(a, 300, 0.01, 6)
    if p0 is None or len(p0) < 15:
        return None, 0
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(21, 21), maxLevel=4)
    ok = st.ravel() == 1
    if ok.sum() < 8:
        return None, 0
    M, inl = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=1.0)
    return (M, int(inl.sum())) if M is not None else (None, 0)


def same_trajectory(frames, i):
    """UI reflow vs real cut.

    A reflow (list collapsing, modal, filter) changes a lot of pixels, but the camera keeps
    its path: the motion before (i-2 -> i-1) equals the motion after (i -> i+1), and the
    parts of the UI that did not change still follow that predicted motion across i-1 -> i.
    Across a real cut essentially no feature lands where the old trajectory predicts.
    """
    if i < 2 or i + 1 >= len(frames):
        return False
    Mp, np_ = _sim(frames[i - 2], frames[i - 1])
    Mn, nn = _sim(frames[i], frames[i + 1])
    if Mp is None or Mn is None or np_ < 20 or nn < 20:
        return False
    if np.hypot(*(Mp[:, 2] - Mn[:, 2])) > 0.12 or abs(np.hypot(Mp[0, 0], Mp[1, 0]) - np.hypot(Mn[0, 0], Mn[1, 0])) > 0.0015:
        return False
    a, b = frames[i - 1], frames[i]
    p0 = cv2.goodFeaturesToTrack(a, 300, 0.01, 6)
    if p0 is None:
        return False
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(21, 21), maxLevel=4)
    pb, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, winSize=(21, 21), maxLevel=4)
    ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm((p0 - pb).reshape(-1, 2), axis=1) < 0.5)
    pred = cv2.transform(p0, Mp).reshape(-1, 2)
    agree = int(((np.linalg.norm(p1.reshape(-1, 2) - pred, axis=1) < 0.7) & ok).sum())
    return agree >= 6


def detect(path, method="auto", scene_thr=0.3, spike_ratio=3.0, cont_thr=0.35, manual=None):
    info = probe(path)
    fps = info["fps"]
    frames, hists = [], []
    for _, f in iter_frames(path, width=SMALL_W, gray=False):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        h = cv2.calcHist([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)], [0, 1, 2], None, [16, 8, 8],
                         [0, 180, 0, 256, 0, 256])
        cv2.normalize(h, h)
        frames.append(g)
        hists.append(h)
    n = len(frames)
    d_abs = np.zeros(n)
    d_hist = np.zeros(n)
    for i in range(1, n):
        d_abs[i] = float(np.mean(cv2.absdiff(frames[i], frames[i - 1])))
        d_hist[i] = float(cv2.compareHist(hists[i - 1], hists[i], cv2.HISTCMP_BHATTACHARYYA))

    if manual is not None:
        cuts = [{"frame": int(c), "method": "manual", "score": None, "continuity": None} for c in sorted(set(manual)) if 0 < c < n]
    else:
        cands = {}
        if method in ("auto", "ffmpeg"):
            for fr, sc in ffmpeg_scene(path, fps, scene_thr).items():
                if 0 < fr < n:
                    cands.setdefault(fr, {"methods": set(), "score": 0.0})
                    cands[fr]["methods"].add("ffmpeg-scene")
                    cands[fr]["score"] = max(cands[fr]["score"], sc)
        if method in ("auto", "threshold") or (method == "ffmpeg" and not cands):
            k = 6
            hist_thr = max(0.25, float(np.median(d_hist[1:])) + 8 * float(np.std(d_hist[1:][d_hist[1:] < np.percentile(d_hist[1:], 95)])) if n > 2 else 0.25)
            for i in range(1, n):
                nb = np.r_[d_abs[max(1, i - k):i], d_abs[i + 1:min(n, i + k + 1)]]
                base = float(np.median(nb)) if nb.size else 0.0
                spike = d_abs[i] > max(3.0, spike_ratio * base + 1.0)
                if spike or d_hist[i] > hist_thr:
                    cands.setdefault(i, {"methods": set(), "score": 0.0})
                    cands[i]["methods"].add("threshold")
                    cands[i]["score"] = max(cands[i]["score"], d_abs[i] / (base + 1e-3))
        cuts = []
        for fr in sorted(cands):
            c = continuity(frames[fr - 1], frames[fr])
            is_cut = c is None or c < cont_thr
            if is_cut and c is not None and same_trajectory(frames, fr):
                is_cut = False  # content changed (UI reflow / modal) but the camera kept its exact path
            if is_cut:
                cuts.append({"frame": fr, "method": "+".join(sorted(cands[fr]["methods"])),
                             "score": r(cands[fr]["score"], 3), "continuity": r(c, 3)})
        # merge cuts closer than 2 frames (flash frames) keeping the first
        merged = []
        for c in cuts:
            if merged and c["frame"] - merged[-1]["frame"] < 2:
                continue
            merged.append(c)
        cuts = merged

    bounds = [0] + [c["frame"] for c in cuts] + [n]
    shots = []
    for i, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        shots.append({"index": i + 1, "start_frame": a, "end_frame": b, "frames": b - a,
                      "start_s": r(a / fps, 3), "end_s": r(b / fps, 3), "dur_s": r((b - a) / fps, 3)})
    for c in cuts:
        c["time_s"] = r(c["frame"] / fps, 3)
    durs = np.array([s["dur_s"] for s in shots], dtype=float)
    return {
        "fps": fps, "frames": n, "width": info["width"], "height": info["height"],
        "duration_s": r(n / fps, 3),
        "cuts": cuts,
        "shots": shots,
        "stats": {
            "shot_count": len(shots),
            "cut_count": len(cuts),
            "asl_s": r(durs.mean(), 2),
            "median_shot_s": r(np.median(durs), 2),
            "min_shot_s": r(durs.min(), 2),
            "max_shot_s": r(durs.max(), 2),
            "cuts_per_min": r(len(cuts) / (n / fps / 60), 1) if n else None,
        },
        "transition_note": "Only hard cuts are detected automatically. Check the contact sheet for dissolves/whips.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("-o", "--out")
    ap.add_argument("--method", default="auto", choices=["auto", "ffmpeg", "threshold"])
    ap.add_argument("--scene", type=float, default=0.3, help="ffmpeg scene threshold (0-1)")
    ap.add_argument("--continuity", type=float, default=0.35, help="max inlier ratio still counted as a cut")
    ap.add_argument("--cuts", help="manual cut times in seconds, comma separated")
    ap.add_argument("--cut-frames", help="manual cut frames, comma separated")
    a = ap.parse_args(argv)
    manual = None
    if a.cut_frames:
        manual = [int(x) for x in a.cut_frames.split(",") if x.strip()]
    elif a.cuts:
        fps = probe(a.video)["fps"]
        manual = [int(round(float(x) * fps)) for x in a.cuts.split(",") if x.strip()]
    res = detect(a.video, a.method, a.scene, cont_thr=a.continuity, manual=manual)
    if a.out:
        dump(res, a.out)
    print(json.dumps({"cuts_s": [c["time_s"] for c in res["cuts"]], **res["stats"]}, indent=2))


if __name__ == "__main__":
    main()
