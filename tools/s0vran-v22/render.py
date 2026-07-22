#!/usr/bin/env python3
import base64,lzma
from pathlib import Path
root=Path(__file__).parent
payload="".join((root/f"p{i}.txt").read_text(encoding="utf-8").strip() for i in range(2))
source=lzma.decompress(base64.b64decode(payload)).decode("utf-8")
# Normalize FFmpeg shorthand decimals and maintain compatibility with FFmpeg 4/6.
source=source.replace("=.", "=0.")
source=source.replace("lowpass=f=12800", "lowpass=f=9800")
source=source.replace(",lowpass=f='if(lt(t,60),18000,1900)':eval=frame", ",lowpass=f=18000")
exec(compile(source,__file__,"exec"))
