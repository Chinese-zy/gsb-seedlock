import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import server


class Repro(unittest.TestCase):
    def test_same_input_stable(self):
        data = {"n": 3}
        outputs = {server.compute_output("1.0.0", data) for _ in range(100)}
        self.assertEqual(len(outputs), 1)

    def test_seed_is_pure_derivation(self):
        sample = json.dumps({"n": 3}, sort_keys=True).encode()
        first = server.derive_seed("1.0.0", sample)
        second = server.derive_seed("1.0.0", sample)
        self.assertEqual(first, second)
        self.assertNotEqual(
            server.derive_seed("1.0.1", sample), first)
        self.assertNotEqual(
            server.derive_seed("1.0.0", sample + b" "), first)

    def test_seed_does_not_use_clock_or_host(self):
        sample = b'{"n":3}'
        os.environ["TZ"] = "UTC"
        a = server.derive_seed("v", sample)
        os.environ["TZ"] = "America/Los_Angeles"
        b = server.derive_seed("v", sample)
        self.assertEqual(a, b)

    def test_run_does_not_mutate_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample_path = os.path.join(tmp, "sample.json")
            manifest_path = os.path.join(tmp, "manifest.json")
            with open(sample_path, "wb") as fh:
                fh.write(b'{"n": 3}')
            data = server.load_sample(sample_path)
            with open(sample_path, "rb") as fh:
                before = fh.read()
            for _ in range(10):
                server.compute_output("1.0.0", data)
            with open(sample_path, "rb") as fh:
                after = fh.read()
            self.assertEqual(before, after)
            self.assertFalse(os.path.exists(os.path.join(tmp, "seed.txt")))
            self.assertFalse(os.path.exists(manifest_path))

    def test_startup_check_rejects_version_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "sample.json"), "rb") as fh:
                sample = fh.read()
            with open(os.path.join(tmp, "sample.json"), "wb") as fh:
                fh.write(sample)
            data = json.loads(sample.decode())
            manifest = {
                "version": "9.9.9",
                "sample_sha256": hashlib.sha256(sample).hexdigest(),
                "seed": server.derive_seed("9.9.9", sample),
                "run_sha256": hashlib.sha256(
                    server.compute_output("9.9.9", data)).hexdigest(),
            }
            with open(os.path.join(tmp, "manifest.json"), "w") as fh:
                json.dump(manifest, fh)

            old_version = server.VERSION
            server.VERSION = "1.0.0"
            try:
                ok, detail = server.startup_check(
                    os.path.join(tmp, "manifest.json"),
                    os.path.join(tmp, "sample.json"))
                self.assertFalse(ok)
                self.assertIn("version mismatch", detail)
            finally:
                server.VERSION = old_version

    def test_selfcheck_exits_nonzero_on_mismatch(self):
        env = dict(os.environ)
        env["APP_VERSION"] = "9.9.9"
        proc = subprocess.run(
            [sys.executable, "server.py", "selfcheck"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=env, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
