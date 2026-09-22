import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

VERSION = os.environ.get("APP_VERSION", "dev")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(BASE_DIR, "sample.json")
MANIFEST_PATH = os.path.join(BASE_DIR, "manifest.json")


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_sample(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def load_sample(path: str = "") -> dict:
    path = path or SAMPLE_PATH
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def derive_seed(version: str, sample_bytes: bytes) -> str:
    """Seed is pinned to this exact code version plus this exact input.

    Pure function: no clock, no hostname, no file mutation.
    """
    return sha256_hex(b"seedlock|v1|version=" + version.encode("utf-8")
                      + b"|sample=" + sha256_hex(sample_bytes).encode("ascii"))


def compute_output(version: str, data: dict) -> bytes:
    sample_bytes = canonical_sample(data)
    seed = derive_seed(version, sample_bytes)
    return sha256_hex(seed.encode("ascii") + b"|" + sample_bytes).encode("ascii")


def run_once(data: dict) -> bytes:
    """Stateless run: same (version, input) always yields the same bytes."""
    return compute_output(VERSION, data)


def load_manifest(path: str = ""):
    path = path or MANIFEST_PATH
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8")), fh.name


def startup_check(manifest_path: str = "", sample_path: str = ""):
    """Verify the loaded process version against the base-layer manifest.

    Returns (ok, detail). On mismatch the process keeps serving but refuses
    readiness; healthz reports the real failure instead of a port-open check.
    """
    try:
        manifest, _ = load_manifest(manifest_path or MANIFEST_PATH)
    except OSError as exc:
        return False, "manifest missing: %s" % exc
    except ValueError as exc:
        return False, "manifest corrupt: %s" % exc

    pinned_version = manifest.get("version")
    if pinned_version != VERSION:
        return False, "version mismatch: process=%r manifest=%r" % (
            VERSION, pinned_version)

    try:
        with open(sample_path or SAMPLE_PATH, "rb") as fh:
            sample_bytes = fh.read()
    except OSError as exc:
        return False, "sample missing: %s" % exc

    sample_digest = sha256_hex(sample_bytes)
    if sample_digest != manifest.get("sample_sha256"):
        return False, "sample drift: input=%s manifest=%s" % (
            sample_digest, manifest.get("sample_sha256"))

    seed = derive_seed(VERSION, sample_bytes)
    if seed != manifest.get("seed"):
        return False, "seed mismatch: derived=%s manifest=%s" % (
            seed, manifest.get("seed"))

    try:
        data = json.loads(sample_bytes.decode("utf-8"))
    except ValueError as exc:
        return False, "sample invalid: %s" % exc

    expected = manifest.get("run_sha256")
    actual = sha256_hex(compute_output(VERSION, data))
    if actual != expected:
        return False, "run mismatch: actual=%s manifest=%s" % (actual, expected)

    return True, "ok version=%s seed=%s" % (VERSION, seed)


def self_check():
    """In-process reproducibility probe.

    Runs the pinned input twice and requires byte-identical output, and
    requires the result to reproduce the base-layer manifest. Exits non-zero
    on any single-byte difference or binding mismatch.
    """
    ok, detail = startup_check()
    if not ok:
        print("selfcheck FAIL: " + detail, file=sys.stderr)
        return 2

    data = load_sample()
    first = run_once(data)
    second = run_once(data)
    if first != second:
        print("selfcheck FAIL: non-reproducible %r != %r" % (first, second),
              file=sys.stderr)
        return 3

    manifest, _ = load_manifest()
    if sha256_hex(first) != manifest["run_sha256"]:
        print("selfcheck FAIL: does not reproduce pinned version+seed",
              file=sys.stderr)
        return 4

    print("selfcheck OK: %s" % first.decode("ascii"))
    return 0


READY, READY_DETAIL = startup_check()


class H(BaseHTTPRequestHandler):
    def _reply(self, code: int, body: bytes, ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            # Probes the actual loaded process: version+seed must reproduce
            # the manifest, and two runs must be byte-identical.
            if not READY:
                self._reply(503, ("NOT READY: " + READY_DETAIL).encode())
                return
            data = load_sample()
            first = run_once(data)
            second = run_once(data)
            if first != second or sha256_hex(first) != \
                    load_manifest()[0]["run_sha256"]:
                self._reply(503, b"NOT READY: reproducibility check failed")
                return
            self._reply(200, b"ok ")
            self.wfile.write(first)
            return
        if self.path == "/version":
            self._reply(200, VERSION.encode())
            return
        if self.path.startswith("/run"):
            if not READY:
                self._reply(503, ("NOT READY: " + READY_DETAIL).encode())
                return
            data = load_sample()
            out = run_once(data)
            self._reply(200, out)
            return
        self._reply(404, b"not found")

    def log_message(self, *args):
        pass


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "selfcheck":
        sys.exit(self_check())
    print("startup: %s" % READY_DETAIL, file=sys.stderr)
    if not READY:
        print("refusing readiness until version/seed binding is fixed",
              file=sys.stderr)
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()


if __name__ == "__main__":
    main()
