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
source=source.replace("d=.05", "d=0.05")
source=source.replace("d=.3", "d=0.3")
exec(compile(source,__file__,"exec"))
