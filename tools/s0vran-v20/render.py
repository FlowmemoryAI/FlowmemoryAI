#!/usr/bin/env python3
import base64,lzma
from pathlib import Path
root=Path(__file__).parent
payload="".join((root/f"p{i}.txt").read_text(encoding="utf-8").strip() for i in range(2))
source=lzma.decompress(base64.b64decode(payload)).decode("utf-8")
old='''    music_src = ASSETS / "signal_to_noise.mp3"\n    if not music_src.exists():\n        download(MUSIC_URL, music_src, referer=MUSIC_PAGE, min_bytes=1_000_000)\n'''
new='''    music_src = ASSETS / "signal_to_noise.mp3"\n    if not music_src.exists():\n        # Pull the artist-published CC-BY release through SoundCloud when the\n        # library CDN is unreachable from the render runner. The audio is not\n        # time-stretched; yt-dlp only obtains and converts the published stream.\n        template = str(music_src.with_suffix(".%(ext)s"))\n        run(["yt-dlp", "--no-playlist", "--force-overwrites", "-x",\n             "--audio-format", "mp3", "--audio-quality", "0",\n             "-o", template,\n             "https://soundcloud.com/scottbuckley/signal-to-noise-cc-by"])\n        if not music_src.exists():\n            raise RuntimeError("Soundtrack download did not produce the expected MP3")\n'''
if old not in source:
    raise RuntimeError("Could not patch soundtrack downloader")
source=source.replace(old,new,1)
exec(compile(source,__file__,"exec"))
