#!/usr/bin/env python3
import base64
import lzma
from pathlib import Path

root = Path(__file__).parent
payload = "".join((root / f"p{i}.txt").read_text(encoding="utf-8").strip() for i in range(3))
source = lzma.decompress(base64.b64decode(payload)).decode("utf-8")
# FFmpeg 6 rejects shorthand duration literals such as d=.55. Normalize every
# option-value decimal before executing the compressed render source.
source = source.replace("=.", "=0.")
# FFmpeg's lowpass filter does not evaluate time expressions in its frequency
# parameter. Keep the licensed track full-band while the supported volume
# expression ducks it beneath the brand card.
source = source.replace("lowpass=f='if(lt(t,59.5),18000,1600)':eval=frame,", "lowpass=f=18000,")
exec(compile(source, __file__, "exec"))
