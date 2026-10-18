"""Automated QA: overflow at 6 widths, console errors, failed requests,
dead links/anchors, axe-core WCAG A/AA scan and a few interaction checks.

usage: python tools/audit.py [path/to/axe.min.js]
Exit code 1 if any problem is found.
"""
import pathlib
import re
import sys
import urllib.parse

from playwright.sync_api import sync_playwright

from _server import PAGES, ROOT, serve

WIDTHS = [320, 375, 768, 1024, 1440, 1920]
problems = []


def report(msg):
    problems.append(msg)
    print("  ✗", msg)


def check_links(page, pg):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
    for href in set(hrefs):
        if href.startswith(("mailto:", "tel:", "http://", "https://")):
            continue
        parsed = urllib.parse.urlparse(href)
        target = parsed.path or pg
        if not (ROOT / target).exists():
            report(f"{pg}: dead link {href}")
            continue
        if parsed.fragment and target.endswith(".html"):
            html = (ROOT / target).read_text(encoding="utf-8")
            if not re.search(rf'id="{re.escape(parsed.fragment)}"', html):
                report(f"{pg}: missing anchor {href}")


def overflow(page):
    return page.evaluate("""() => {
      const vw = document.documentElement.clientWidth;
      if (document.documentElement.scrollWidth <= vw) return null;
      const bad = [...document.querySelectorAll('body *')].filter(el => {
        const r = el.getBoundingClientRect();
        return r.width && r.right > vw + 1 && getComputedStyle(el).position !== 'fixed';
      }).slice(0, 3).map(el => el.tagName.toLowerCase() + '.' + [...el.classList].join('.'));
      return document.documentElement.scrollWidth + 'px > ' + vw + 'px: ' + bad.join(', ');
    }""")


def interactions(browser, base):
    ctx = browser.new_context(viewport={"width": 375, "height": 800})
    page = ctx.new_page()
    page.goto(base + "index.html")
    toggle = page.locator("[data-nav-toggle]")
    toggle.click()
    if not page.locator("#site-nav").is_visible():
        report("nav: menu not visible after toggle")
    page.keyboard.press("Escape")
    if toggle.get_attribute("aria-expanded") != "false":
        report("nav: Escape did not close menu")

    page.goto(base + "galleria.html")
    page.locator("[data-lightbox]").first.click()
    dialog = page.locator("[data-lightbox-dialog]")
    if not dialog.evaluate("d => d.open"):
        report("lightbox: did not open")
    page.keyboard.press("ArrowRight")
    if "2 /" not in page.locator("[data-lightbox-count]").inner_text():
        report("lightbox: ArrowRight did not advance")
    page.keyboard.press("Escape")
    if dialog.evaluate("d => d.open"):
        report("lightbox: Escape did not close")
    if not page.evaluate("document.activeElement.matches('[data-lightbox]')"):
        report("lightbox: focus not returned to trigger")

    page.goto(base + "configura.html")
    page.locator('input[name="struttura"][value="verde"]').check()
    if "#178048" not in (page.locator("[data-house]").get_attribute("style") or ""):
        report("configurator: structure colour not applied")
    if "verde" not in page.url:
        report("configurator: hash not updated")
    page.goto(base + "configura.html#struttura=rosso&pannelli=ocra")
    if "Rosso" not in page.locator("[data-summary]").inner_text():
        report("configurator: hash not restored")
    ctx.close()

    # Reduced motion: nothing may stay hidden.
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    for pg in PAGES:
        page.goto(base + pg, wait_until="networkidle")
        hidden = page.evaluate("[...document.querySelectorAll('[data-reveal]')].filter(e => getComputedStyle(e).opacity < 0.5).length")
        if hidden:
            report(f"{pg}: {hidden} [data-reveal] element(s) hidden with reduced motion")
    ctx.close()


def main():
    axe_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    httpd, base = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w in WIDTHS:
            print(f"width {w}px")
            ctx = browser.new_context(viewport={"width": w, "height": 900})
            page = ctx.new_page()
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("response", lambda r: errors.append(f"HTTP {r.status} {r.url}") if r.status >= 400 else None)
            for pg in PAGES:
                errors.clear()
                page.goto(base + pg, wait_until="networkidle")
                page.wait_for_timeout(300)
                if (o := overflow(page)):
                    report(f"{pg} @{w}: horizontal overflow {o}")
                for e in errors:
                    report(f"{pg} @{w}: {e}")
                if w == 1440:
                    check_links(page, pg)
                if axe_path and w in (375, 1440):
                    page.add_script_tag(path=str(axe_path))
                    res = page.evaluate("axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']})")
                    for v in res["violations"]:
                        targets = "; ".join(",".join(n["target"]) for n in v["nodes"][:3])
                        report(f"{pg} @{w}: axe {v['impact']} {v['id']}: {targets}")
            ctx.close()
        print("interactions")
        interactions(browser, base)
        browser.close()
    httpd.shutdown()
    print(f"\n{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
