#!/usr/bin/env python3
import base64
import lzma
from pathlib import Path

root = Path(__file__).parent
payload = "".join((root / f"p{i}.txt").read_text(encoding="utf-8").strip() for i in range(4))
source = lzma.decompress(base64.b64decode(payload)).decode("utf-8")
exec(compile(source, __file__, "exec"))
