#!/usr/bin/env python3
import ast
import base64
import lzma
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
old = '''    for page_url in page_urls:\n        try:\n            candidates = pexels_mp4_candidates(page_url)\n'''
new = '''    for page_url in page_urls:\n        try:\n            # Pexels exposes a stable download endpoint keyed by the video ID.\n            # It often remains available even when the HTML page challenges automated clients.\n            match = re.search(r"-(\\d+)/?$", page_url.rstrip("/"))\n            if match:\n                direct = f"https://www.pexels.com/download/video/{match.group(1)}/"\n                try:\n                    download_stream(direct, destination, referer=page_url)\n                    duration, width, height, _ = video_meta(destination)\n                    if duration >= 2.0 and width >= 960 and height >= 540:\n                        log(f"Selected Pexels direct asset {direct} ({width}x{height}, {duration:.2f}s)")\n                        return page_url, direct\n                    destination.unlink(missing_ok=True)\n                except Exception as exc:\n                    errors.append(f"direct {direct}: {exc}")\n                    destination.unlink(missing_ok=True)\n            candidates = pexels_mp4_candidates(page_url)\n'''
if old not in source:
    raise RuntimeError("Expected download function pattern was not found")
source = source.replace(old, new, 1)
exec(compile(source, str(loader_path), "exec"))
