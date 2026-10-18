"""Full-page screenshots of every page at desktop and mobile size.

usage: python tools/shoot.py docs/screenshots/<branch>
Requires: pip install playwright && python -m playwright install chromium
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

from _server import PAGES, ROOT, serve

VIEWPORTS = {"desktop": (1440, 900, 1), "mobile": (390, 844, 2)}


def settle(page):
    # Scroll through the page so lazy images load and reveal animations run.
    height = page.evaluate("document.documentElement.scrollHeight")
    for y in range(0, height, 400):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(60)
    page.wait_for_timeout(900)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(700)


def main():
    out = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots/current")
    out.mkdir(parents=True, exist_ok=True)
    httpd, base = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, (w, h, dpr) in VIEWPORTS.items():
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr)
            page = ctx.new_page()
            for pg in PAGES:
                page.goto(base + pg, wait_until="networkidle")
                settle(page)
                target = out / f"{name}-{pg.replace('.html', '')}.jpg"
                page.screenshot(path=str(target), full_page=True, type="jpeg", quality=78)
                print("saved", target.relative_to(ROOT))
            ctx.close()
        browser.close()
    httpd.shutdown()


if __name__ == "__main__":
    main()
