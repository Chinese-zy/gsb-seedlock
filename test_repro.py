import json
import os
import unittest

import server

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def sample():
    with open(os.path.join(BASE_DIR, "sample.json")) as f:
        return json.load(f)


class Repro(unittest.TestCase):
    def test_same_input_byte_identical(self):
        data = sample()
        self.assertEqual(server.run_once(data), server.run_once(data))

    def test_seed_file_not_mutated_by_run(self):
        path = os.path.join(BASE_DIR, "seed.txt")
        with open(path, "rb") as f:
            before = f.read()
        server.run_once(sample())
        with open(path, "rb") as f:
            self.assertEqual(before, f.read())

    def test_seed_bound_to_version_and_input(self):
        data = sample()
        out = server.run_once(data)
        original = server.LOADED_VERSION
        try:
            server.LOADED_VERSION = "other-version"
            self.assertNotEqual(out, server.run_once(data))
        finally:
            server.LOADED_VERSION = original
        changed = dict(data)
        changed["n"] = changed.get("n", 0) + 1
        self.assertNotEqual(out, server.run_once(changed))

    def test_version_mismatch_not_ready(self):
        original = server.LOADED_VERSION
        try:
            server.LOADED_VERSION = "wrong-version"
            self.assertFalse(server.ready())
        finally:
            server.LOADED_VERSION = original
        self.assertTrue(server.ready())

    def test_ready_requires_byte_identical_reproduction(self):
        self.assertTrue(server.ready())
        self.assertEqual(server.run_once(sample()), server.run_once(sample()))


if __name__ == "__main__":
    # Same input twice must be byte-identical; any diff exits non-zero.
    unittest.main()
