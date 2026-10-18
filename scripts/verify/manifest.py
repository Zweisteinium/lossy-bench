#!/usr/bin/env python3
"""Manifest of the data files for docs/data.md: path, lines, bytes, sha256 of every file git would track under
corpus/ and results/ (tracked or untracked-but-not-ignored), then the ignored ones. Usage: manifest.py [--ignored]"""

import hashlib
import subprocess
import sys

from common import ROOT


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.splitlines()


paths = sorted(set(git("ls-files", "--cached", "--others", "--exclude-standard", "corpus", "results")))
if "--ignored" in sys.argv:
    paths = sorted(git("ls-files", "--others", "--ignored", "--exclude-standard", "corpus", "results"))
for rel in paths:
    data = (ROOT / rel).read_bytes()
    lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    print(f"{rel}\t{lines}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}")
