#!/usr/bin/env python3
import base64
import lzma
from pathlib import Path

root = Path(__file__).parent
payload = "".join((root / f"p{i}.txt").read_text(encoding="utf-8").strip() for i in range(4))
source = lzma.decompress(base64.b64decode(payload)).decode("utf-8")
# FFmpeg 6 requires a leading zero for duration values in the fade filter.
source = source.replace("d=.12", "d=0.12").replace("d=.25", "d=0.25")
exec(compile(source, __file__, "exec"))
