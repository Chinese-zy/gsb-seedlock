"""Build-time generator: pins the seed into the base layer as a manifest.

The seed is a pure function of (version, sample input bytes); nothing is
ever written into sample.json and no seed file is mutated at run time.
"""

import hashlib
import json
import os

import server


def main():
    version = os.environ.get("APP_VERSION", "dev")
    here = os.path.dirname(os.path.abspath(__file__))
    sample_path = os.path.join(here, "sample.json")
    manifest_path = os.path.join(here, "manifest.json")

    with open(sample_path, "rb") as fh:
        sample_bytes = fh.read()
    data = json.loads(sample_bytes.decode("utf-8"))

    seed = server.derive_seed(version, sample_bytes)
    output = server.compute_output(version, data)

    manifest = {
        "schema": "seedlock-manifest/v1",
        "version": version,
        "sample_sha256": hashlib.sha256(sample_bytes).hexdigest(),
        "seed": seed,
        "run_sha256": hashlib.sha256(output).hexdigest(),
    }

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
