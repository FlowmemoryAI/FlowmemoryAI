#!/usr/bin/env python3
import base64,lzma
from pathlib import Path
root=Path(__file__).parent
payload="".join((root/f"p{i}.txt").read_text(encoding="utf-8").strip() for i in range(2))
source=lzma.decompress(base64.b64decode(payload)).decode("utf-8")
old_music='''    music_src = ASSETS / "signal_to_noise.mp3"\n    if not music_src.exists():\n        download(MUSIC_URL, music_src, referer=MUSIC_PAGE, min_bytes=1_000_000)\n'''
new_music='''    music_src = ASSETS / "signal_to_noise.mp3"\n    if not music_src.exists():\n        # Pull the artist-published CC-BY release through SoundCloud when the\n        # library CDN is unreachable from the render runner. The audio is not\n        # time-stretched; yt-dlp only obtains and converts the published stream.\n        template = str(music_src.with_suffix(".%(ext)s"))\n        run(["yt-dlp", "--no-playlist", "--force-overwrites", "-x",\n             "--audio-format", "mp3", "--audio-quality", "0",\n             "-o", template,\n             "https://soundcloud.com/scottbuckley/signal-to-noise-cc-by"])\n        if not music_src.exists():\n            raise RuntimeError("Soundtrack download did not produce the expected MP3")\n'''
if old_music not in source:
    raise RuntimeError("Could not patch soundtrack downloader")
source=source.replace(old_music,new_music,1)
old_amb='''        if not p.exists():\n            download(str(info["url"]), p, referer=str(info["page"]), min_bytes=8_000)\n        ambience_paths[key] = p\n'''
new_amb='''        if not p.exists():\n            last_error = None\n            for attempt in range(3):\n                try:\n                    download(str(info["url"]), p, referer=str(info["page"]), min_bytes=8_000)\n                    break\n                except Exception as exc:\n                    last_error = exc\n                    p.unlink(missing_ok=True)\n                    time.sleep(4.0 * (attempt + 1))\n            if not p.exists():\n                if key == "thud":\n                    # A short non-musical impact only marks the physical disconnect.\n                    # Generate it locally rather than failing the complete render on\n                    # a rate-limited 50 KB ambience file.\n                    run(["ffmpeg", "-y", "-f", "lavfi", "-i",\n                         "sine=frequency=48:duration=0.55", "-af",\n                         "volume=0.42,afade=t=out:st=0.08:d=0.47",\n                         "-ar", "48000", "-ac", "2", "-c:a", "libvorbis", str(p)])\n                else:\n                    raise RuntimeError(f"Ambience download failed for {key}: {last_error}")\n        time.sleep(2.0)\n        ambience_paths[key] = p\n'''
if old_amb not in source:
    raise RuntimeError("Could not patch ambience downloader")
source=source.replace(old_amb,new_amb,1)
source=source.replace("volume=.055", "volume=0.055")
source=source.replace("atrim=0:.45", "atrim=0:0.45")
source=source.replace("volume=.18", "volume=0.18")
source=source.replace("d=.", "d=0.")
source=source.replace("end-.05", "end-0.40")
old_thumb='''        thumbs.append(Image.open(p).convert("RGB"))\n'''
new_thumb='''        if p.exists():\n            thumbs.append(Image.open(p).convert("RGB"))\n        elif thumbs:\n            thumbs.append(thumbs[-1].copy())\n        else:\n            thumbs.append(Image.new("RGB", (480, 270), "black"))\n'''
if old_thumb not in source:
    raise RuntimeError("Could not patch contact-sheet fallback")
source=source.replace(old_thumb,new_thumb,1)
old_scene='''    filt = f"setpts={1/speed:.8f}*PTS," + color_filter(look, duration, xalign, fade)\n'''
new_scene='''    filt = (f"setpts={1/speed:.8f}*PTS," + color_filter(look, duration, xalign, fade)\n            + f",tpad=stop_mode=clone:stop_duration={duration:.3f},trim=duration={duration:.3f},setpts=PTS-STARTPTS")\n'''
if old_scene not in source:
    raise RuntimeError("Could not patch exact scene duration")
source=source.replace(old_scene,new_scene,1)
old_input='''        "ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(src), "-an",\n'''
new_input='''        "ffmpeg", "-y", "-stream_loop", "-1", "-ss", f"{start:.3f}", "-i", str(src), "-an",\n'''
if old_input not in source:
    raise RuntimeError("Could not patch looping scene input")
source=source.replace(old_input,new_input,1)
exec(compile(source,__file__,"exec"))
