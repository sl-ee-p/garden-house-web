"""Tiny helper: serve the repo root on a free localhost port in a thread."""
import functools
import http.server
import pathlib
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ["index.html", "galleria.html", "configura.html", "contatti.html"]


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    handler = functools.partial(_Quiet, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/"
