"""Download the latin subset of a Google Fonts css2 URL as self-hosted woff2.

usage: python tools/fetch_fonts.py "<css2 url>" > /tmp/fonts.css
Writes files to assets/fonts/ and prints matching @font-face rules
(paths relative to css/). Fonts on Google Fonts are SIL OFL licensed.
"""
import re
import sys
import urllib.request

from _server import ROOT

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read()


def main():
    css = get(sys.argv[1]).decode()
    out = ROOT / "assets" / "fonts"
    out.mkdir(parents=True, exist_ok=True)
    seen = {}
    faces = {}
    for comment, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, re.S):
        if comment != "latin":
            continue
        fam = re.search(r"font-family: '([^']+)'", block).group(1)
        style = re.search(r"font-style: (\w+)", block).group(1)
        weight = [int(w) for w in re.search(r"font-weight: ([\d ]+);", block).group(1).split()]
        url = re.search(r"url\((\S+?)\)", block).group(1)
        if url not in seen:
            name = f"{fam.lower().replace(' ', '-')}-{style}.woff2"
            if name in seen.values():
                name = name.replace(".woff2", f"-{len(seen)}.woff2")
            (out / name).write_bytes(get(url))
            seen[url] = name
        faces.setdefault(url, [fam, style, []])[2].extend(weight)
    for url, (fam, style, weights) in faces.items():
        w = str(min(weights)) if len(set(weights)) == 1 else f"{min(weights)} {max(weights)}"
        print(f"@font-face {{ font-family: '{fam}'; font-style: {style}; font-weight: {w}; font-display: swap; "
              f"src: url(../assets/fonts/{seen[url]}) format('woff2'); }}")
    for name in seen.values():
        print(f"/* {name}: {(out / name).stat().st_size // 1024} KB */", file=sys.stderr)


if __name__ == "__main__":
    main()
