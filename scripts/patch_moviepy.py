#!/usr/bin/env python3
"""
MoviePy 1.x の deprecated_version_of 呼び出しを修正するパッチスクリプト。
Python 3.13 等で oldname= キーワードが受け付けられない場合に実行してください。

使い方:
  python scripts/patch_moviepy.py
  または
  .venv/bin/python scripts/patch_moviepy.py
"""
import sys
from pathlib import Path

def main():
    import moviepy
    base = Path(moviepy.__file__).parent
    target = base / "video" / "compositing" / "concatenate.py"
    if not target.exists():
        print(f"Not found: {target}", file=sys.stderr)
        return 1
    text = target.read_text(encoding="utf-8")
    if 'oldname="concatenate"' in text:
        text = text.replace(
            'concatenate = deprecated_version_of(concatenate_videoclips,\n                                    oldname="concatenate")',
            'concatenate = deprecated_version_of(concatenate_videoclips, "concatenate")'
        )
        target.write_text(text, encoding="utf-8")
        print("Patched:", target)
        return 0
    if 'deprecated_version_of(concatenate_videoclips, "concatenate")' in text:
        print("Already patched:", target)
        return 0
    print("Unexpected content, skip.", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
