"""Run Lighthouse (mobile + desktop) on every page and print the scores.

usage: LIGHTHOUSE=/path/to/lighthouse CHROME_PATH=/path/to/chrome python tools/lighthouse.py
"""
import json
import os
import subprocess
import tempfile

from _server import PAGES, serve

CATS = ["performance", "accessibility", "best-practices", "seo"]


def main():
    lh = os.environ.get("LIGHTHOUSE", "lighthouse")
    httpd, base = serve()
    rows = []
    for preset in ("mobile", "desktop"):
        for pg in PAGES:
            with tempfile.NamedTemporaryFile(suffix=".json") as f:
                cmd = [lh, base + pg, "--quiet", "--output=json", f"--output-path={f.name}",
                       "--chrome-flags=--headless=new --no-sandbox", f"--only-categories={','.join(CATS)}"]
                if preset == "desktop":
                    cmd.append("--preset=desktop")
                subprocess.run(cmd, check=True)
                data = json.load(open(f.name))
            scores = [round((data["categories"][c]["score"] or 0) * 100) for c in CATS]
            audits = data["audits"]
            cls = audits["cumulative-layout-shift"]["displayValue"]
            lcp = audits["largest-contentful-paint"]["displayValue"]
            rows.append((preset, pg, *scores, lcp, cls))
            print(f"{preset:7} {pg:15} perf {scores[0]:3}  a11y {scores[1]:3}  bp {scores[2]:3}  seo {scores[3]:3}  LCP {lcp}  CLS {cls}", flush=True)
    httpd.shutdown()


if __name__ == "__main__":
    main()
