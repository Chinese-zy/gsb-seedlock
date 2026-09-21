import json, hashlib, os
from http.server import BaseHTTPRequestHandler, HTTPServer

VERSION = os.environ.get("APP_VERSION", "dev")

def run_once(data: dict) -> bytes:
    # BUG: mutates seed.txt every run; not pinned to input+version
    seed = open("seed.txt").read().strip()
    open("seed.txt", "w").write(seed + "+")
    h = hashlib.sha256((seed + json.dumps(data, sort_keys=True)).encode()).hexdigest()
    return h.encode()

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            # BUG: only checks process up
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok"); return
        if self.path == "/version":
            self.send_response(200); self.end_headers(); self.wfile.write(VERSION.encode()); return
        if self.path.startswith("/run"):
            data = json.load(open("sample.json"))
            out = run_once(data)
            self.send_response(200); self.end_headers(); self.wfile.write(out); return
        self.send_response(404); self.end_headers()
    def log_message(self, *args):
        pass

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
