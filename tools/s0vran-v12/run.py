#!/usr/bin/env python3
import ast
import base64
import lzma
import re
from pathlib import Path

loader_path = Path(__file__).with_name("render.py")
module = ast.parse(loader_path.read_text(encoding="utf-8"))
payload = None
for node in module.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "P" for t in node.targets):
        payload = ast.literal_eval(node.value)
        break
if not payload:
    raise RuntimeError("Could not extract render payload")
source = lzma.decompress(base64.b64decode(payload)).decode("utf-8")

old_download = '''    for page_url in page_urls:\n        try:\n            candidates = pexels_mp4_candidates(page_url)\n'''
new_download = '''    for page_url in page_urls:\n        try:\n            # Pexels exposes a stable download endpoint keyed by the video ID.\n            # It often remains available even when the HTML page challenges automated clients.\n            match = re.search(r"-(\\d+)/?$", page_url.rstrip("/"))\n            if match:\n                direct = f"https://www.pexels.com/download/video/{match.group(1)}/"\n                try:\n                    download_stream(direct, destination, referer=page_url)\n                    duration, width, height, _ = video_meta(destination)\n                    if duration >= 2.0 and width >= 960 and height >= 540:\n                        log(f"Selected Pexels direct asset {direct} ({width}x{height}, {duration:.2f}s)")\n                        return page_url, direct\n                    destination.unlink(missing_ok=True)\n                except Exception as exc:\n                    errors.append(f"direct {direct}: {exc}")\n                    destination.unlink(missing_ok=True)\n            candidates = pexels_mp4_candidates(page_url)\n'''
if old_download not in source:
    raise RuntimeError("Expected download function pattern was not found")
source = source.replace(old_download, new_download, 1)

replacement = '''def choose_music_window(music_path: Path) -> dict[str, Any]:
    log("Analyzing soundtrack tempo, beat phase, and energy arc")
    y, sr = librosa.load(str(music_path), sr=22050, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    hop = 512
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo_arr, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=hop, units="frames")
    tempo = float(np.atleast_1d(tempo_arr)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
    log(f"Detected {len(beat_times)} beats at {tempo:.2f} BPM across {duration:.2f}s")

    # Nightfall is published around 80 BPM, but beat trackers may report half-time
    # or double-time. Start on a detected beat, then preserve the original track speed
    # and use an exact 80-BPM edit grid (0.75 seconds per beat).
    candidate_starts = [float(t) for t in beat_times if t >= 8.0 and t + 45.0 <= duration - 0.5]
    if not candidate_starts:
        candidate_starts = [float(t) for t in np.arange(8.0, max(8.1, duration - 45.5), 0.75)]
    if not candidate_starts:
        raise RuntimeError(f"Soundtrack is too short for a 45-second edit window: {duration:.2f}s")

    best: tuple[float, float] | None = None
    for t0 in candidate_starts:
        t1 = t0 + 45.0
        first = mean_rms_between(rms, rms_times, t0, t0 + 9.0)
        middle = mean_rms_between(rms, rms_times, t0 + 17.0, t0 + 29.0)
        final = mean_rms_between(rms, rms_times, t1 - 9.0, t1)
        peak_mask = (rms_times >= t1 - 7.5) & (rms_times <= t1)
        peak = float(np.max(rms[peak_mask])) if np.any(peak_mask) else final
        onset_times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=hop)
        tail_mask = (onset_times >= t1 - 10.0) & (onset_times < t1)
        early_mask = (onset_times >= t0) & (onset_times < t0 + 10.0)
        tail_onsets = float(np.mean(onset_env[tail_mask])) if np.any(tail_mask) else 0.0
        early_onsets = float(np.mean(onset_env[early_mask])) if np.any(early_mask) else 0.0
        score = (final - first) * 7.0 + (final - middle) * 2.4 + peak * 1.4
        score += (tail_onsets - early_onsets) * 0.055
        score -= first * 0.45
        score += (t0 / max(duration, 1.0)) * 0.04
        if best is None or score > best[0]:
            best = (score, t0)

    assert best is not None
    start = best[1]
    end = start + 45.0
    log(f"Soundtrack selected: {start:.3f}s–{end:.3f}s, detected tempo {tempo:.2f} BPM; original speed preserved")
    return {
        "track_duration": duration,
        "detected_tempo_bpm": tempo,
        "selected_start_seconds": start,
        "selected_end_seconds": end,
        "selected_original_duration_seconds": 45.0,
        "target_main_duration_seconds": 45.0,
        "atempo_factor": 1.0,
        "beat_count": 60,
        "target_edit_tempo_bpm": 80.0,
        "video_fps": 24,
        "frames_per_target_beat": 18,
    }


def make_audio_edit'''
pattern = r'def choose_music_window\(music_path: Path\) -> dict\[str, Any\]:\n.*?\n\ndef make_audio_edit'
source, count = re.subn(pattern, replacement, source, count=1, flags=re.S)
if count != 1:
    raise RuntimeError("Could not patch soundtrack window selector")

exec(compile(source, str(loader_path), "exec"))
