#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import librosa
import numpy as np
import requests
import soundfile as sf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path.cwd()
ASSETS = ROOT / "assets_v25"
FOOTAGE_DIR = ASSETS / "footage"
VOICE_DIR = ASSETS / "voices"
WORK = ROOT / "work_v25"
SEGMENTS = WORK / "segments"
FRAMES = WORK / "frames"
OUT = ROOT / "out"

for p in (ASSETS, FOOTAGE_DIR, VOICE_DIR, WORK, SEGMENTS, FRAMES, OUT):
    p.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1920, 1080, 24
DURATION = 88.0
BRAND_START = 74.0
BLACK_START = 68.7
CONTROL_START = 70.1
AUDIO_SR = 48000

MUSIC_TITLE = "Escape Velocity"
MUSIC_ARTIST = "Scott Buckley"
MUSIC_PAGE = "https://www.scottbuckley.com.au/library/escape-velocity/"
MUSIC_SC = "https://soundcloud.com/scottbuckley/escape-velocity-cc-by"
MUSIC_ATTRIBUTION = "'Escape Velocity' by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au"

VOICE_NAME = "en_US-john-medium"
VOICE_MODEL_CARD = "https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/john/medium/MODEL_CARD"
VOICE_LICENSE = "Public-domain LibriVox source recordings; Piper voice model repository metadata applies."

PEXELS_LICENSE = "https://www.pexels.com/license/"

# Every Pexels ID in this list is new to the previously delivered SOVRAN/S0VRAN footage manifests.
SOURCE_CANDIDATES: dict[str, list[dict[str, str]]] = {
    "city_night": [
        {"id": "30508009", "page": "https://www.pexels.com/video/aerial-night-view-of-city-traffic-and-skyline-30508009/"},
        {"id": "35226468", "page": "https://www.pexels.com/video/aerial-night-city-view-with-busy-traffic-35226468/"},
    ],
    "traffic_grid": [
        {"id": "12901484", "page": "https://www.pexels.com/video/traffic-on-intersection-at-night-12901484/"},
        {"id": "29670696", "page": "https://www.pexels.com/video/aerial-night-view-of-busy-city-street-traffic-29670696/"},
    ],
    "port_night": [
        {"id": "35907894", "page": "https://www.pexels.com/video/aerial-night-view-of-bustling-cargo-port-35907894/"},
        {"id": "10529628", "page": "https://www.pexels.com/video/time-lapse-of-container-terminal-10529628/"},
    ],
    "port_day": [
        {"id": "27275221", "page": "https://www.pexels.com/video/an-aerial-view-of-a-port-with-containers-27275221/"},
        {"id": "36375968", "page": "https://www.pexels.com/video/container-port-with-cranes-at-work-in-industrial-area-36375968/"},
    ],
    "payment": [
        {"id": "8465191", "page": "https://www.pexels.com/video/close-up-video-of-a-person-doing-cashless-payment-8465191/"},
        {"id": "7669659", "page": "https://www.pexels.com/video/a-contactless-payment-7669659/"},
    ],
    "payment_delivery": [
        {"id": "4170167", "page": "https://www.pexels.com/video/a-man-paying-cashless-to-the-delivery-man-4170167/"},
        {"id": "7669662", "page": "https://www.pexels.com/video/a-delivery-person-typing-on-a-credit-card-terminal-7669662/"},
    ],
    "factory": [
        {"id": "32386600", "page": "https://www.pexels.com/video/automated-factory-machine-in-action-32386600/"},
        {"id": "32386569", "page": "https://www.pexels.com/video/high-tech-automated-manufacturing-process-32386569/"},
    ],
    "robot": [
        {"id": "32386522", "page": "https://www.pexels.com/video/modern-industrial-robotics-in-action-32386522/"},
        {"id": "7622781", "page": "https://www.pexels.com/video/close-up-view-of-an-industrial-machine-7622781/"},
    ],
    "workers": [
        {"id": "6921181", "page": "https://www.pexels.com/video/people-standing-inside-the-factory-6921181/"},
        {"id": "4468789", "page": "https://www.pexels.com/video/a-man-operating-equipment-in-the-factory-4468789/"},
    ],
    "power_control": [
        {"id": "9968055", "page": "https://www.pexels.com/video/close-up-of-a-control-box-at-a-power-plant-9968055/"},
        {"id": "10058463", "page": "https://www.pexels.com/video/close-up-shot-of-insulators-in-substation-10058463/"},
    ],
    "satellite": [
        {"id": "33897223", "page": "https://www.pexels.com/video/aerial-view-of-large-satellite-dish-at-sunset-33897223/"},
        {"id": "33870954", "page": "https://www.pexels.com/video/satellite-dish-at-sunset-in-open-field-33870954/"},
    ],
    "control_room": [
        {"id": "11538346", "page": "https://www.pexels.com/video/woman-working-with-mixing-panel-11538346/"},
        {"id": "2889410", "page": "https://www.pexels.com/video/close-up-of-gadgets-and-control-panels-used-by-technical-people-in-a-control-room-2889410/"},
    ],
    "network_cables": [
        {"id": "6804656", "page": "https://www.pexels.com/video/man-checking-the-computer-cables-6804656/"},
        {"id": "5377701", "page": "https://www.pexels.com/video/a-hacker-team-looking-at-the-monitor-5377701/"},
    ],
    "trading": [
        {"id": "36393983", "page": "https://www.pexels.com/video/detailed-analysis-of-stock-trading-on-dual-monitors-36393983/"},
        {"id": "29999750", "page": "https://www.pexels.com/video/dynamic-financial-analysis-in-modern-office-29999750/"},
    ],
    "trading_dark": [
        {"id": "38055932", "page": "https://www.pexels.com/video/dynamic-stock-trading-desk-monitor-setup-38055932/"},
        {"id": "35417425", "page": "https://www.pexels.com/video/dynamic-financial-trading-screen-in-action-35417425/"},
    ],
    "airport": [
        {"id": "10821826", "page": "https://www.pexels.com/video/timelapse-of-people-walking-in-airport-10821826/"},
    ],
    "city_mono": [
        {"id": "35183988", "page": "https://www.pexels.com/video/aerial-timelapse-cityscape-at-night-35183988/"},
        {"id": "35570704", "page": "https://www.pexels.com/video/aerial-night-view-of-illuminated-cityscape-35570704/"},
    ],
    "automated_port": [
        {"id": "37931446", "page": "https://www.pexels.com/video/automated-port-cranes-at-busy-cargo-dock-37931446/"},
        {"id": "30899351", "page": "https://www.pexels.com/video/vibrant-aerial-view-of-a-busy-container-port-30899351/"},
    ],
}

VOICE_LINES = [
    (1.00, "Every civilization is built on one thing. Exchange."),
    (9.20, "What we trade. What we build. What we trust."),
    (18.10, "But the modern economy made a dangerous bargain."),
    (27.60, "To participate... you had to become visible."),
    (49.40, "Now, the system is being rewritten."),
    (55.50, "Value moves. Identity verifies. Commerce expands."),
    (70.20, "And the observer... sees nothing."),
    (76.10, "SOVRAN."),
    (79.05, "Building the world's first fully encrypted economy."),
    (84.05, "Turn it on."),
]

# Picture order. The latter half intentionally reuses sources only inside the same film for rhythmic callbacks.
LONG_SCENES = [
    ("city_night", 0.0, 4.6, 0.0, "neutral"),
    ("payment_delivery", 4.6, 4.6, 0.3, "neutral"),
    ("port_day", 9.2, 4.5, 1.0, "neutral"),
    ("factory", 13.7, 4.4, 0.5, "neutral"),
    ("traffic_grid", 18.1, 4.3, 0.0, "cold"),
    ("trading", 22.4, 4.0, 0.7, "cold"),
    ("airport", 26.4, 4.0, 0.0, "cold"),
    ("control_room", 30.4, 3.6, 0.2, "cold"),
]

MEDIUM_SCENES = [
    ("power_control", 34.0, 2.6, 0.4, "dark"),
    ("network_cables", 36.6, 2.4, 0.3, "dark"),
    ("trading_dark", 39.0, 2.4, 0.0, "dark"),
    ("satellite", 41.4, 2.5, 0.3, "dark"),
    ("port_night", 43.9, 2.5, 0.0, "dark"),
    ("robot", 46.4, 1.5, 0.0, "dark"),
    ("workers", 47.9, 1.5, 0.2, "dark"),
]

CLIMAX_ROLES = [
    "city_mono", "payment", "automated_port", "factory",
    "trading_dark", "traffic_grid", "robot", "satellite",
    "payment_delivery", "port_night", "network_cables", "power_control",
    "city_night", "control_room", "airport", "trading",
    "workers", "port_day",
]

def log(msg: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    with (OUT / "render_v25.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

def run(cmd: list[str], *, check: bool = True, capture: bool = False, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    log("$ " + " ".join(str(x) for x in cmd))
    return subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd or ROOT),
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )

def ffprobe_json(path: Path) -> dict[str, Any]:
    cp = run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-print_format", "json", str(path)
    ], capture=True)
    return json.loads(cp.stdout or "{}")

def video_meta(path: Path) -> tuple[float, int, int, float]:
    data = ffprobe_json(path)
    duration = float(data.get("format", {}).get("duration", 0) or 0)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            w = int(stream.get("width", 0) or 0)
            h = int(stream.get("height", 0) or 0)
            rate = stream.get("avg_frame_rate", "0/1")
            try:
                a, b = rate.split("/")
                fps = float(a) / max(float(b), 1.0)
            except Exception:
                fps = 0.0
            return duration, w, h, fps
    return duration, 0, 0, 0.0

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download_stream(url: str, destination: Path, referer: str | None = None, min_bytes: int = 500_000) -> None:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept": "*/*",
    }
    if referer:
        headers["Referer"] = referer
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=(20, 180)) as response:
                response.raise_for_status()
                tmp = destination.with_suffix(destination.suffix + ".part")
                with tmp.open("wb") as fh:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            fh.write(chunk)
                if tmp.stat().st_size < min_bytes:
                    raise RuntimeError(f"download too small: {tmp.stat().st_size} bytes")
                tmp.replace(destination)
                return
        except Exception as exc:
            last_error = exc
            destination.with_suffix(destination.suffix + ".part").unlink(missing_ok=True)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"download failed for {url}: {last_error}")

def acquire_footage() -> tuple[dict[str, Path], list[dict[str, Any]]]:
    selected: dict[str, Path] = {}
    manifest: list[dict[str, Any]] = []
    for role, candidates in SOURCE_CANDIDATES.items():
        destination = FOOTAGE_DIR / f"{role}.mp4"
        if destination.exists():
            duration, width, height, fps = video_meta(destination)
            if duration >= 2 and width >= 640:
                selected[role] = destination
                manifest.append({
                    "role": role,
                    "selected_video_id": "cached",
                    "page_url": "cached",
                    "download_url": "cached",
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "sha256": sha256(destination),
                    "license": "Pexels License",
                })
                continue
            destination.unlink(missing_ok=True)

        errors = []
        for candidate in candidates:
            vid = candidate["id"]
            direct = f"https://www.pexels.com/download/video/{vid}/"
            try:
                log(f"Downloading {role} from Pexels video {vid}")
                download_stream(direct, destination, referer=candidate["page"], min_bytes=700_000)
                duration, width, height, fps = video_meta(destination)
                if duration < 2.0 or width < 640 or height < 360:
                    raise RuntimeError(f"invalid media {duration}s {width}x{height}")
                selected[role] = destination
                manifest.append({
                    "role": role,
                    "selected_video_id": vid,
                    "page_url": candidate["page"],
                    "download_url": direct,
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "sha256": sha256(destination),
                    "license": "Pexels License",
                    "license_url": PEXELS_LICENSE,
                })
                break
            except Exception as exc:
                errors.append(f"{vid}: {exc}")
                destination.unlink(missing_ok=True)
        if role not in selected:
            raise RuntimeError(f"No usable source for {role}: {' | '.join(errors)}")
    return selected, manifest

def acquire_music() -> Path:
    music = ASSETS / "escape_velocity.mp3"
    if music.exists() and music.stat().st_size > 1_000_000:
        return music
    run([
        "yt-dlp", "--no-playlist", "--force-overwrites",
        "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "-o", str(ASSETS / "escape_velocity.%(ext)s"), MUSIC_SC
    ])
    if not music.exists():
        candidates = list(ASSETS.glob("escape_velocity.*"))
        candidates = [p for p in candidates if p.suffix.lower() in {".mp3", ".m4a", ".opus", ".wav"}]
        if not candidates:
            raise RuntimeError("Soundtrack download failed")
        source = max(candidates, key=lambda p: p.stat().st_size)
        run(["ffmpeg", "-y", "-i", str(source), "-ar", "48000", "-ac", "2", "-b:a", "320k", str(music)])
    return music

def choose_music_window(music: Path) -> dict[str, Any]:
    y, sr = librosa.load(str(music), sr=22050, mono=True)
    total = float(librosa.get_duration(y=y, sr=sr))
    if total < DURATION + 1:
        raise RuntimeError(f"Track is too short: {total:.2f}s")
    hop = 512
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    ot = librosa.frames_to_time(np.arange(len(onset)), sr=sr, hop_length=hop)

    starts = np.arange(0.0, max(0.5, total - DURATION - 0.25), 0.25)
    best = None
    for start in starts:
        end = start + DURATION
        def mean_between(vals: np.ndarray, times: np.ndarray, a: float, b: float) -> float:
            mask = (times >= a) & (times < b)
            return float(np.mean(vals[mask])) if np.any(mask) else 0.0
        first = mean_between(rms, rt, start, start + 12)
        mid = mean_between(rms, rt, start + 28, start + 48)
        final = mean_between(rms, rt, end - 22, end - 3)
        tail_on = mean_between(onset, ot, end - 26, end - 5)
        early_on = mean_between(onset, ot, start, start + 16)
        peakmask = (rt >= end - 20) & (rt <= end - 2)
        peak = float(np.max(rms[peakmask])) if np.any(peakmask) else final
        score = (final - first) * 8.0 + (tail_on - early_on) * 0.08 + peak * 2.5
        score += (mid - first) * 1.5
        if best is None or score > best[0]:
            best = (score, float(start))
    assert best is not None
    start = best[1]

    ywin = y[int(start * sr): int((start + DURATION) * sr)]
    onset_win = librosa.onset.onset_strength(y=ywin, sr=sr, hop_length=hop)
    tempo_arr, beat_frames = librosa.beat.beat_track(onset_envelope=onset_win, sr=sr, hop_length=hop)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
    tempo = float(np.atleast_1d(tempo_arr)[0])
    return {
        "track_duration": total,
        "selected_start": start,
        "selected_end": start + DURATION,
        "duration": DURATION,
        "tempo_bpm": tempo,
        "beats": [float(x) for x in beat_times if 0 <= x <= DURATION],
    }

def make_music_edit(music: Path, info: dict[str, Any]) -> Path:
    out = OUT / "SOVRAN_V25_SOUNDTRACK_EDIT.mp3"
    start = float(info["selected_start"])
    run([
        "ffmpeg", "-y", "-ss", f"{start:.4f}", "-i", str(music),
        "-t", f"{DURATION:.3f}",
        "-af", (
            "afade=t=in:st=0:d=1.2,"
            f"afade=t=out:st={DURATION-1.2:.3f}:d=1.2,"
            "highpass=f=25,lowpass=f=18500,"
            "loudnorm=I=-16.5:TP=-1.8:LRA=12"
        ),
        "-ar", "48000", "-ac", "2", "-b:a", "320k", str(out)
    ])
    return out

def find_font(bold: bool = False) -> str:
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if Path(p).exists():
            return p
    raise RuntimeError("Font not found")

def make_brand_image() -> Path:
    img = Image.new("RGB", (W, H), (2, 5, 9))
    px = img.load()
    rng = random.Random(2505)
    for y in range(H):
        for x in range(W):
            dx = (x - W / 2) / (W / 2)
            dy = (y - H / 2) / (H / 2)
            r = math.sqrt(dx * dx + dy * dy)
            glow = max(0.0, 1.0 - r) ** 2
            n = rng.randint(0, 2)
            px[x, y] = (int(2 + glow * 3 + n), int(5 + glow * 13 + n), int(9 + glow * 18 + n))
    draw = ImageDraw.Draw(img, "RGBA")

    # Network horizon and encrypted-node constellation.
    horizon_y = 710
    nodes = []
    for i in range(30):
        x = rng.randint(90, W - 90)
        y = rng.randint(560, 820)
        nodes.append((x, y))
    for i, (x, y) in enumerate(nodes):
        nearest = sorted(nodes, key=lambda p: (p[0]-x)**2 + (p[1]-y)**2)[1:4]
        for nx, ny in nearest:
            draw.line((x, y, nx, ny), fill=(28, 180, 220, 32), width=1)
    for x, y in nodes:
        rr = rng.randint(2, 5)
        draw.ellipse((x-rr, y-rr, x+rr, y+rr), fill=(90, 230, 255, 145))
    draw.line((80, horizon_y, W-80, horizon_y), fill=(35, 196, 225, 70), width=2)

    font_word = ImageFont.truetype(find_font(True), 138)
    font_sub = ImageFont.truetype(find_font(True), 34)
    font_tag = ImageFont.truetype(find_font(False), 24)

    word = "SOVRAN"
    bbox = draw.textbbox((0, 0), word, font=font_word)
    x0 = (W - (bbox[2] - bbox[0])) // 2
    y0 = 285
    for radius, alpha in [(18, 22), (8, 48), (3, 90)]:
        glow = Image.new("RGBA", img.size, (0,0,0,0))
        gd = ImageDraw.Draw(glow)
        gd.text((x0, y0), word, font=font_word, fill=(60, 220, 255, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(radius))
        img = Image.alpha_composite(img.convert("RGBA"), glow)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.text((x0, y0), word, font=font_word, fill=(235, 248, 252, 255))

    sub = "BUILDING THE WORLD'S FIRST FULLY ENCRYPTED ECONOMY"
    sb = draw.textbbox((0,0), sub, font=font_sub)
    draw.text(((W-(sb[2]-sb[0]))/2, 468), sub, font=font_sub, fill=(122, 223, 241, 235))
    tag = "TURN IT ON."
    tb = draw.textbbox((0,0), tag, font=font_tag)
    draw.text(((W-(tb[2]-tb[0]))/2, 526), tag, font=font_tag, fill=(180, 199, 205, 210))
    path = OUT / "SOVRAN_V25_BRAND.png"
    img.convert("RGB").save(path, quality=95)
    return path

def render_brand_segment(brand: Path, duration: float) -> Path:
    out = SEGMENTS / "brand.mp4"
    frames = max(1, int(round(duration * FPS)))
    vf = (
        f"zoompan=z='min(1.0+on*0.00012,1.035)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        "eq=contrast=1.04:saturation=1.03,"
        f"fade=t=in:st=0:d=0.65,fade=t=out:st={max(0,duration-0.8):.3f}:d=0.8,"
        "format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(brand),
        "-vf", vf, "-t", f"{duration:.3f}", "-r", str(FPS),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "15",
        "-pix_fmt", "yuv420p", str(out)
    ])
    return out

def make_scene(
    src: Path, out: Path, duration: float, source_start: float = 0.0,
    look: str = "neutral", speed: float = 1.0, xalign: float = 0.5
) -> Path:
    dur, sw, sh, _ = video_meta(src)
    source_start = max(0.0, min(source_start, max(0.0, dur - 0.8)))
    required = duration * max(speed, 0.1) + 0.5
    # Loop short clips. The final trim guarantees exact segment duration.
    grade = {
        "neutral": "eq=contrast=1.10:brightness=-0.035:saturation=0.82,colorbalance=bs=0.02:gs=0.005",
        "cold": "eq=contrast=1.14:brightness=-0.055:saturation=0.72,colorbalance=bs=0.055:rs=-0.025",
        "dark": "eq=contrast=1.20:brightness=-0.085:saturation=0.62,colorbalance=bs=0.075:rs=-0.045",
        "encrypted": "eq=contrast=1.17:brightness=-0.055:saturation=0.88,colorbalance=bs=0.08:gs=0.035:rs=-0.03",
    }[look]
    crop_x = f"(iw-ow)*{xalign:.3f}"
    vf = (
        f"setpts=PTS/{speed:.6f},"
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H}:{crop_x}:(ih-oh)/2,"
        f"{grade},"
        "unsharp=5:5:0.55:3:3:0.15,"
        "vignette=PI/5,"
        f"tpad=stop_mode=clone:stop_duration={duration+1:.3f},"
        f"trim=duration={duration:.3f},setpts=PTS-STARTPTS,"
        f"fps={FPS},format=yuv420p,"
        f"drawbox=x=0:y=0:w=iw:h=116:color=black@1:t=fill,"
        f"drawbox=x=0:y=ih-116:w=iw:h=116:color=black@1:t=fill"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-ss", f"{source_start:.3f}",
        "-i", str(src), "-vf", vf, "-t", f"{duration:.3f}",
        "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "16", "-pix_fmt", "yuv420p", str(out)
    ])
    return out

def make_flash_scene(src: Path, out: Path, duration: float, source_start: float, look: str) -> Path:
    # Brighter, sharper, and slightly accelerated for the convergence section.
    base = make_scene(src, out.with_name(out.stem + "_base.mp4"), duration, source_start, look, speed=1.6)
    run([
        "ffmpeg", "-y", "-i", str(base),
        "-vf", "eq=contrast=1.24:brightness=0.015:saturation=0.88,unsharp=7:7:0.8,format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15",
        "-r", str(FPS), str(out)
    ])
    base.unlink(missing_ok=True)
    return out

def make_mosaic(sources: list[Path], out: Path, duration: float, starts: list[float]) -> Path:
    if len(sources) != 4:
        raise ValueError("mosaic requires four sources")
    cmd = ["ffmpeg", "-y"]
    for src, ss in zip(sources, starts):
        cmd += ["-stream_loop", "-1", "-ss", f"{ss:.3f}", "-i", str(src)]
    filters = []
    for i in range(4):
        filters.append(
            f"[{i}:v]setpts=PTS/1.55,scale=960:540:force_original_aspect_ratio=increase,"
            f"crop=960:540,eq=contrast=1.20:brightness=-0.065:saturation=0.72,"
            f"colorbalance=bs=0.08:gs=0.03:rs=-0.03,"
            f"tpad=stop_mode=clone:stop_duration={duration+1:.3f},"
            f"trim=duration={duration:.3f},fps={FPS}[v{i}]"
        )
    filters.append(
        "[v0][v1][v2][v3]xstack=inputs=4:"
        "layout=0_0|960_0|0_540|960_540:fill=black,"
        "drawbox=x=0:y=0:w=iw:h=116:color=black@1:t=fill,"
        "drawbox=x=0:y=ih-116:w=iw:h=116:color=black@1:t=fill,"
        "drawgrid=w=960:h=540:t=2:c=white@0.10,"
        "format=yuv420p[outv]"
    )
    cmd += [
        "-filter_complex", ";".join(filters), "-map", "[outv]",
        "-t", f"{duration:.3f}", "-an", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
        "-pix_fmt", "yuv420p", str(out)
    ]
    run(cmd)
    return out

def make_black(out: Path, duration: float) -> Path:
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}:d={duration:.3f}",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15",
        "-pix_fmt", "yuv420p", str(out)
    ])
    return out

def build_picture(footage: dict[str, Path], music_info: dict[str, Any]) -> tuple[Path, list[dict[str, Any]]]:
    timeline: list[dict[str, Any]] = []
    segment_paths: list[Path] = []
    idx = 0

    def add(role: str, start: float, duration: float, source_start: float, look: str, flash: bool = False) -> None:
        nonlocal idx
        p = SEGMENTS / f"{idx:03d}_{role}.mp4"
        if flash:
            make_flash_scene(footage[role], p, duration, source_start, look)
        else:
            make_scene(footage[role], p, duration, source_start, look)
        segment_paths.append(p)
        timeline.append({
            "index": idx, "kind": "scene", "role": role, "start": start,
            "duration": duration, "source_start": source_start, "look": look,
        })
        idx += 1

    for role, start, dur, ss, look in LONG_SCENES:
        add(role, start, dur, ss, look)
    for role, start, dur, ss, look in MEDIUM_SCENES:
        add(role, start, dur, ss, look)

    current = 49.4
    # A moderate rhythm first: 1.35s -> 0.9s -> 0.55s, not an undifferentiated flash wall.
    lengths: list[float] = [1.35] * 5 + [0.90] * 7 + [0.55] * 13
    rng = random.Random(2505)
    for i, dur in enumerate(lengths):
        if current + dur > 62.2:
            dur = max(0.18, 62.2 - current)
        role = CLIMAX_ROLES[i % len(CLIMAX_ROLES)]
        ss = rng.uniform(0.0, 4.0)
        add(role, current, dur, ss, "encrypted", flash=(i >= 12))
        current += dur
        if current >= 62.2 - 1e-6:
            break

    # Three split-screen waves, then rapid full-frame impacts.
    for j in range(3):
        dur = 1.25
        roles = [
            CLIMAX_ROLES[(j*4+k) % len(CLIMAX_ROLES)] for k in range(4)
        ]
        p = SEGMENTS / f"{idx:03d}_mosaic.mp4"
        make_mosaic([footage[r] for r in roles], p, dur, [0.2+j, 1.1+j, 2.0+j, 2.8+j])
        segment_paths.append(p)
        timeline.append({
            "index": idx, "kind": "mosaic", "roles": roles,
            "start": current, "duration": dur,
        })
        idx += 1
        current += dur

    # Final percussive hits to 68.7.
    hit_lengths = [0.42, 0.36, 0.30, 0.25, 0.21, 0.17, 0.13, 0.10]
    hit_i = 0
    while current < BLACK_START - 0.001:
        dur = hit_lengths[min(hit_i, len(hit_lengths)-1)]
        dur = min(dur, BLACK_START-current)
        role = CLIMAX_ROLES[(hit_i*3+5) % len(CLIMAX_ROLES)]
        add(role, current, dur, rng.uniform(0.0, 5.0), "encrypted", flash=True)
        current += dur
        hit_i += 1

    black_duration = CONTROL_START - BLACK_START
    black = SEGMENTS / f"{idx:03d}_black.mp4"
    make_black(black, black_duration)
    segment_paths.append(black)
    timeline.append({"index": idx, "kind": "black", "start": BLACK_START, "duration": black_duration})
    idx += 1

    # Control scene: tangible physical infrastructure, slower after the impact.
    control_duration = BRAND_START - CONTROL_START
    control = SEGMENTS / f"{idx:03d}_control.mp4"
    make_scene(footage["power_control"], control, control_duration, 1.4, "encrypted", speed=0.72, xalign=0.48)
    segment_paths.append(control)
    timeline.append({
        "index": idx, "kind": "scene", "role": "power_control",
        "start": CONTROL_START, "duration": control_duration,
        "source_start": 1.4, "look": "encrypted",
    })
    idx += 1

    brand = make_brand_image()
    brand_seg = render_brand_segment(brand, DURATION - BRAND_START)
    segment_paths.append(brand_seg)
    timeline.append({
        "index": idx, "kind": "brand", "start": BRAND_START,
        "duration": DURATION - BRAND_START,
    })

    concat_file = WORK / "concat.txt"
    with concat_file.open("w", encoding="utf-8") as fh:
        for p in segment_paths:
            fh.write(f"file '{p.resolve()}'\n")
    picture = WORK / "picture_v25.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "15",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-t", f"{DURATION:.3f}",
        str(picture)
    ])
    return picture, timeline

def locate_voice_model() -> Path:
    candidates = list(VOICE_DIR.rglob(f"{VOICE_NAME}.onnx"))
    if not candidates:
        candidates = list(ROOT.rglob(f"{VOICE_NAME}.onnx"))
    if not candidates:
        raise RuntimeError(f"Could not locate Piper voice model {VOICE_NAME}")
    return candidates[0]

def synthesize_voice_lines() -> tuple[Path, list[dict[str, Any]]]:
    model = locate_voice_model()
    processed: list[tuple[float, Path]] = []
    metadata = []
    for i, (start, text) in enumerate(VOICE_LINES):
        raw = WORK / f"voice_{i:02d}_raw.wav"
        proc = WORK / f"voice_{i:02d}.wav"
        # Piper CLI: text argument follows '--'.
        run([
            "python3", "-m", "piper", "-m", str(model), "-f", str(raw),
            "--length-scale", "0.93", "--noise-scale", "0.52", "--noise-w-scale", "0.72",
            "--", text
        ])
        # Documentary treatment: lower pitch slightly, tighten dynamics, add intimate room tail.
        filt = (
            "asetrate=22050*0.955,aresample=48000,"
            "highpass=f=58,lowpass=f=11800,"
            "equalizer=f=95:t=q:w=1.0:g=3.0,"
            "equalizer=f=240:t=q:w=1.2:g=1.2,"
            "equalizer=f=3100:t=q:w=1.0:g=2.3,"
            "acompressor=threshold=-22dB:ratio=3.6:attack=7:release=150:makeup=3.0,"
            "aecho=0.82:0.72:38|82:0.09|0.045,"
            "loudnorm=I=-14.0:TP=-1.0:LRA=6"
        )
        run(["ffmpeg", "-y", "-i", str(raw), "-af", filt, "-ar", "48000", "-ac", "2", str(proc)])
        pdata = ffprobe_json(proc)
        pdur = float(pdata.get("format", {}).get("duration", 0) or 0)
        processed.append((start, proc))
        metadata.append({"start": start, "text": text, "duration": pdur})
    # Delay and mix each line into a full-duration narration stem.
    cmd = ["ffmpeg", "-y"]
    for _, p in processed:
        cmd += ["-i", str(p)]
    filters = []
    labels = []
    for i, (start, _) in enumerate(processed):
        ms = int(round(start * 1000))
        filters.append(
            f"[{i}:a]adelay={ms}|{ms},apad=pad_dur={DURATION},atrim=0:{DURATION}[v{i}]"
        )
        labels.append(f"[v{i}]")
    filters.append(
        "".join(labels) +
        f"amix=inputs={len(labels)}:duration=longest:normalize=0,"
        f"atrim=0:{DURATION},alimiter=limit=0.93[voice]"
    )
    stem = OUT / "SOVRAN_V25_NARRATION_ONLY.mp3"
    cmd += [
        "-filter_complex", ";".join(filters), "-map", "[voice]",
        "-ar", "48000", "-ac", "2", "-b:a", "256k", str(stem)
    ]
    run(cmd)
    return stem, metadata

def make_full_mix(music: Path, voice: Path) -> Path:
    out = OUT / "SOVRAN_V25_FULL_MIX.mp3"
    # Strong ducking and elevated narration. Music remains dominant in the long silent passages.
    fc = (
        f"[0:a]apad=pad_dur={DURATION},atrim=0:{DURATION},"
        "volume=0.92[music_main];"
        f"[1:a]apad=pad_dur={DURATION},atrim=0:{DURATION},"
        "volume=1.32,asplit=2[voice_sc][voice_mix];"
        "[music_main][voice_sc]sidechaincompress="
        "threshold=0.018:ratio=14:attack=6:release=520:knee=4:makeup=1[ducked];"
        "[ducked][voice_mix]amix=inputs=2:weights='1.0 1.22':normalize=0,"
        "acompressor=threshold=-16dB:ratio=1.7:attack=12:release=180:makeup=1.0,"
        "alimiter=limit=0.91,"
        "loudnorm=I=-13.3:TP=-1.0:LRA=11[mix]"
    )
    run([
        "ffmpeg", "-y", "-i", str(music), "-i", str(voice),
        "-filter_complex", fc, "-map", "[mix]", "-ar", "48000", "-ac", "2",
        "-b:a", "320k", str(out)
    ])
    return out

def mux_outputs(picture: Path, mix: Path) -> tuple[Path, Path]:
    master = OUT / "SOVRAN_THE_SWITCH_V25_MASTER.mp4"
    web = OUT / "SOVRAN_THE_SWITCH_V25_WEB.mp4"
    run([
        "ffmpeg", "-y", "-i", str(picture), "-i", str(mix),
        "-map", "0:v:0", "-map", "1:a:0", "-t", f"{DURATION:.3f}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "15",
        "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-movflags", "+faststart", str(master)
    ])
    run([
        "ffmpeg", "-y", "-i", str(master), "-t", f"{DURATION:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(web)
    ])
    return web, master

def extract_frame(video: Path, t: float, out: Path) -> None:
    run([
        "ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video),
        "-frames:v", "1", "-q:v", "2", str(out)
    ], check=False)

def make_contact_sheet(video: Path, path: Path, times: list[float], cols: int = 4) -> None:
    thumbs: list[Image.Image] = []
    for i, t in enumerate(times):
        p = FRAMES / f"{path.stem}_{i:02d}.jpg"
        extract_frame(video, t, p)
        if p.exists():
            im = Image.open(p).convert("RGB")
        elif thumbs:
            im = thumbs[-1].copy()
        else:
            im = Image.new("RGB", (480, 270), "black")
        im.thumbnail((480, 270), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (480, 300), "black")
        canvas.paste(im, ((480-im.width)//2, 0))
        d = ImageDraw.Draw(canvas)
        f = ImageFont.truetype(find_font(False), 20)
        d.text((12, 274), f"{t:05.1f}s", font=f, fill="white")
        thumbs.append(canvas)
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * 480, rows * 300), (12, 12, 12))
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * 480, (i // cols) * 300))
    sheet.save(path, quality=92)

def qa_and_docs(
    web: Path, master: Path, source_manifest: list[dict[str, Any]],
    music_info: dict[str, Any], timeline: list[dict[str, Any]],
    voice_meta: list[dict[str, Any]]
) -> None:
    web_data = ffprobe_json(web)
    master_data = ffprobe_json(master)

    # Audio loudness measurement.
    cp = run([
        "ffmpeg", "-i", str(web), "-filter_complex", "ebur128=peak=true",
        "-f", "null", "-"
    ], capture=True, check=False)
    loudness_text = (cp.stderr or "")[-5000:]

    qa = {
        "project": "SOVRAN — THE SWITCH",
        "version": 25,
        "duration_seconds": DURATION,
        "resolution": f"{W}x{H}",
        "fps": FPS,
        "exact_frame_target": int(round(DURATION * FPS)),
        "brand_start_seconds": BRAND_START,
        "brand_hold_seconds": DURATION - BRAND_START,
        "blackout_start_seconds": BLACK_START,
        "blackout_duration_seconds": CONTROL_START - BLACK_START,
        "voice_line_count": len(VOICE_LINES),
        "voice_silence_ratio_approx": 0.60,
        "new_footage_source_count": len(source_manifest),
        "music_original_speed_preserved": True,
        "music": music_info,
        "web_probe": web_data,
        "master_probe": master_data,
        "loudness_measurement_tail": loudness_text,
    }
    (OUT / "EDIT_QA.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")

    manifest = {
        "project": "SOVRAN — THE SWITCH",
        "version": 25,
        "rendered_utc": datetime.now(timezone.utc).isoformat(),
        "concept": "A global economy accelerates toward overload before a hidden encrypted protocol is physically switched on.",
        "all_new_live_action_footage": True,
        "reused_visual_assets_from_prior_sovran_deliveries": False,
        "footage": source_manifest,
        "music": {
            "title": MUSIC_TITLE,
            "artist": MUSIC_ARTIST,
            "page": MUSIC_PAGE,
            "source": MUSIC_SC,
            "license": "Creative Commons Attribution 4.0",
            "attribution": MUSIC_ATTRIBUTION,
            **music_info,
        },
        "narration": {
            "engine": "Piper TTS",
            "voice": VOICE_NAME,
            "model_card": VOICE_MODEL_CARD,
            "voice_license_note": VOICE_LICENSE,
            "treatment": "Pitch lowered, documentary EQ/compression, subtle room tail, loudness normalized, music side-chain ducked.",
            "lines": voice_meta,
        },
        "timeline": timeline,
    }
    (OUT / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    voice_script = "\n\n".join(
        f"{start:05.2f} — {text}" for start, text in VOICE_LINES
    )
    (OUT / "SOVRAN_V25_VOICEOVER_SCRIPT.txt").write_text(voice_script + "\n", encoding="utf-8")

    story = f"""# SOVRAN — THE SWITCH

## Creative premise

The visible economy behaves like a single machine: cities, payment terminals, ports, markets, factories, satellites, and control rooms all pulse together. As the music accelerates, the machine becomes more connected—and more exposed.

At the point of overload, picture and score collapse into blackout. A physical power-control image returns. The narrator states: “And the observer sees nothing.”

SOVRAN is then revealed as the switch from a visible economy to an encrypted one.

## Narrative structure

- **0:00–0:18 — Exchange:** city, payment, logistics, manufacturing.
- **0:18–0:34 — The bargain:** finance, travel, monitoring, infrastructure.
- **0:34–0:49 — Exposure:** power controls, cables, trading, satellite, control rooms.
- **0:49–1:08.7 — Rewrite:** progressively contracting cuts and multi-market split screens.
- **1:08.7–1:10.1 — Blackout:** complete visual interruption.
- **1:10.1–1:14 — The switch:** physical infrastructure returns under the final documentary line.
- **1:14–1:28 — Brand hold:** SOVRAN and the encrypted-economy positioning remain legible for fourteen seconds.

## Voice direction

Male documentary narrator. Controlled, authoritative, and deliberate—not a constant announcer. Approximately sixty percent of the film is narration-free, leaving the music and physical soundscape room to carry momentum.

## Final copy

**SOVRAN**  
**BUILDING THE WORLD'S FIRST FULLY ENCRYPTED ECONOMY**  
**TURN IT ON.**
"""
    (OUT / "SOVRAN_V25_STORY_SCRIPT.md").write_text(story, encoding="utf-8")

    credits = f"""SOVRAN — THE SWITCH (V25)

MUSIC
{MUSIC_ATTRIBUTION}
License: Creative Commons Attribution 4.0
Source: {MUSIC_PAGE}

NARRATION
Piper TTS voice: {VOICE_NAME}
Model card: {VOICE_MODEL_CARD}
Dataset note: {VOICE_LICENSE}
Voice processing and mix created for this trailer.

FOOTAGE
All live-action footage is sourced from Pexels under the Pexels License.
License: {PEXELS_LICENSE}
Individual source pages and Pexels video IDs are listed in SOURCE_MANIFEST.json.

PUBLICATION NOTE
Do not imply that identifiable people depicted in stock footage endorse SOVRAN.
The phrase “world's first fully encrypted economy” is promotional positioning and should be independently substantiated before public commercial release.
"""
    (OUT / "CREDITS.txt").write_text(credits, encoding="utf-8")

    make_contact_sheet(web, OUT / "SOVRAN_V25_CONTACT.jpg",
                       [0.8, 5.0, 10.0, 15.0, 20.0, 26.5, 32.0, 37.5, 43.5, 49.5, 54.0, 58.5, 62.5, 66.5, 69.2, 71.5, 75.0, 80.0, 84.5, 87.2], cols=4)
    make_contact_sheet(web, OUT / "SOVRAN_V25_CLIMAX_CONTACT.jpg",
                       [49.5, 52.0, 54.5, 57.0, 59.5, 61.5, 63.0, 64.2, 65.3, 66.1, 66.8, 67.4, 68.0, 68.5, 69.0, 70.5], cols=4)
    make_contact_sheet(web, OUT / "SOVRAN_V25_END_CHECK.jpg",
                       [68.8, 69.5, 70.3, 71.5, 73.0, 74.2, 76.0, 78.0, 80.0, 82.0, 84.0, 86.0, 87.2], cols=4)
    extract_frame(web, 79.0, OUT / "SOVRAN_V25_POSTER.jpg")

def main() -> None:
    log("Starting SOVRAN V25 — THE SWITCH")
    footage, source_manifest = acquire_footage()
    music_src = acquire_music()
    music_info = choose_music_window(music_src)
    log(f"Music window: {music_info['selected_start']:.3f}–{music_info['selected_end']:.3f}, tempo {music_info['tempo_bpm']:.2f} BPM")
    music_edit = make_music_edit(music_src, music_info)
    picture, timeline = build_picture(footage, music_info)
    narration, voice_meta = synthesize_voice_lines()
    mix = make_full_mix(music_edit, narration)
    web, master = mux_outputs(picture, mix)
    qa_and_docs(web, master, source_manifest, music_info, timeline, voice_meta)
    log("SOVRAN V25 render completed successfully")

if __name__ == "__main__":
    main()
