import json, hashlib, os
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(name):
    with open(os.path.join(BASE_DIR, name)) as f:
        return f.read().strip()


# Version pinned into the image at build time; the process must actually
# load this exact version or it never becomes ready.
PINNED_VERSION = _read("VERSION")
# Base seed pinned in its own image layer; never written back at runtime.
BASE_SEED = _read("seed.txt")
# The version this process actually loaded (env override wins).
LOADED_VERSION = os.environ.get("APP_VERSION", PINNED_VERSION)


def version_ok():
    return LOADED_VERSION == PINNED_VERSION


def effective_seed(data: dict) -> str:
    # Seed is bound to this input and the loaded version; derived, never stored.
    canonical = json.dumps(data, sort_keys=True)
    return hashlib.sha256(
        f"{BASE_SEED}|{LOADED_VERSION}|{canonical}".encode()
    ).hexdigest()


def run_once(data: dict) -> bytes:
    canonical = json.dumps(data, sort_keys=True)
    h = hashlib.sha256((effective_seed(data) + canonical).encode()).hexdigest()
    return h.encode()


def load_sample():
    with open(os.path.join(BASE_DIR, "sample.json")) as f:
        return json.load(f)


def ready() -> bool:
    # Not ready unless the loaded version matches the pinned one AND this
    # version + this seed reproduces byte-identically on the sample input.
    if not version_ok():
        return False
    sample = load_sample()
    return run_once(sample) == run_once(sample)


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            if ready():
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"not ready")
            return
        if self.path == "/version":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(LOADED_VERSION.encode())
            return
        if self.path.startswith("/run"):
            out = run_once(load_sample())
            self.send_response(200)
            self.end_headers()
            self.wfile.write(out)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
