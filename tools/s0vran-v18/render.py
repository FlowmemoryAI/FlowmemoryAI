#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path.cwd()
ASSETS = ROOT / "assets_v18"
FOOTAGE_DIR = ASSETS / "footage"
SEGMENTS_DIR = ASSETS / "segments"
STILLS_DIR = ASSETS / "stills"
OUT = ROOT / "out"

FPS = 24
WIDTH = 1920
HEIGHT = 1080
CONTENT_HEIGHT = 816
STORY_FRAMES = 1320        # 55.0 seconds
BLACKOUT_FRAMES = 36       # 1.5 seconds
CONTROL_FRAMES = 60        # 2.5 seconds
BRAND_FRAMES = 228         # 9.5 seconds
TOTAL_FRAMES = STORY_FRAMES + BLACKOUT_FRAMES + CONTROL_FRAMES + BRAND_FRAMES
TOTAL_DURATION = TOTAL_FRAMES / FPS
TRACK_BPM = 145.0

MUSIC_PAGE = "https://www.free-stock-music.com/shane-ivers-subway-cell.html"
MUSIC_DIRECT = "https://www.free-stock-music.com/music/shane-ivers/mp3/shane-ivers-subway-cell.mp3"
MUSIC_TITLE = "Subway Cell"
MUSIC_ARTIST = "Shane Ivers"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

@dataclass(frozen=True)
class Source:
    key: str
    video_id: int
    page_url: str
    creator: str
    description: str

SOURCES: list[Source] = [
    Source(
        "neon_signal", 5820390,
        "https://www.pexels.com/video/a-neon-sign-turning-on-and-off-5820390/",
        "Maksim Goncharenok",
        "A blue neon sign pulses on and off in darkness.",
    ),
    Source(
        "alley_walk", 35735035,
        "https://www.pexels.com/video/mysterious-man-walking-in-narrow-alleyway-35735035/",
        "Özgür Sürmeli",
        "A lone man walks through a narrow, dimly lit alley.",
    ),
    Source(
        "hooded_portrait", 5495782,
        "https://www.pexels.com/video/a-man-in-black-hoodie-looking-pensive-5495782/",
        "Pavel Danilyuk",
        "A hooded man watches a computer in a dark room.",
    ),
    Source(
        "tunnel_silhouettes", 19867786,
        "https://www.pexels.com/video/the-dark-room-with-two-people-walking-in-the-dark-19867786/",
        "Ferhat E. Arslan",
        "Two silhouettes move through an underground passage.",
    ),
    Source(
        "underground_group", 5237051,
        "https://www.pexels.com/video/group-of-urban-friends-5237051/",
        "cottonbro studio",
        "A group gathers in a concrete underground passage.",
    ),
    Source(
        "dark_exchange", 7230797,
        "https://www.pexels.com/video/a-man-talking-with-someone-in-the-dark-7230797/",
        "MART PRODUCTION",
        "Two people face each other in a tense dark room.",
    ),
    Source(
        "wiring", 6442794,
        "https://www.pexels.com/video/a-man-seriously-fixing-the-cable-6442794/",
        "ArtHouse Studio",
        "A technician works on cables and electronics.",
    ),
    Source(
        "router", 7140937,
        "https://www.pexels.com/video/a-close-up-video-of-cable-wires-connected-on-a-motherboard-7140937/",
        "MrColo",
        "Network cables and router lights in close-up.",
    ),
    Source(
        "hacker_cell", 5377521,
        "https://www.pexels.com/video/people-hacking-the-system-while-wearing-a-hacker-mask-5377521/",
        "Tima Miroshnichenko",
        "Two anonymous operators work at multiple computers.",
    ),
    Source(
        "screen_operator", 8720760,
        "https://www.pexels.com/video/woman-typing-and-looking-at-multiple-computers-8720760/",
        "cottonbro studio",
        "A woman works among vintage screens and cables.",
    ),
    Source(
        "network_room", 8721654,
        "https://www.pexels.com/video/woman-sitting-in-front-of-computers-8721654/",
        "cottonbro studio",
        "An operator sits inside a dense room of screens and wires.",
    ),
    Source(
        "mixing_cables", 12315281,
        "https://www.pexels.com/video/close-up-of-cables-and-switches-on-a-mixing-console-12315281/",
        "utopia 36",
        "Cables and signal controls move through a mixing console.",
    ),
    Source(
        "city_grid", 17980449,
        "https://www.pexels.com/video/city-in-the-night-4k-hyperlapse-17980449/",
        "Delsograf Free",
        "A night city hyperlapse becomes a living network.",
    ),
    Source(
        "antenna", 30449790,
        "https://www.pexels.com/video/dramatic-sunset-over-silhouetted-antenna-hill-30449790/",
        "CESAR A RAMIREZ VALLEJO TRAPHITHO",
        "Communication antennas stand against a dramatic sky.",
    ),
    Source(
        "tunnel_drive", 33938673,
        "https://www.pexels.com/video/moody-night-drive-through-a-dimly-lit-tunnel-33938673/",
        "정규송 Nui MALAMA",
        "A vehicle moves through a dark underground tunnel.",
    ),
    Source(
        "city_aerial", 9731129,
        "https://www.pexels.com/video/aerial-view-hyperlapse-of-city-at-night-9731129/",
        "Jose Valdivia",
        "The city pulses from above at night.",
    ),
    Source(
        "laptop_close", 29624964,
        "https://www.pexels.com/video/closing-a-laptop-on-a-wooden-desk-29624964/",
        "Jakub Zerdzicki",
        "A hand decisively closes a laptop.",
    ),
]

SOURCE_BY_KEY = {source.key: source for source in SOURCES}

LONG_KEYS = [
    "neon_signal",
    "alley_walk",
    "hooded_portrait",
    "tunnel_silhouettes",
    "underground_group",
    "dark_exchange",
    "wiring",
    "router",
    "hacker_cell",
    "screen_operator",
]
MEDIUM_KEYS = [
    "network_room",
    "mixing_cables",
    "hooded_portrait",
    "city_grid",
    "antenna",
    "tunnel_drive",
    "underground_group",
    "city_aerial",
]
FAST_KEYS = [
    "hacker_cell",
    "router",
    "screen_operator",
    "city_grid",
    "tunnel_silhouettes",
    "network_room",
]
BEAT_KEYS = [
    "alley_walk",
    "mixing_cables",
    "router",
    "hacker_cell",
    "antenna",
    "city_aerial",
]
FLASH_KEYS = [
    "neon_signal",
    "hooded_portrait",
    "tunnel_silhouettes",
    "underground_group",
    "dark_exchange",
    "wiring",
    "router",
    "hacker_cell",
    "screen_operator",
    "network_room",
]

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
)


def log(message: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    with (OUT / "render_v18.log").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    log("$ " + " ".join(command))
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        with (OUT / "ffmpeg_v18.log").open("a", encoding="utf-8") as handle:
            handle.write(result.stdout)
            if not result.stdout.endswith("\n"):
                handle.write("\n")
    if check and result.returncode != 0:
        tail = "\n".join(result.stdout.splitlines()[-60:])
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{tail}")
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffprobe(path: Path) -> dict[str, Any]:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,width,height,r_frame_rate,avg_frame_rate,nb_frames,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(result.stdout)


def video_meta(path: Path) -> tuple[float, int, int]:
    data = ffprobe(path)
    duration = float(data["format"]["duration"])
    stream = next(item for item in data["streams"] if item.get("codec_type") == "video")
    return duration, int(stream["width"]), int(stream["height"])


def download_stream(url: str, destination: Path, referer: str | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Referer": referer} if referer else {}
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    with SESSION.get(url, headers=headers, stream=True, timeout=(30, 300), allow_redirects=True) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    handle.write(chunk)
        if temporary.stat().st_size < 250_000:
            sample = temporary.read_bytes()[:500].lower()
            if b"<html" in sample or b"<!doctype" in sample or "text/html" in content_type:
                raise RuntimeError(f"Expected media but received HTML from {url}")
    temporary.replace(destination)


def pexels_candidates(page_url: str) -> list[tuple[int, int, str]]:
    response = SESSION.get(page_url, timeout=(30, 120))
    response.raise_for_status()
    body = html.unescape(response.text).replace("\\u002F", "/").replace("\\/", "/")
    candidates: list[tuple[int, int, str]] = []
    object_pattern = re.compile(
        r'"width"\s*:\s*(\d+)\s*,\s*"height"\s*:\s*(\d+).*?'
        r'"link"\s*:\s*"(https://videos\.pexels\.com/video-files/[^"]+?\.mp4[^"]*)"',
        flags=re.S,
    )
    for width, height, link in object_pattern.findall(body):
        candidates.append((int(width), int(height), link.replace("&amp;", "&")))
    if not candidates:
        for link in re.findall(r"https://videos\.pexels\.com/video-files/[^\"'<>\s]+?\.mp4[^\"'<>\s]*", body):
            candidates.append((0, 0, link.replace("&amp;", "&")))
    unique: dict[str, tuple[int, int, str]] = {}
    for item in candidates:
        unique[item[2]] = item
    return sorted(
        unique.values(),
        key=lambda item: (
            item[0] >= 1920 and item[1] >= 1080,
            item[0] * item[1],
        ),
        reverse=True,
    )


def download_pexels(source: Source) -> Path:
    destination = FOOTAGE_DIR / f"{source.video_id}_{source.key}.mp4"
    if destination.exists() and destination.stat().st_size > 250_000:
        try:
            duration, width, height = video_meta(destination)
            if duration >= 2.5 and width >= 640 and height >= 360:
                log(f"Using cached {source.key}: {width}x{height}, {duration:.2f}s")
                return destination
        except Exception:
            destination.unlink(missing_ok=True)

    errors: list[str] = []
    direct = f"https://www.pexels.com/download/video/{source.video_id}/"
    try:
        log(f"Downloading {source.key} from Pexels direct endpoint")
        download_stream(direct, destination, referer=source.page_url)
        duration, width, height = video_meta(destination)
        if duration >= 2.5 and width >= 640 and height >= 360:
            log(f"Selected {source.key}: {width}x{height}, {duration:.2f}s")
            return destination
        raise RuntimeError(f"Unexpected media dimensions/duration {width}x{height}, {duration:.2f}s")
    except Exception as exc:
        errors.append(f"direct endpoint: {exc}")
        destination.unlink(missing_ok=True)

    try:
        for width, height, candidate in pexels_candidates(source.page_url):
            try:
                log(f"Trying parsed Pexels asset for {source.key}: {width}x{height}")
                download_stream(candidate, destination, referer=source.page_url)
                duration, actual_width, actual_height = video_meta(destination)
                if duration >= 2.5 and actual_width >= 640 and actual_height >= 360:
                    log(f"Selected {source.key}: {actual_width}x{actual_height}, {duration:.2f}s")
                    return destination
                destination.unlink(missing_ok=True)
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                destination.unlink(missing_ok=True)
    except Exception as exc:
        errors.append(f"page parsing: {exc}")

    raise RuntimeError(f"Could not download Pexels source {source.key}: " + " | ".join(errors[-8:]))


def download_music() -> Path:
    destination = ASSETS / "subway_cell.mp3"
    if destination.exists() and destination.stat().st_size > 1_000_000:
        log("Using cached soundtrack")
        return destination
    log(f"Downloading soundtrack: {MUSIC_TITLE} by {MUSIC_ARTIST}")
    download_stream(MUSIC_DIRECT, destination, referer=MUSIC_PAGE)
    if destination.stat().st_size < 1_000_000:
        raise RuntimeError("Soundtrack download is unexpectedly small")
    return destination


def mean_rms(rms: np.ndarray, times: np.ndarray, start: float, end: float) -> float:
    mask = (times >= start) & (times < end)
    if not np.any(mask):
        return 0.0
    return float(np.mean(rms[mask]))


def select_music_window(music_path: Path, duration_needed: float = 55.0) -> dict[str, Any]:
    log("Analyzing soundtrack and locating a low-to-high dramatic arc")
    y, sr = librosa.load(str(music_path), sr=22050, mono=True)
    track_duration = float(librosa.get_duration(y=y, sr=sr))
    hop = 512
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo_array, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop,
        units="frames",
    )
    detected_tempo = float(np.atleast_1d(tempo_array)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
    if len(beat_times) < 8:
        beat_times = np.arange(0.0, track_duration, 60.0 / TRACK_BPM)
    log(f"Detected tempo {detected_tempo:.2f} BPM; published tempo {TRACK_BPM:.1f} BPM")

    candidate_starts = [
        float(value)
        for value in beat_times
        if value >= 4.0 and value + duration_needed + 2.0 < track_duration
    ]
    if not candidate_starts:
        candidate_starts = list(np.arange(4.0, max(4.01, track_duration - duration_needed - 2.0), 60.0 / TRACK_BPM))
    if not candidate_starts:
        raise RuntimeError(f"Track is too short: {track_duration:.2f}s")

    onset_times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=hop)
    best: tuple[float, float] | None = None
    for start in candidate_starts:
        end = start + duration_needed
        intro = mean_rms(rms, rms_times, start, start + 8.0)
        first_middle = mean_rms(rms, rms_times, start + 16.0, start + 30.0)
        late_middle = mean_rms(rms, rms_times, start + 30.0, start + 43.0)
        climax = mean_rms(rms, rms_times, start + 46.0, end)
        peak_mask = (rms_times >= start + 49.0) & (rms_times < end)
        peak = float(np.max(rms[peak_mask])) if np.any(peak_mask) else climax
        onset_intro = onset_env[(onset_times >= start) & (onset_times < start + 10.0)]
        onset_climax = onset_env[(onset_times >= start + 44.0) & (onset_times < end)]
        onset_gain = (
            float(np.mean(onset_climax)) - float(np.mean(onset_intro))
            if len(onset_climax) and len(onset_intro)
            else 0.0
        )
        score = (
            (first_middle - intro) * 1.8
            + (late_middle - intro) * 3.2
            + (climax - intro) * 6.5
            + peak * 1.8
            + onset_gain * 0.04
            - intro * 0.45
        )
        if best is None or score > best[0]:
            best = (score, start)
    assert best is not None
    selected_start = best[1]
    log(
        f"Selected soundtrack window {selected_start:.3f}s–"
        f"{selected_start + duration_needed:.3f}s"
    )
    return {
        "track_duration": track_duration,
        "detected_tempo_bpm": detected_tempo,
        "published_tempo_bpm": TRACK_BPM,
        "selected_start_seconds": selected_start,
        "selected_end_seconds": selected_start + duration_needed,
    }


def make_soundtrack(music_path: Path, selection: dict[str, Any]) -> Path:
    output = OUT / "S0VRAN_V18_SOUNDTRACK_EDIT.mp3"
    start = float(selection["selected_start_seconds"])
    story_duration = STORY_FRAMES / FPS
    main_end = start + story_duration - 0.25
    tail_start = max(start, main_end - 1.3)
    filter_complex = (
        f"[0:a]atrim=start={start:.6f}:end={main_end:.6f},"
        "asetpts=PTS-STARTPTS,aresample=48000,"
        "afade=t=in:st=0:d=0.45,"
        f"afade=t=out:st={story_duration - 0.85:.6f}:d=0.60,"
        f"apad=pad_dur={TOTAL_DURATION + 1.0:.3f}[main];"
        f"[0:a]atrim=start={tail_start:.6f}:end={main_end:.6f},"
        "asetpts=PTS-STARTPTS,aresample=48000,"
        "volume=0.48,"
        "aecho=0.8:0.86:620|1240|2480:0.34|0.21|0.12,"
        "lowpass=f=1500,"
        f"adelay={int((story_duration - 1.0) * 1000)}|{int((story_duration - 1.0) * 1000)},"
        f"apad=pad_dur={TOTAL_DURATION:.3f}[tail];"
        "[main][tail]amix=inputs=2:duration=longest:normalize=0,"
        f"atrim=duration={TOTAL_DURATION:.6f},"
        f"afade=t=out:st={TOTAL_DURATION - 1.4:.6f}:d=1.4,"
        "loudnorm=I=-14.0:TP=-1.5:LRA=9[out]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(music_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[out]",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            str(output),
        ]
    )
    return output


def source_start(duration: float, needed: float, fraction: float) -> float:
    available = max(0.0, duration - needed - 0.08)
    return max(0.0, min(available, available * fraction))


def grade_filter(width: int, height: int, speed: float, variant: str) -> str:
    common = [
        f"setpts=PTS/{speed:.6f}",
        f"fps={FPS}",
    ]
    if width >= height * 1.25:
        common.extend(
            [
                f"scale={WIDTH}:{CONTENT_HEIGHT}:force_original_aspect_ratio=increase",
                f"crop={WIDTH}:{CONTENT_HEIGHT}",
                "eq=contrast=1.20:brightness=-0.065:saturation=0.72:gamma=0.94",
                "colorbalance=bs=0.055:rs=-0.025",
                "vignette=PI/4.8",
                "unsharp=5:5:0.35:5:5:0",
                f"pad={WIDTH}:{HEIGHT}:0:{(HEIGHT - CONTENT_HEIGHT) // 2}:black",
            ]
        )
    else:
        common.extend(
            [
                f"split=2[bg][fg]",
            ]
        )
        return (
            f"setpts=PTS/{speed:.6f},fps={FPS},split=2[bg][fg];"
            f"[bg]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},boxblur=24:2,"
            "eq=contrast=1.15:brightness=-0.09:saturation=0.48[bg2];"
            f"[fg]scale={WIDTH}:{CONTENT_HEIGHT}:force_original_aspect_ratio=decrease,"
            "eq=contrast=1.20:brightness=-0.065:saturation=0.72:gamma=0.94,"
            "colorbalance=bs=0.055:rs=-0.025,vignette=PI/4.8[fg2];"
            f"[bg2][fg2]overlay=(W-w)/2:(H-h)/2,format=yuv420p"
        )
    if variant == "red":
        common.append("colorchannelmixer=rr=1.22:rg=0.05:gg=0.62:bb=0.48")
    elif variant == "mono":
        common.append("hue=s=0")
    elif variant == "negative":
        common.extend(["negate", "eq=contrast=1.22:brightness=-0.02:saturation=0.75"])
    elif variant == "flash":
        common.extend(["eq=contrast=1.40:brightness=0.02:saturation=0.28", "noise=alls=4:allf=t+u"])
    else:
        common.append("noise=alls=1.2:allf=t+u")
    common.append("format=yuv420p")
    return ",".join(common)


def render_segment(
    source_path: Path,
    output_path: Path,
    frames: int,
    fraction: float,
    speed: float = 1.0,
    variant: str = "normal",
) -> None:
    duration, width, height = video_meta(source_path)
    output_duration = frames / FPS
    needed = output_duration * speed + 0.18
    start = source_start(duration, needed, fraction)
    filter_value = grade_filter(width, height, speed, variant)
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.6f}",
            "-i",
            str(source_path),
            "-an",
            "-vf",
            filter_value,
            "-frames:v",
            str(frames),
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "16",
            "-g",
            "48",
            "-keyint_min",
            "48",
            "-sc_threshold",
            "0",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
    )


def make_black_segment() -> Path:
    output = SEGMENTS_DIR / "blackout.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}",
            "-frames:v",
            str(BLACKOUT_FRAMES),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "10",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )
    return output


def load_font(size: int, light: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf" if light else "",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def draw_spaced_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    spacing: int,
    anchor: str = "mm",
) -> None:
    widths = [draw.textlength(char, font=font) for char in text]
    total = sum(widths) + spacing * max(0, len(text) - 1)
    x, y = xy
    if anchor == "mm":
        x -= total / 2
    for char, width in zip(text, widths):
        draw.text((x, y), char, font=font, fill=fill, anchor="lm")
        x += width + spacing


def make_brand_card() -> tuple[Path, Path]:
    base = Image.new("RGBA", (WIDTH, HEIGHT), (2, 4, 7, 255))
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    logo_font = load_font(142, light=True)
    tag_font = load_font(31, light=False)

    center_x = WIDTH / 2
    logo_y = 476
    tag_y = 608
    draw_spaced_text(
        glow_draw,
        (center_x, logo_y),
        "S0VRAN",
        logo_font,
        (100, 205, 255, 175),
        18,
    )
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    base = Image.alpha_composite(base, glow)

    draw = ImageDraw.Draw(base)
    draw_spaced_text(
        draw,
        (center_x, logo_y),
        "S0VRAN",
        logo_font,
        (238, 246, 250, 255),
        18,
    )
    draw.line((724, 558, 1196, 558), fill=(62, 104, 126, 210), width=1)
    draw_spaced_text(
        draw,
        (center_x, tag_y),
        "A NETWORK WITH NO MASTER.",
        tag_font,
        (151, 177, 190, 235),
        7,
    )

    rng = np.random.default_rng(18)
    for _ in range(90):
        x = int(rng.integers(160, WIDTH - 160))
        y = int(rng.integers(180, HEIGHT - 180))
        alpha = int(rng.integers(18, 50))
        radius = int(rng.integers(1, 3))
        ImageDraw.Draw(base).ellipse((x - radius, y - radius, x + radius, y + radius), fill=(72, 136, 165, alpha))

    png = STILLS_DIR / "brand_card.png"
    base.convert("RGB").save(png, quality=95)

    video = SEGMENTS_DIR / "brand.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(png),
            "-vf",
            (
                f"zoompan=z='min(zoom+0.00018,1.018)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={BRAND_FRAMES}:s={WIDTH}x{HEIGHT}:fps={FPS},"
                "fade=t=in:st=0:d=1.1,"
                f"fade=t=out:st={(BRAND_FRAMES / FPS) - 1.0:.3f}:d=1.0,"
                "noise=alls=1.0:allf=t+u,format=yuv420p"
            ),
            "-frames:v",
            str(BRAND_FRAMES),
            "-r",
            str(FPS),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "14",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ]
    )
    return png, video


def make_schedule() -> list[dict[str, Any]]:
    schedule: list[dict[str, Any]] = []
    fractions = [0.06, 0.18, 0.30, 0.42, 0.54, 0.66, 0.78, 0.25, 0.48, 0.72]
    for index, key in enumerate(LONG_KEYS):
        schedule.append(
            {
                "key": key,
                "frames": 79,
                "fraction": fractions[index],
                "speed": 0.94 + 0.02 * (index % 4),
                "variant": "normal",
                "stage": "long",
            }
        )
    for index, key in enumerate(MEDIUM_KEYS):
        schedule.append(
            {
                "key": key,
                "frames": 40,
                "fraction": (0.13 + 0.11 * index) % 0.82,
                "speed": 1.02 + 0.04 * (index % 3),
                "variant": "normal" if index < 5 else "red",
                "stage": "medium",
            }
        )
    fast_variants = ["normal", "red", "mono", "normal", "red", "flash"]
    for index, key in enumerate(FAST_KEYS):
        schedule.append(
            {
                "key": key,
                "frames": 20,
                "fraction": (0.21 + 0.13 * index) % 0.82,
                "speed": 1.12 + 0.08 * (index % 3),
                "variant": fast_variants[index],
                "stage": "fast",
            }
        )
    beat_variants = ["red", "normal", "mono", "negative", "red", "flash"]
    for index, key in enumerate(BEAT_KEYS):
        schedule.append(
            {
                "key": key,
                "frames": 10,
                "fraction": (0.17 + 0.15 * index) % 0.84,
                "speed": 1.28 + 0.12 * (index % 2),
                "variant": beat_variants[index],
                "stage": "beat",
            }
        )
    flash_variants = ["negative", "red", "mono", "flash", "red", "negative", "flash", "mono", "red", "flash"]
    for index, key in enumerate(FLASH_KEYS):
        schedule.append(
            {
                "key": key,
                "frames": 3,
                "fraction": (0.09 + 0.087 * index) % 0.88,
                "speed": 1.0,
                "variant": flash_variants[index],
                "stage": "flash",
            }
        )
    total = sum(item["frames"] for item in schedule)
    if total != STORY_FRAMES:
        raise AssertionError(f"Schedule frames {total} != story frames {STORY_FRAMES}")
    return schedule


def make_story_segments(downloaded: dict[str, Path]) -> tuple[list[Path], list[dict[str, Any]]]:
    schedule = make_schedule()
    paths: list[Path] = []
    timeline: list[dict[str, Any]] = []
    frame_cursor = 0
    for index, item in enumerate(schedule):
        output = SEGMENTS_DIR / f"story_{index:03d}_{item['key']}.mp4"
        render_segment(
            downloaded[item["key"]],
            output,
            frames=int(item["frames"]),
            fraction=float(item["fraction"]),
            speed=float(item["speed"]),
            variant=str(item["variant"]),
        )
        start = frame_cursor / FPS
        frame_cursor += int(item["frames"])
        timeline.append(
            {
                **item,
                "index": index,
                "start_seconds": start,
                "end_seconds": frame_cursor / FPS,
            }
        )
        paths.append(output)
    return paths, timeline


def concatenate_video(parts: list[Path], destination: Path) -> None:
    concat_file = ASSETS / "concat_v18.txt"
    with concat_file.open("w", encoding="utf-8") as handle:
        for part in parts:
            escaped = str(part.resolve()).replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-an",
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "15",
            "-g",
            "48",
            "-keyint_min",
            "48",
            "-sc_threshold",
            "0",
            "-pix_fmt",
            "yuv420p",
            destination.as_posix(),
        ]
    )


def mux_master(silent_video: Path, soundtrack: Path) -> tuple[Path, Path]:
    master = OUT / "S0VRAN_THE_RELAY_V18_MASTER.mp4"
    web = OUT / "S0VRAN_THE_RELAY_V18_WEB.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(soundtrack),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "14",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            "-t",
            f"{TOTAL_DURATION:.6f}",
            str(master),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(master),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "21",
            "-profile:v",
            "high",
            "-level",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(web),
        ]
    )
    return master, web


def extract_frame(video: Path, time_seconds: float, output: Path) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{time_seconds:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ]
    )


def make_contact_sheet(video: Path, output: Path, times: list[float], columns: int, thumb_width: int = 480) -> None:
    frames: list[Image.Image] = []
    for index, value in enumerate(times):
        still = STILLS_DIR / f"contact_{output.stem}_{index:02d}.jpg"
        extract_frame(video, value, still)
        image = Image.open(still).convert("RGB")
        scale = thumb_width / image.width
        image = image.resize((thumb_width, int(image.height * scale)), Image.Resampling.LANCZOS)
        frames.append(image)
    rows = math.ceil(len(frames) / columns)
    thumb_height = frames[0].height
    sheet = Image.new("RGB", (columns * thumb_width, rows * thumb_height), (0, 0, 0))
    for index, image in enumerate(frames):
        x = (index % columns) * thumb_width
        y = (index // columns) * thumb_height
        sheet.paste(image, (x, y))
    sheet.save(output, quality=91, optimize=True)


def write_documents(
    downloaded: dict[str, Path],
    selection: dict[str, Any],
    timeline: list[dict[str, Any]],
    master: Path,
    web: Path,
) -> None:
    source_records = []
    for source in SOURCES:
        path = downloaded[source.key]
        duration, width, height = video_meta(path)
        source_records.append(
            {
                "key": source.key,
                "pexels_video_id": source.video_id,
                "page_url": source.page_url,
                "download_url": f"https://www.pexels.com/download/video/{source.video_id}/",
                "creator": source.creator,
                "description": source.description,
                "local_filename": path.name,
                "duration_seconds": duration,
                "width": width,
                "height": height,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "project": "S0VRAN — THE RELAY",
        "version": 18,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "music": {
            "title": MUSIC_TITLE,
            "artist": MUSIC_ARTIST,
            "page_url": MUSIC_PAGE,
            "download_url": MUSIC_DIRECT,
            "license": "Creative Commons Attribution 4.0 International",
            "selected_window": selection,
        },
        "footage": source_records,
        "output": {
            "master": master.name,
            "web": web.name,
            "duration_seconds": TOTAL_DURATION,
            "fps": FPS,
            "resolution": [WIDTH, HEIGHT],
        },
        "prior_s0vran_footage_reused": False,
    }
    (OUT / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    cut_times = [item["start_seconds"] for item in timeline[1:]]
    quarter = (60.0 / TRACK_BPM) / 4.0
    offsets = [min(value % quarter, quarter - (value % quarter)) for value in cut_times]
    qa = {
        "project": "S0VRAN — THE RELAY",
        "version": 18,
        "video": {
            "fps": FPS,
            "total_frames": TOTAL_FRAMES,
            "duration_seconds": TOTAL_DURATION,
            "story_frames": STORY_FRAMES,
            "blackout_frames": BLACKOUT_FRAMES,
            "control_frames": CONTROL_FRAMES,
            "brand_frames": BRAND_FRAMES,
            "brand_hold_seconds": BRAND_FRAMES / FPS,
        },
        "music": selection,
        "edit_sync": {
            "published_bpm": TRACK_BPM,
            "quarter_beat_grid_seconds": quarter,
            "cut_count": len(cut_times),
            "average_cut_offset_milliseconds": float(np.mean(offsets) * 1000.0),
            "maximum_cut_offset_milliseconds": float(np.max(offsets) * 1000.0),
        },
        "story_timeline": timeline,
        "footage_reuse_check": {
            "new_pexels_video_ids": [source.video_id for source in SOURCES],
            "reused_previous_video_ids": [],
        },
    }
    (OUT / "EDIT_QA.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")

    script = """# S0VRAN — THE RELAY

## Concept

At 2:13 a.m., a neon light begins pulsing in an empty street. The pattern is not an advertisement. It is an invitation.

Anonymous figures follow the signal through separate alleys and underground passages. They do not know one another above ground. Below it, they form a relay: one person brings access, another brings hardware, another brings a route. Cables connect. Screens wake. A hidden network spreads from a concrete room into towers, tunnels, and the illuminated grid of the city.

No single person controls what the network becomes. That is its strength — until the system begins accelerating beyond the people who built it. The edit contracts with the soundtrack from long, controlled observations to fractions of a beat. Faces, cables, tunnels, antennas, and city lights collide too quickly to own.

Then one operator closes the machine.

The signal stops.

S0VRAN appears only after the network no longer has a master.

## Picture structure

- **The pulse:** a neon light flashes in an otherwise empty night.
- **The invitation:** a hooded figure notices; other silhouettes move below the city.
- **The cell:** people gather in a concrete underground passage.
- **The exchange:** access passes from person to person without explanation.
- **The relay:** cables connect, machines wake, and operators begin working.
- **The spread:** the hidden room becomes city lights, antennas, tunnels, and infrastructure.
- **The surge:** full-beat cuts contract into partial-beat flashes.
- **The interruption:** the screen goes black.
- **The choice:** a laptop closes; participation ends.
- **The brand:** **S0VRAN — A NETWORK WITH NO MASTER.**

## Editorial rule

There are no explanatory captions, no instructional hacking imagery, and no product mockup. The story is carried by physical movement, anonymous faces, repeated signal imagery, and increasingly compressed rhythm.
"""
    (OUT / "S0VRAN_V18_STORY_SCRIPT.md").write_text(script, encoding="utf-8")

    credits_lines = [
        "S0VRAN — THE RELAY (V18)",
        "",
        "MUSIC",
        f'"{MUSIC_TITLE}" by {MUSIC_ARTIST}',
        "https://www.silvermansound.com",
        "Royalty Free Music by https://www.free-stock-music.com",
        "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "https://creativecommons.org/licenses/by/4.0/",
        "",
        "LIVE-ACTION FOOTAGE",
        "All clips were sourced from Pexels and modified for this film.",
        "Pexels attribution is not required, but creator credits are included below.",
        "",
    ]
    for source in SOURCES:
        credits_lines.append(f"- {source.creator}: {source.page_url}")
    credits_lines.extend(
        [
            "",
            "PUBLICATION NOTE",
            "Do not imply that any person depicted endorses S0VRAN.",
            "The film is a fictional brand concept, not a depiction of actual criminal activity.",
        ]
    )
    (OUT / "CREDITS.txt").write_text("\n".join(credits_lines) + "\n", encoding="utf-8")


def main() -> None:
    random.seed(18)
    for directory in [ASSETS, FOOTAGE_DIR, SEGMENTS_DIR, STILLS_DIR, OUT]:
        directory.mkdir(parents=True, exist_ok=True)
    for log_file in [OUT / "render_v18.log", OUT / "ffmpeg_v18.log"]:
        log_file.unlink(missing_ok=True)

    log("Starting S0VRAN V18 — THE RELAY")
    music_path = download_music()
    selection = select_music_window(music_path)
    soundtrack = make_soundtrack(music_path, selection)

    downloaded: dict[str, Path] = {}
    for source in SOURCES:
        downloaded[source.key] = download_pexels(source)

    story_parts, timeline = make_story_segments(downloaded)
    blackout = make_black_segment()

    control = SEGMENTS_DIR / "control_laptop_close.mp4"
    render_segment(
        downloaded["laptop_close"],
        control,
        frames=CONTROL_FRAMES,
        fraction=0.28,
        speed=0.82,
        variant="normal",
    )
    _, brand = make_brand_card()

    silent_video = ASSETS / "silent_v18.mp4"
    concatenate_video(story_parts + [blackout, control, brand], silent_video)
    master, web = mux_master(silent_video, soundtrack)

    poster = OUT / "S0VRAN_V18_POSTER.jpg"
    extract_frame(master, 63.0, poster)
    make_contact_sheet(
        master,
        OUT / "S0VRAN_V18_CONTACT.jpg",
        [1.0, 5.0, 9.5, 14.0, 19.0, 24.0, 30.0, 36.0, 42.0, 47.5, 51.0, 53.5, 55.2, 57.2, 59.0, 63.0],
        columns=4,
    )
    make_contact_sheet(
        master,
        OUT / "S0VRAN_V18_CLIMAX_CONTACT.jpg",
        [49.0, 49.5, 50.0, 50.5, 51.0, 51.5, 52.0, 52.5, 53.0, 53.5, 54.0, 54.4, 54.7, 54.9, 55.1, 56.0],
        columns=4,
        thumb_width=480,
    )
    make_contact_sheet(
        master,
        OUT / "S0VRAN_V18_END_CHECK.jpg",
        [55.0, 55.8, 56.4, 57.0, 58.0, 59.0, 60.0, 61.0, 63.0, 65.0, 67.0, 68.3],
        columns=4,
        thumb_width=480,
    )

    write_documents(downloaded, selection, timeline, master, web)

    final_meta = ffprobe(master)
    log(f"Finished master: {master} ({master.stat().st_size / 1_000_000:.1f} MB)")
    log(f"Finished web cut: {web} ({web.stat().st_size / 1_000_000:.1f} MB)")
    log(f"Total duration target: {TOTAL_DURATION:.3f}s")
    log(json.dumps(final_meta, indent=2)[:2000])


if __name__ == "__main__":
    main()
