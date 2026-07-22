#!/usr/bin/env python3
import base64,lzma
from pathlib import Path
root=Path(__file__).parent
payload=(root/"p0.txt").read_text(encoding="utf-8").strip()
source=lzma.decompress(base64.b64decode(payload)).decode("utf-8")
exec(compile(source,__file__,"exec"))
