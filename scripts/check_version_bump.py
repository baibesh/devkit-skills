#!/usr/bin/env python3
"""Fails if a plugin changed since --base without a version bump in its plugin.json."""

import argparse
import json
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    base = parser.parse_args().base

    changed = {
        path.split("/")[1]
        for path in git("diff", "--name-only", f"{base}...HEAD").splitlines()
        if path.startswith("plugins/") and path.count("/") >= 2
    }
    failed = False
    for plugin in sorted(changed):
        manifest = f"plugins/{plugin}/.claude-plugin/plugin.json"
        try:
            old = json.loads(git("show", f"{base}:{manifest}"))["version"]
        except subprocess.CalledProcessError:
            continue  # new plugin
        try:
            with open(manifest, encoding="utf-8") as f:
                new = json.load(f)["version"]
        except FileNotFoundError:
            continue  # plugin removed
        if old == new:
            print(f"error: plugins/{plugin} changed but version is still {old}")
            failed = True
        else:
            print(f"ok: {plugin} {old} -> {new}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
