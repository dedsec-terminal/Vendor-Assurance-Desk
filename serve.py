"""Loopback-only viewer for generated assessment files; no external dependencies."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ROUTES = {
    "/": ("web/index.html", "text/html; charset=utf-8"),
    "/index.html": ("web/index.html", "text/html; charset=utf-8"),
    "/style.css": ("web/style.css", "text/css; charset=utf-8"),
    "/app.js": ("web/app.js", "application/javascript; charset=utf-8"),
    "/api/assessment": ("output/assessment.json", "application/json; charset=utf-8"),
    "/output/assessment.json": ("output/assessment.json", "application/json; charset=utf-8"),
    "/output/results.json": ("output/results.json", "application/json; charset=utf-8"),
    "/output/risk_register.csv": ("output/risk_register.csv", "text/csv; charset=utf-8"),
    "/output/decision_memo.md": ("output/decision_memo.md", "text/markdown; charset=utf-8"),
    "/output/control_review.json": ("output/control_review.json", "application/json; charset=utf-8"),
    "/output/control_matrix.csv": ("output/control_matrix.csv", "text/csv; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = ROUTES.get(urlsplit(self.path).path)
        if not route:
            self.send_error(404)
            return
        file = ROOT / route[0]
        if not file.is_file():
            self.send_error(503, "Run python assessment.py first, then refresh.")
            return
        body = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", route[1])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"Vendor Assurance Desk: http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
