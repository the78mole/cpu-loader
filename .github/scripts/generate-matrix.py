#!/usr/bin/env python3
"""
Generate GitHub Actions matrix from distros.yaml
Outputs a single-line JSON for use in workflow matrix
"""

import yaml
import json
import sys


def main():
    with open("distros.yaml", "r") as f:
        config = yaml.safe_load(f)

    matrix = []
    for dist in config["distributions"]:
        for arch in dist["architectures"]:
            matrix.append(
                {
                    "distro": dist["distro"],
                    "version": dist["version"],
                    "codename": dist["codename"],
                    "arch": arch,
                    "display_name": dist.get(
                        "display_name", f"{dist['distro']} {dist['version']}"
                    ),
                }
            )

    # Output as single-line JSON for GitHub Actions
    print(json.dumps({"include": matrix}, separators=(",", ":")))


if __name__ == "__main__":
    main()
