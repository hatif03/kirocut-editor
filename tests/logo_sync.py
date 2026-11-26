#!/usr/bin/env python3
"""Put docs/logo.svg into every place the pages draw the mark: the favicon (a data URI) and each inline <svg> copy.

    py tests/logo_sync.py          rewrite the copies
    py tests/logo_sync.py --check  exit 1 when a copy differs (check_plugins.py runs this)
"""
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "docs" / "logo.svg"
PAGES = [ROOT / "plugins" / "kirocut" / "lib" / "kirocut" / n for n in ("home.html", "review.html")]
# an inline copy: from the purple tile to the end of the mark (the old crossed cut or the film strip)
INLINE = re.compile(r'(?:<clipPath id="kc[a-z]-\d+">(?:(?!</clipPath>).)*</clipPath>)?'
                    r'<rect width="64" height="64" rx="16" fill="#7B5CFF"/>.*?(?=</svg>)', re.S)
FAVICON = re.compile(r'<link rel="icon" href="data:image/svg\+xml,[^"]*">')


def body(svg, cid):
    """The mark's inside (no outer <svg>, no newlines), its clip id made unique for this copy."""
    inner = re.sub(r"^\s*<svg[^>]*>|</svg>\s*$", "", svg.strip())
    inner = re.sub(r">\s+<", "><", inner).strip()
    i = inner.index('<rect width="64" height="64" rx="16" fill="#7B5CFF"/>')
    inner = inner[i:] if "<clipPath" not in inner[:i] else inner
    clip = re.search(r'<clipPath id="kc-tile">.*?</clipPath>', inner)
    inner = inner.replace(clip.group(), "") if clip else inner
    defs = clip.group().replace('id="kc-tile"', f'id="{cid}"') if clip else ""
    return defs + inner.replace("url(#kc-tile)", f"url(#{cid})")


def favicon(svg):
    one = re.sub(r">\s+<", "><", svg.strip()).replace('"', "'")
    return '<link rel="icon" href="data:image/svg+xml,' + urllib.parse.quote(one, safe="=:/ '") + '">'


def synced(text, svg, prefix):
    n = [0]

    def inline(m):
        n[0] += 1
        return body(svg, f"{prefix}-{n[0]}")
    text = INLINE.sub(inline, text)
    return FAVICON.sub(lambda m: favicon(svg), text), n[0]


def main(argv):
    svg = LOGO.read_text(encoding="utf-8")
    bad = []
    for p in PAGES:
        t = p.read_text(encoding="utf-8")
        new, n = synced(t, svg, "kc" + p.stem[0])
        if not n:
            bad.append(f"{p.name}: no copy of the mark found")
        if new != t:
            if "--check" in argv:
                bad.append(f"{p.relative_to(ROOT).as_posix()}: the mark differs from docs/logo.svg (run py tests/logo_sync.py)")
            else:
                p.write_text(new, encoding="utf-8", newline="")
                print(f"{p.name}: {n} copies of the mark")
    for b in bad:
        print(b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
