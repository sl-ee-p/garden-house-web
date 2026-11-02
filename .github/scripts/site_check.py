#!/usr/bin/env python3
"""Site integrity checks, run against the live site (daily) or a local server (PRs).

usage: site_check.py BASE_URL [--live]
  --live  also checks TLS expiry, deploy drift (live files vs this checkout) and response headers.
Run it from the repository root. Exit code 1 if anything fails.
"""
import hashlib, re, socket, ssl, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag

PROD = "https://www.techs-gardenhouse.com"
base = sys.argv[1].rstrip("/")
live = "--live" in sys.argv
nc = str(int(time.time()))
fails = []

def ok(m): print("ok:   " + m)
def bad(m): print("::error::" + m); fails.append(m)

def get(url, method="GET"):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + (sep + "nc=" + nc if live else ""), method=method,
                                 headers={"User-Agent": "site-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b""
    except Exception as e:
        return 0, {}, str(e).encode()

def local(url):  # map a production URL onto the server under test
    return base + url[len(PROD):] if url.startswith(PROD) else url

# ---- 1. uptime + TLS ---------------------------------------------------------
if live:
    host = urlparse(base).hostname
    try:
        with socket.create_connection((host, 443), timeout=20) as s, \
             ssl.create_default_context().wrap_socket(s, server_hostname=host) as t:
            exp = datetime.strptime(t.getpeercert()["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days = (exp - datetime.now(timezone.utc)).days
        (ok if days >= 14 else bad)(f"TLS certificate valid for {days} more days (min 14)")
    except Exception as e:
        bad(f"TLS/DNS check failed for {host}: {e}")
    code = get(base + "/")[0]
    (ok if code == 200 else bad)(f"home answers {code}")

# ---- 3a. robots.txt ------------------------------------------------------------
_, _, rb = get(base + "/robots.txt")
rb = rb.decode("utf8", "replace")
(ok if "sitemap:" in rb.lower() else bad)("robots.txt references the sitemap")
(bad if re.search(r"(?im)^disallow:\s*/\s*$", rb) else ok)("robots.txt does not block the whole site")

# ---- sitemap -> pages -----------------------------------------------------------
_, _, sm = get(base + "/sitemap.xml")
pages = [local(u) for u in re.findall(r"<loc>([^<]+)</loc>", sm.decode("utf8", "replace"))]
(ok if len(pages) >= 8 else bad)(f"sitemap lists {len(pages)} pages (expect >= 8)")

class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.refs = []; s.alts = {}; s.title = ""; s.robots = ""; s._t = False
    def handle_starttag(s, tag, a):
        a = dict(a)
        if tag == "title": s._t = True
        for k in ("href", "src"):
            if a.get(k) and not a[k].startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
                s.refs.append(a[k])
        for k in ("srcset", "imagesrcset"):
            if a.get(k): s.refs += [x.strip().split()[0] for x in a[k].split(",") if x.strip()]
        if tag == "meta" and a.get("name") == "robots": s.robots += " " + a.get("content", "")
        if tag == "meta" and a.get("property") == "og:image" and a.get("content"): s.refs.append(a["content"])
        if tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"): s.alts[a["hreflang"]] = a["href"]
    def handle_endtag(s, tag):
        if tag == "title": s._t = False
    def handle_data(s, d):
        if s._t: s.title += d

assets, parsed = set(), {}
for url in pages:
    code, hdr, body = get(url)
    if code != 200: bad(f"{url} answers {code}"); continue
    p = P(); p.feed(body.decode("utf8", "replace")); parsed[url] = p
    # ---- 5. content tripwires
    if not p.title.strip(): bad(f"{url} has an empty <title>")
    if "noindex" in p.robots.lower(): bad(f"{url} has meta robots noindex")
    if "noindex" in hdr.get("X-Robots-Tag", "").lower(): bad(f"{url} sends X-Robots-Tag noindex")
    if len(body) < 3000: bad(f"{url} is suspiciously small ({len(body)} bytes)")
    for r in p.refs:
        full = urldefrag(urljoin(url, r))[0]
        full = local(full)
        if full.startswith(base): assets.add(full)
ok(f"fetched {len(parsed)}/{len(pages)} sitemap pages")

home = next((u for u in parsed if u.rstrip("/") == base), None)
if home:
    _, _, hb = get(home)
    (ok if b"vailfabio05@gmail.com" in hb else bad)("home page still shows the contact email")
    (ok if b'rel="canonical"' in hb else bad)("home page has a canonical link")
    (ok if b'"offers"' in hb else bad)("home page has Product offers in JSON-LD")

# ---- 3b. hreflang reciprocity ---------------------------------------------------
for url, p in parsed.items():
    for lang, href in p.alts.items():
        if lang == "x-default": continue
        t = local(href)
        if t not in parsed: bad(f"{url} hreflang {lang} -> {href} is not in the sitemap"); continue
        if not any(local(h) == url for h in parsed[t].alts.values()):
            bad(f"hreflang not reciprocal: {url} -> {t}")
ok("hreflang alternates checked") if not [f for f in fails if "hreflang" in f] else None

# ---- 2. every referenced internal file resolves ---------------------------------
missing = 0
for a in sorted(assets):
    if get(a, "HEAD")[0] != 200 and get(a)[0] != 200:
        bad(f"broken reference: {a}"); missing += 1
if not missing: ok(f"all {len(assets)} internal links/assets referenced by the sitemap pages return 200")

# ---- 4. deploy drift + 6. headers (live only) -------------------------------------
if live:
    files = subprocess.check_output(["git", "ls-files"], text=True).split("\n")
    skip = re.compile(r"^(\.git|\.github/|tools/|docs/|README\.md|\.htaccess)")
    drift = 0; n = 0
    for f in filter(None, files):
        if skip.match(f): continue
        n += 1
        code, _, body = get(f"{base}/{f}")
        local_bytes = open(f, "rb").read()
        if code != 200: bad(f"deployed file missing: {f} ({code})"); drift += 1
        elif hashlib.sha256(body).digest() != hashlib.sha256(local_bytes).digest():
            bad(f"deploy drift: live {f} differs from main"); drift += 1
    if not drift: ok(f"all {n} deployed files match the repo")
    _, h, _ = get(base + "/")
    h = {k.lower(): v for k, v in h.items()}
    csp = h.get("content-security-policy", "")
    for need in ("default-src 'self'", "object-src 'none'", "frame-ancestors"):
        (ok if need in csp else bad)(f"CSP contains {need}")
    for bannedtok in ("'unsafe-eval'", " *", "http:"):
        (bad if bannedtok in csp.replace("script-src", "script-src ") else ok)(f"CSP free of {bannedtok.strip()}")
    sc, _, _ = get(base + "/this-page-does-not-exist-" + nc)
    (ok if sc == 404 else bad)(f"unknown URL returns {sc} (want 404)")

sys.exit(1 if fails else 0)
