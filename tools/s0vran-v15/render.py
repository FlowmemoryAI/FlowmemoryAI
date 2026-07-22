#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import librosa
import numpy as np
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

try:
    from curl_cffi import requests as cffi_requests
except Exception:
    cffi_requests = None

ROOT = Path.cwd()
OUT = ROOT / "out"
ASSETS = ROOT / "assets_v15"
SHOTS = ROOT / "shots_v15"
OUT.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)
SHOTS.mkdir(parents=True, exist_ok=True)

FPS = 24
WIDTH = 1920
HEIGHT = 1080
STORY_SECONDS = 54.0
BLACK_SECONDS = 1.5
BRAND_SECONDS = 10.5
TOTAL_SECONDS = STORY_SECONDS + BLACK_SECONDS + BRAND_SECONDS
STORY_FRAMES = int(round(STORY_SECONDS * FPS))
TOTAL_FRAMES = int(round(TOTAL_SECONDS * FPS))
LOG_FILE = OUT / "render_v15.log"

WEB = OUT / "S0VRAN_BEYOND_THE_VEIL_V15_WEB.mp4"
MASTER = OUT / "S0VRAN_BEYOND_THE_VEIL_V15_MASTER.mp4"
MUSIC_PREVIEW = OUT / "S0VRAN_V15_SOUNDTRACK_EDIT.mp3"
POSTER = OUT / "S0VRAN_V15_POSTER.jpg"
CONTACT = OUT / "S0VRAN_V15_CONTACT.jpg"
CLIMAX_CONTACT = OUT / "S0VRAN_V15_CLIMAX_CONTACT.jpg"
SCRIPT_FILE = OUT / "S0VRAN_V15_STORY_SCRIPT.md"
CREDITS = OUT / "CREDITS.txt"
MANIFEST = OUT / "SOURCE_MANIFEST.json"
QA_FILE = OUT / "EDIT_QA.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

MUSIC_PAGE = "https://www.scottbuckley.com.au/library/the-illusionist/"
MUSIC_TITLE = "The Illusionist"
MUSIC_ARTIST = "Scott Buckley"
MUSIC_ATTRIBUTION = (
    "'The Illusionist' by Scott Buckley - released under CC-BY 4.0. "
    "www.scottbuckley.com.au"
)

# Every page in this pool is new to this film. Each role has fallbacks so the
# render remains resilient if one page changes its delivery URL.
FOOTAGE: dict[str, list[tuple[str, str]]] = {
    "candle_mirror": [
        ("Black candle beside a mirror", "https://www.pexels.com/video/the-flame-of-a-burning-black-candlightle-6014528/"),
        ("Candle in a dark setting", "https://www.pexels.com/video/burning-candle-flame-in-dark-setting-34293818/"),
    ],
    "mirror_woman": [
        ("Woman looking into a vintage mirror", "https://www.pexels.com/video/a-woman-looking-in-the-mirror-7271365/"),
        ("Woman under neon light looking at a mirror", "https://www.pexels.com/video/a-woman-looking-at-mirror-6835789/"),
    ],
    "eye_phone": [
        ("Phone reflected inside an eye", "https://www.pexels.com/video/close-up-of-eye-with-phone-reflection-36507913/"),
        ("Blue eye reflected against darkness", "https://www.pexels.com/video/blue-eye-reflected-on-dark-background-7698455/"),
    ],
    "rain_window": [
        ("Rain on a window over city lights", "https://www.pexels.com/video/nighttime-cityscape-with-rain-on-window-35099181/"),
        ("Rain-soaked city lights through glass", "https://www.pexels.com/video/rainy-night-city-lights-through-window-36417696/"),
    ],
    "fog_street": [
        ("Solitary walk through a foggy street", "https://www.pexels.com/video/moody-night-walk-in-foggy-street-35502610/"),
        ("Foggy urban scene beneath streetlights", "https://www.pexels.com/video/foggy-urban-night-scene-under-streetlights-36244096/"),
    ],
    "empty_train": [
        ("Empty subway interior at night", "https://www.pexels.com/video/inside-an-empty-subway-train-at-night-31436148/"),
        ("Moving train in a modern empty station", "https://www.pexels.com/video/modern-subway-station-with-moving-train-30343775/"),
    ],
    "train_tunnel": [
        ("Train approaching through a dark tunnel", "https://www.pexels.com/video/a-local-6-train-approaches-the-59th-street-subway-station-via-a-dark-subway-tunnel-eerily-illuminated-by-a-lone-red-stop-light-17176014/"),
        ("Subway train rushing through a tunnel", "https://www.pexels.com/video/a-subway-train-is-moving-through-a-tunnel-18657034/"),
    ],
    "tunnel_blur": [
        ("Monochrome subway tunnel in motion", "https://www.pexels.com/video/subway-tunnel-with-motion-blur-at-night-35759066/"),
        ("Fast night drive through a city tunnel", "https://www.pexels.com/video/fast-paced-night-drive-through-city-tunnel-31196470/"),
    ],
    "forest_night": [
        ("Figure walking through a misty forest at night", "https://www.pexels.com/video/eerie-walk-in-misty-forest-at-night-29725267/"),
        ("Woman walking along a misty forest trail", "https://www.pexels.com/video/woman-with-camera-walking-in-forest-11592868/"),
    ],
    "forest_path": [
        ("Mysterious illuminated forest path", "https://www.pexels.com/video/walking-in-a-path-in-the-forest-3679072/"),
        ("Woman walking through a winter forest", "https://www.pexels.com/video/a-woman-walking-in-the-forest-5950574/"),
    ],
    "moon": [
        ("Moon moving through dramatic clouds", "https://www.pexels.com/video/dramatic-night-sky-with-moon-through-clouds-33474906/"),
        ("Full moon shrouded by clouds", "https://www.pexels.com/video/full-moon-shrouded-by-dramatic-clouds-30343257/"),
    ],
    "dark_room": [
        ("Woman in a dark room with laser reflections", "https://www.pexels.com/video/a-woman-inside-a-dark-room-7846671/"),
        ("Lonely woman in dim light", "https://www.pexels.com/video/lonely-woman-in-a-dimly-lit-room-7277933/"),
    ],
    "hallway": [
        ("Dark industrial hallway", "https://www.pexels.com/video/a-dark-hallway-with-a-light-on-the-wall-19217894/"),
        ("Empty corridor with reflective glass", "https://www.pexels.com/video/a-dark-empty-hallway-7598737/"),
    ],
    "server": [
        ("Server LEDs in a dark data center", "https://www.pexels.com/video/close-up-of-a-cpu-7140928/"),
        ("Modern server room infrastructure", "https://www.pexels.com/video/database-storage-of-a-server-5028622/"),
    ],
    "hand_water": [
        ("Hand touching dark reflective water", "https://www.pexels.com/video/a-hand-is-touching-a-black-surface-in-the-dark-16392048/"),
        ("Rain puddle reflecting red light", "https://www.pexels.com/video/moody-night-rain-puddle-with-reflections-37050680/"),
    ],
    "neon_space": [
        ("Abstract neon installation in darkness", "https://www.pexels.com/video/neon-lights-glowing-in-a-dark-room-8058346/"),
        ("Rainy city street with luminous reflections", "https://www.pexels.com/video/moody-nighttime-city-street-with-rain-reflection-34796501/"),
    ],
    "candle_dark": [
        ("Solitary candle in darkness", "https://www.pexels.com/video/a-lit-candle-in-the-dark-with-a-black-background-19204923/"),
        ("Flickering candles in a dark room", "https://www.pexels.com/video/faded-flames-from-small-candles-at-dark-6213410/"),
    ],
}


def log(message: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("RUN " + " ".join(str(x) for x in command))
    result = subprocess.run(command, text=True, capture_output=True)
    if result.stdout:
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(result.stdout + "\n")
    if result.stderr:
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(result.stderr + "\n")
    if check and result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-4000:]
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{tail}")
    return result


def ffprobe(path: Path, count_frames: bool = False) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json",
    ]
    if count_frames:
        command[4:4] = ["-count_frames"]
    command.append(str(path))
    result = run(command)
    return json.loads(result.stdout or "{}")


def media_info(path: Path) -> tuple[float, int, int]:
    data = ffprobe(path)
    duration = float(data.get("format", {}).get("duration") or 0.0)
    width = height = 0
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            break
    return duration, width, height


def http_get(url: str, *, stream: bool = False, referer: str | None = None, timeout: int = 90):
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    errors: list[str] = []
    clients: list[Any] = []
    if cffi_requests is not None:
        clients.append(cffi_requests)
    clients.append(requests)
    for client in clients:
        try:
            kwargs: dict[str, Any] = {
                "headers": headers,
                "timeout": timeout,
                "allow_redirects": True,
                "stream": stream,
            }
            if client is cffi_requests:
                kwargs["impersonate"] = "chrome"
            response = client.get(url, **kwargs)
            if response.status_code >= 400:
                errors.append(f"{client.__name__}: HTTP {response.status_code}")
                continue
            return response
        except Exception as exc:
            errors.append(f"{getattr(client, '__name__', str(client))}: {exc}")
    raise RuntimeError(f"GET failed for {url}: {'; '.join(errors)}")


def download_stream(url: str, destination: Path, *, referer: str | None = None) -> None:
    response = http_get(url, stream=True, referer=referer, timeout=120)
    length = int(response.headers.get("content-length") or 0)
    if length and length > 650_000_000:
        raise RuntimeError(f"Remote file is unexpectedly large: {length} bytes")
    temp = destination.with_suffix(destination.suffix + ".part")
    with temp.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    if temp.stat().st_size < 200_000:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded file was too small: {url}")
    temp.replace(destination)


def pexels_id(page_url: str) -> str:
    match = re.search(r"-(\d+)/?$", page_url.rstrip("/"))
    if not match:
        raise ValueError(f"No Pexels video ID found in {page_url}")
    return match.group(1)


def pexels_mp4_candidates(page_url: str) -> list[str]:
    response = http_get(page_url, stream=False, timeout=60)
    text = html.unescape(response.text).replace("\\u002F", "/").replace("\\/", "/")
    found = re.findall(r"https://videos\.pexels\.com/video-files/[^\"'<>\\s]+?\.mp4", text)
    unique: list[str] = []
    for url in found:
        clean = url.replace("\\", "")
        if clean not in unique:
            unique.append(clean)

    def score(url: str) -> tuple[int, int]:
        match = re.search(r"_(\d{3,4})_(\d{3,4})_\d+fps\.mp4", url)
        if not match:
            return (9_999_999, 9_999_999)
        width, height = int(match.group(1)), int(match.group(2))
        landscape_penalty = 0 if width >= height else 2_000_000
        over_penalty = max(0, width - 1920) * 80
        under_penalty = abs(1920 - width) + abs(1080 - height)
        return (landscape_penalty + over_penalty + under_penalty, -width)

    unique.sort(key=score)
    return unique


def download_pexels(role: str, pages: list[tuple[str, str]]) -> dict[str, Any]:
    destination = ASSETS / f"{role}.mp4"
    if destination.exists():
        duration, width, height = media_info(destination)
        if duration >= 2.0 and width >= 640 and height >= 360:
            return {
                "role": role,
                "title": pages[0][0],
                "page_url": pages[0][1],
                "download_url": "cached",
                "duration": duration,
                "width": width,
                "height": height,
                "path": str(destination),
            }
        destination.unlink(missing_ok=True)

    errors: list[str] = []
    for title, page_url in pages:
        video_id = pexels_id(page_url)
        candidate_urls: list[str] = []
        try:
            candidate_urls.extend(pexels_mp4_candidates(page_url))
        except Exception as exc:
            errors.append(f"page parse {page_url}: {exc}")
        candidate_urls.append(f"https://www.pexels.com/download/video/{video_id}/")

        for media_url in candidate_urls[:8]:
            try:
                log(f"Downloading {role}: {title}")
                destination.unlink(missing_ok=True)
                download_stream(media_url, destination, referer=page_url)
                duration, width, height = media_info(destination)
                if duration < 2.0 or width < 640 or height < 360:
                    raise RuntimeError(
                        f"Invalid media geometry/duration: {width}x{height}, {duration:.2f}s"
                    )
                log(f"Selected {role}: {width}x{height}, {duration:.2f}s")
                return {
                    "role": role,
                    "title": title,
                    "page_url": page_url,
                    "download_url": media_url,
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "path": str(destination),
                }
            except Exception as exc:
                errors.append(f"{media_url}: {exc}")
                destination.unlink(missing_ok=True)
    raise RuntimeError(f"Could not download footage for {role}: {' | '.join(errors[-12:])}")


def download_music() -> tuple[Path, str]:
    destination = ASSETS / "the_illusionist.mp3"
    if destination.exists():
        duration, _, _ = media_info(destination)
        if duration > STORY_SECONDS + 2:
            return destination, "cached"
        destination.unlink(missing_ok=True)

    response = http_get(MUSIC_PAGE, stream=False, timeout=60)
    soup = BeautifulSoup(response.text, "html.parser")
    candidates: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(MUSIC_PAGE, anchor["href"])
        text = anchor.get_text(" ", strip=True).lower()
        if ".mp3" in href.lower() or ("mp3" in text and "download" in text):
            candidates.append(href)
    candidates.extend(
        [
            "https://www.scottbuckley.com.au/wp-content/uploads/2019/07/The-Illusionist.mp3",
            "https://www.scottbuckley.com.au/wp-content/uploads/2019/07/Scott-Buckley-The-Illusionist.mp3",
        ]
    )
    seen: set[str] = set()
    errors: list[str] = []
    for url in candidates:
        if url in seen:
            continue
        seen.add(url)
        try:
            destination.unlink(missing_ok=True)
            log(f"Downloading soundtrack candidate: {url}")
            download_stream(url, destination, referer=MUSIC_PAGE)
            duration, _, _ = media_info(destination)
            if duration <= STORY_SECONDS + 2:
                raise RuntimeError(f"Track too short: {duration:.2f}s")
            log(f"Soundtrack downloaded: {duration:.2f}s")
            return destination, url
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            destination.unlink(missing_ok=True)
    raise RuntimeError("Could not download soundtrack: " + " | ".join(errors[-8:]))


def mean_between(values: np.ndarray, times: np.ndarray, start: float, end: float) -> float:
    mask = (times >= start) & (times < end)
    if not np.any(mask):
        return 0.0
    return float(np.mean(values[mask]))


def select_music_window(music_path: Path) -> tuple[float, np.ndarray, float, dict[str, Any]]:
    log("Analyzing soundtrack energy and musical onsets")
    y, sr = librosa.load(str(music_path), sr=22050, mono=True)
    track_duration = float(librosa.get_duration(y=y, sr=sr))
    if track_duration < STORY_SECONDS + 1:
        raise RuntimeError(f"Soundtrack is too short: {track_duration:.2f}s")
    hop = 512
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onset_times_all = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=hop)

    best_score = -1e9
    best_start = 0.0
    latest = max(0.0, track_duration - STORY_SECONDS - 0.5)
    for start in np.arange(0.0, latest + 0.01, 0.5):
        end = start + STORY_SECONDS
        intro = mean_between(rms, rms_times, start, start + 10.0)
        middle = mean_between(rms, rms_times, start + 20.0, start + 36.0)
        final = mean_between(rms, rms_times, end - 11.0, end)
        peak_mask = (rms_times >= end - 8.0) & (rms_times <= end)
        peak = float(np.max(rms[peak_mask])) if np.any(peak_mask) else final
        early_onsets = mean_between(onset_env, onset_times_all, start, start + 12.0)
        late_onsets = mean_between(onset_env, onset_times_all, end - 12.0, end)
        score = (final - intro) * 15.0 + (peak - middle) * 5.0
        score += (late_onsets - early_onsets) * 0.10
        score -= intro * 1.2
        if score > best_score:
            best_score = score
            best_start = float(start)

    start_sample = int(round(best_start * sr))
    end_sample = int(round((best_start + STORY_SECONDS) * sr))
    segment = y[start_sample:end_sample]
    segment_onset_env = librosa.onset.onset_strength(y=segment, sr=sr, hop_length=hop)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=segment_onset_env,
        sr=sr,
        hop_length=hop,
        backtrack=False,
        units="frames",
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop)
    strengths = segment_onset_env[onset_frames] if len(onset_frames) else np.array([], dtype=float)
    if len(strengths):
        threshold = float(np.percentile(strengths, 38))
        strong = onset_times[strengths >= threshold]
    else:
        strong = np.array([], dtype=float)
    log(
        f"Selected soundtrack window {best_start:.3f}s–{best_start + STORY_SECONDS:.3f}s; "
        f"{len(strong)} strong musical onsets"
    )
    analysis = {
        "track_duration_seconds": track_duration,
        "selected_start_seconds": best_start,
        "selected_end_seconds": best_start + STORY_SECONDS,
        "window_score": best_score,
        "strong_onset_count": int(len(strong)),
        "sample_rate": sr,
    }
    return best_start, strong, sr, analysis


def build_cut_frames(onset_times: np.ndarray) -> list[int]:
    desired_seconds = [
        0.0, 4.75, 8.75, 12.50, 16.00, 19.40, 22.60, 25.50, 28.30,
        31.00, 33.50, 35.80, 37.80, 39.60, 41.20, 42.70, 44.00, 45.20,
        46.30, 47.30, 48.20, 49.05, 49.80, 50.50, 51.15, 51.70, 52.15,
        52.55, 52.90, 53.20, 53.45, 53.65, 53.82, 54.00,
    ]
    desired = [int(round(value * FPS)) for value in desired_seconds]
    onset_frames = sorted({int(round(float(value) * FPS)) for value in onset_times})
    cuts: list[int] = [0]
    for index, target in enumerate(desired[1:-1], start=1):
        remaining = len(desired) - index - 1
        minimum = cuts[-1] + (5 if index < 23 else 3)
        maximum = STORY_FRAMES - remaining * 3
        chosen = target
        if index < 23 and onset_frames:
            tolerance = 13 if index < 16 else 9
            candidates = [
                frame for frame in onset_frames
                if minimum <= frame <= maximum and abs(frame - target) <= tolerance
            ]
            if candidates:
                chosen = min(candidates, key=lambda frame: abs(frame - target))
        chosen = max(minimum, min(chosen, maximum))
        cuts.append(chosen)
    cuts.append(STORY_FRAMES)
    return cuts


def deterministic_start(role: str, index: int, source_duration: float, needed: float) -> float:
    available = max(0.0, source_duration - needed - 0.25)
    if available <= 0.0:
        return 0.0
    digest = hashlib.sha256(f"{role}:{index}:v15".encode("utf-8")).hexdigest()
    unit = int(digest[:8], 16) / 0xFFFFFFFF
    return available * (0.08 + 0.82 * unit)


def prepare_shot(
    source: Path,
    source_duration: float,
    role: str,
    index: int,
    frames: int,
) -> Path:
    destination = SHOTS / f"shot_{index:03d}_{role}.mp4"
    duration = frames / FPS
    start = deterministic_start(role, index, source_duration, duration)
    warm = role in {"candle_mirror", "candle_dark", "mirror_woman"}
    magenta = role in {"dark_room", "neon_space"}
    flip = index % 7 in {3, 6}
    phase = (index * 0.61) % (2 * math.pi)
    drift_x = 12 if duration > 1.2 else 4
    drift_y = 7 if duration > 1.2 else 3
    filters = [
        "tpad=stop_mode=clone:stop_duration=6",
        f"trim=duration={duration:.6f}",
        "setpts=PTS-STARTPTS",
    ]
    if flip:
        filters.append("hflip")
    filters.extend(
        [
            "scale=2048:1152:force_original_aspect_ratio=increase",
            (
                "crop=1920:1080:"
                f"x='(iw-ow)/2+{drift_x}*sin(n/43+{phase:.3f})':"
                f"y='(ih-oh)/2+{drift_y}*cos(n/57+{phase:.3f})'"
            ),
            f"fps={FPS}",
        ]
    )
    if warm:
        filters.extend(
            [
                "eq=contrast=1.10:brightness=-0.035:saturation=0.88:gamma=0.96",
                "colorchannelmixer=rr=1.07:gg=0.98:bb=0.90",
            ]
        )
    elif magenta:
        filters.extend(
            [
                "eq=contrast=1.14:brightness=-0.050:saturation=0.82:gamma=0.93",
                "colorchannelmixer=rr=1.03:gg=0.91:bb=1.12",
            ]
        )
    else:
        filters.extend(
            [
                "eq=contrast=1.12:brightness=-0.045:saturation=0.78:gamma=0.94",
                "colorchannelmixer=rr=0.94:gg=0.98:bb=1.09",
            ]
        )
    filters.extend(["vignette=PI/5", "unsharp=5:5:0.28"])

    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.6f}", "-i", str(source),
        "-vf", ",".join(filters),
        "-frames:v", str(frames),
        "-an", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
        "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
        "-g", "48", "-keyint_min", "48", "-sc_threshold", "0",
        str(destination),
    ]
    run(command)
    return destination


def make_black_clip() -> Path:
    destination = SHOTS / "black.mp4"
    frames = int(round(BLACK_SECONDS * FPS))
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}:d={BLACK_SECONDS}",
            "-frames:v", str(frames), "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
            "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-g", "48", "-keyint_min", "48", "-sc_threshold", "0",
            str(destination),
        ]
    )
    return destination


def font_path(bold: bool = False) -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    if bold:
        candidates.insert(0, "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf")
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("No suitable system font found")


def spaced_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, spacing: int) -> int:
    widths = [draw.textlength(char, font=font) for char in text]
    return int(round(sum(widths) + max(0, len(text) - 1) * spacing))


def draw_spaced(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    spacing: int,
    fill: tuple[int, int, int, int],
) -> None:
    x = center_x - spaced_width(draw, text, font, spacing) / 2
    for char in text:
        draw.text((x, y), char, font=font, fill=fill, anchor="la")
        x += draw.textlength(char, font=font) + spacing


def make_brand_image() -> Path:
    destination = ASSETS / "brand_v15.png"
    yy, xx = np.ogrid[:HEIGHT, :WIDTH]
    cx, cy = WIDTH / 2.0, HEIGHT / 2.0 - 40
    radius = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    glow = np.clip(1.0 - radius / 720.0, 0.0, 1.0) ** 3
    array = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    array[..., 0] = np.clip(2 + glow * 13, 0, 255)
    array[..., 1] = np.clip(3 + glow * 17, 0, 255)
    array[..., 2] = np.clip(7 + glow * 38, 0, 255)
    array[..., 3] = 255
    image = Image.fromarray(array, mode="RGBA")
    draw = ImageDraw.Draw(image, "RGBA")

    rng = np.random.default_rng(15015)
    for _ in range(115):
        x = int(rng.integers(100, WIDTH - 100))
        y = int(rng.integers(90, HEIGHT - 90))
        alpha = int(rng.integers(20, 90))
        size = int(rng.choice([1, 1, 1, 2]))
        draw.ellipse((x - size, y - size, x + size, y + size), fill=(150, 205, 255, alpha))

    ring_center = (WIDTH // 2, 345)
    for radius_value, alpha_value, line_width in [(93, 40, 2), (77, 105, 2), (6, 220, 0)]:
        box = (
            ring_center[0] - radius_value,
            ring_center[1] - radius_value,
            ring_center[0] + radius_value,
            ring_center[1] + radius_value,
        )
        if line_width:
            draw.ellipse(box, outline=(135, 205, 255, alpha_value), width=line_width)
        else:
            draw.ellipse(box, fill=(200, 235, 255, alpha_value))
    draw.arc((ring_center[0] - 62, ring_center[1] - 62, ring_center[0] + 62, ring_center[1] + 62), 205, 322, fill=(235, 245, 255, 215), width=3)

    brand_font = ImageFont.truetype(font_path(), 112)
    tagline_font = ImageFont.truetype(font_path(), 31)
    draw_spaced(draw, WIDTH // 2, 475, "S0VRAN", brand_font, 24, (242, 247, 252, 255))
    draw_spaced(
        draw,
        WIDTH // 2,
        628,
        "BEYOND THE WATCHED WORLD",
        tagline_font,
        10,
        (174, 195, 214, 230),
    )
    draw.line((760, 710, 1160, 710), fill=(98, 139, 170, 80), width=1)
    image.save(destination)
    return destination


def make_brand_clip(image_path: Path) -> Path:
    destination = SHOTS / "brand.mp4"
    frames = int(round(BRAND_SECONDS * FPS))
    fade_out_start = BRAND_SECONDS - 1.5
    filter_graph = (
        "scale=2048:1152,"
        "zoompan=z='min(zoom+0.00011,1.026)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={WIDTH}x{HEIGHT}:fps={FPS},"
        "fade=t=in:st=0:d=1.15,"
        f"fade=t=out:st={fade_out_start:.3f}:d=1.5"
    )
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", str(image_path),
            "-vf", filter_graph,
            "-frames:v", str(frames), "-an", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
            "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-g", "48", "-keyint_min", "48", "-sc_threshold", "0",
            str(destination),
        ]
    )
    return destination


def create_audio(music_path: Path, start: float) -> tuple[Path, Path]:
    wav = OUT / "soundtrack_v15.wav"
    filter_graph = (
        "aresample=48000,"
        "afade=t=in:st=0:d=1.15,"
        f"afade=t=out:st={STORY_SECONDS - 0.40:.3f}:d=0.40,"
        "aecho=0.80:0.45:650|1300|1950:0.16|0.085|0.04,"
        f"apad=pad_dur={TOTAL_SECONDS - STORY_SECONDS + 2:.3f},"
        f"atrim=duration={TOTAL_SECONDS:.3f},"
        "loudnorm=I=-15.0:TP=-1.4:LRA=10,"
        "alimiter=limit=0.95"
    )
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{start:.6f}", "-t", f"{STORY_SECONDS:.3f}", "-i", str(music_path),
            "-af", filter_graph,
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(wav),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "320k", str(MUSIC_PREVIEW),
        ]
    )
    return wav, MUSIC_PREVIEW


def concat_video(parts: list[Path]) -> Path:
    list_file = OUT / "concat_v15.txt"
    with list_file.open("w", encoding="utf-8") as handle:
        for path in parts:
            escaped = str(path.resolve()).replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")
    destination = OUT / "picture_v15.mp4"
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-an", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "slow", "-crf", "12",
            "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-g", "48", "-keyint_min", "48", "-sc_threshold", "0",
            "-movflags", "+faststart", "-t", f"{TOTAL_SECONDS:.3f}",
            str(destination),
        ]
    )
    return destination


def mux_outputs(picture: Path, audio: Path) -> None:
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(picture), "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart",
            "-metadata", "title=S0VRAN - Beyond the Veil",
            str(MASTER),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(MASTER),
            "-c:v", "libx264", "-preset", "slow", "-crf", "20",
            "-maxrate", "11M", "-bufsize", "22M",
            "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(WEB),
        ]
    )


def create_review_images() -> None:
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", "33.0", "-i", str(WEB), "-frames:v", "1",
            "-q:v", "2", str(POSTER),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(WEB),
            "-vf", "fps=1/4.35,scale=472:-1,tile=4x4:padding=5:margin=5",
            "-frames:v", "1", "-q:v", "2", str(CONTACT),
        ]
    )
    run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", "46.0", "-t", "8.2", "-i", str(WEB),
            "-vf", "fps=4.35,scale=312:-1,tile=6x6:padding=4:margin=4",
            "-frames:v", "1", "-q:v", "2", str(CLIMAX_CONTACT),
        ]
    )


def write_story_script() -> None:
    SCRIPT_FILE.write_text(
        """# S0VRAN — Beyond the Veil\n\n"
        "## Concept\n\n"
        "A woman notices that the surfaces around her are behaving like thresholds: a mirror, a phone screen, rain on glass, a train window, dark water. Each reflection implies another version of her life being observed somewhere beyond the visible world. She follows that unseen presence from the city into a dreamlike labyrinth of tunnels, forest paths, empty corridors, and machine rooms. The fragments accelerate until the physical world and its hidden duplicate become indistinguishable. Silence breaks the spell. S0VRAN appears not as a weapon, but as the door out.\n\n"
        "## Picture and music script\n\n"
        "**0:00–0:09 — The Flame**  \n"
        "A black candle and a woman at a mirror establish ritual, reflection, and unease. The music is allowed to breathe; cuts are long and visual motion is slow.\n\n"
        "**0:09–0:20 — The Reflection**  \n"
        "A phone reflected in an eye dissolves conceptually into rain on glass and a lone figure under foggy streetlights. The image begins to suggest that every surface can look back.\n\n"
        "**0:20–0:31 — The Threshold**  \n"
        "An empty train, a red light in a tunnel, and rushing underground motion carry the viewer away from ordinary space. Cuts begin landing on stronger musical impulses.\n\n"
        "**0:31–0:41 — The Labyrinth**  \n"
        "A night forest, an illuminated path, the moon, and a woman inside refracted light transform the surveillance story into a mythic journey through an invisible system.\n\n"
        "**0:41–0:48 — The Double**  \n"
        "Dark corridors, server lights, water reflections, eyes, and neon geometry reveal the second world: a machine-made shadow assembled from traces.\n\n"
        "**0:48–0:54 — Convergence**  \n"
        "The edit compresses from near-second cuts into fractions of a second. Mirrors, tunnels, moonlight, rain, eyes, flame, and machines collide on musical onsets.\n\n"
        "**0:54–0:55.5 — Blackout**  \n"
        "The picture disappears. Only the soundtrack's natural reverberant tail remains.\n\n"
        "**0:55.5–1:06 — S0VRAN**  \n"
        "The brand appears within a restrained halo and remains fully readable for nine seconds before a deliberate final fade. Tagline: **BEYOND THE WATCHED WORLD.**\n"
        """,
        encoding="utf-8",
    )


def write_metadata(
    sources: list[dict[str, Any]],
    music_url: str,
    music_analysis: dict[str, Any],
    cuts: list[int],
    onsets: np.ndarray,
) -> None:
    cut_seconds = [frame / FPS for frame in cuts]
    onset_list = [float(value) for value in onsets]
    errors = []
    for value in cut_seconds[1:-11]:
        if onset_list:
            errors.append(min(abs(value - onset) for onset in onset_list))
    qa = {
        "title": "S0VRAN - Beyond the Veil",
        "version": 15,
        "visual_source_pool": "all-new live-action footage for this film",
        "resolution": [WIDTH, HEIGHT],
        "fps": FPS,
        "target_duration_seconds": TOTAL_SECONDS,
        "target_frame_count": TOTAL_FRAMES,
        "story_duration_seconds": STORY_SECONDS,
        "blackout_duration_seconds": BLACK_SECONDS,
        "brand_card_start_seconds": STORY_SECONDS + BLACK_SECONDS,
        "brand_card_duration_seconds": BRAND_SECONDS,
        "brand_full_readability_seconds": BRAND_SECONDS - 2.65,
        "cut_count": len(cuts) - 2,
        "rapid_climax_start_seconds": 46.3,
        "mean_cut_to_musical_onset_ms": (float(np.mean(errors)) * 1000 if errors else None),
        "maximum_cut_to_musical_onset_ms": (float(np.max(errors)) * 1000 if errors else None),
        "music": {
            "title": MUSIC_TITLE,
            "artist": MUSIC_ARTIST,
            "page": MUSIC_PAGE,
            "download_url": music_url,
            "license": "Creative Commons Attribution 4.0",
            **music_analysis,
        },
    }
    final_probe = ffprobe(WEB, count_frames=True)
    qa["render_probe"] = final_probe
    QA_FILE.write_text(json.dumps(qa, indent=2), encoding="utf-8")

    manifest = {
        "project": "S0VRAN Beyond the Veil V15",
        "music": {
            "title": MUSIC_TITLE,
            "artist": MUSIC_ARTIST,
            "source_page": MUSIC_PAGE,
            "download_url": music_url,
            "license": "CC BY 4.0",
            "required_attribution": MUSIC_ATTRIBUTION,
        },
        "footage_license": "Pexels License",
        "footage": sources,
        "cut_frames": cuts,
        "cut_seconds": cut_seconds,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "S0VRAN — BEYOND THE VEIL (V15)",
        "",
        "MUSIC",
        MUSIC_ATTRIBUTION,
        f"Source: {MUSIC_PAGE}",
        "License: Creative Commons Attribution 4.0 International.",
        "",
        "LIVE-ACTION FOOTAGE",
        "All footage is used under the Pexels License and was newly sourced for this cut.",
        "Do not imply that any identifiable person depicted endorses S0VRAN.",
        "",
    ]
    for source in sources:
        lines.append(f"- {source['title']}: {source['page_url']}")
    CREDITS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    log("Starting S0VRAN V15 — Beyond the Veil")
    music_path, music_url = download_music()
    music_start, onsets, _sr, music_analysis = select_music_window(music_path)
    cuts = build_cut_frames(onsets)
    durations = [cuts[index + 1] - cuts[index] for index in range(len(cuts) - 1)]
    log(f"Built {len(durations)} picture intervals across {STORY_FRAMES} frames")

    source_records: list[dict[str, Any]] = []
    source_paths: dict[str, Path] = {}
    source_durations: dict[str, float] = {}
    for role, pages in FOOTAGE.items():
        record = download_pexels(role, pages)
        source_records.append({key: value for key, value in record.items() if key != "path"})
        source_paths[role] = Path(record["path"])
        source_durations[role] = float(record["duration"])

    narrative_sequence = [
        "candle_mirror", "mirror_woman", "eye_phone", "rain_window", "fog_street",
        "empty_train", "train_tunnel", "tunnel_blur", "forest_night", "forest_path",
        "moon", "dark_room", "hallway", "server", "hand_water", "eye_phone",
        "neon_space", "fog_street", "moon", "tunnel_blur", "mirror_woman", "server",
        "forest_path",
    ]
    climax_sequence = [
        "eye_phone", "candle_mirror", "hallway", "moon", "hand_water", "dark_room",
        "server", "rain_window", "train_tunnel", "candle_dark", "forest_path",
        "neon_space", "eye_phone", "fog_street", "moon", "candle_dark",
    ]
    sequence = narrative_sequence + climax_sequence
    while len(sequence) < len(durations):
        sequence.extend(climax_sequence)
    sequence = sequence[: len(durations)]

    shot_paths: list[Path] = []
    for index, (role, frame_count) in enumerate(zip(sequence, durations)):
        shot_paths.append(
            prepare_shot(
                source_paths[role],
                source_durations[role],
                role,
                index,
                frame_count,
            )
        )

    black = make_black_clip()
    brand_image = make_brand_image()
    brand = make_brand_clip(brand_image)
    picture = concat_video(shot_paths + [black, brand])
    audio, _preview = create_audio(music_path, music_start)
    mux_outputs(picture, audio)
    create_review_images()
    write_story_script()
    write_metadata(source_records, music_url, music_analysis, cuts, onsets)

    duration, width, height = media_info(WEB)
    if abs(duration - TOTAL_SECONDS) > 0.15:
        raise RuntimeError(f"Final duration failed QA: {duration:.3f}s")
    if width != WIDTH or height != HEIGHT:
        raise RuntimeError(f"Final geometry failed QA: {width}x{height}")
    log(f"Completed film: {WEB} ({duration:.3f}s, {width}x{height})")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"FATAL: {type(exc).__name__}: {exc}")
        raise
