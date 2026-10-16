#!/usr/bin/env python3
"""Fetch the reviewed VPS kernel pair without accepting floating binaries."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
RELEASE = "6.18.41-20261013.x64v3-omr-3k"
BASE_URL = "https://repoomr.3klab.com/frozen3k/v0.64.2-20261013/vps-kernel/"


def digest_and_size(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def lock_entries():
    lock_file = ROOT / "package-lock.json"
    data = json.loads(lock_file.read_text())
    if data.get("schema") != 1 or data.get("release") != RELEASE:
        raise ValueError("unexpected reviewed kernel lock")
    packages = data.get("packages")
    if not isinstance(packages, dict) or set(packages) != {"image", "headers"}:
        raise ValueError("kernel lock must contain image and headers")
    for kind in ("image", "headers"):
        entry = packages[kind]
        if not isinstance(entry, dict):
            raise ValueError(f"invalid {kind} lock entry")
        if entry.get("url") != BASE_URL + kind + ".deb":
            raise ValueError(f"unexpected {kind} source URL")
        if not isinstance(entry.get("size"), int) or entry["size"] <= 0:
            raise ValueError(f"invalid {kind} package size")
        if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError(f"invalid {kind} SHA256")
    return packages


def fetch_one(kind, entry, destination):
    if destination.exists():
        actual = digest_and_size(destination)
        if actual != (entry["sha256"], entry["size"]):
            raise ValueError(f"existing {kind} package differs from reviewed lock: {destination}")
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{kind}-", suffix=".deb.part",
                                         dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            request = Request(entry["url"], headers={"User-Agent": "OMR-3K-frozen-kernel/1"})
            with urlopen(request, timeout=60) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    stream.write(chunk)
                    if stream.tell() > entry["size"]:
                        raise ValueError(f"{kind} download exceeds reviewed size")
        if digest_and_size(temporary) != (entry["sha256"], entry["size"]):
            raise ValueError(f"{kind} downloaded package differs from reviewed lock")
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    packages = lock_entries()
    output = ROOT / "packages"
    output.mkdir(exist_ok=True)
    for kind in ("image", "headers"):
        fetch_one(kind, packages[kind], output / f"{kind}.deb")
    subprocess.run([sys.executable, str(ROOT / "verify-3k-kernel.py"),
                    str(output / "image.deb"), str(output / "headers.deb")], check=True)
    print("Reviewed VPS kernel image and headers verified")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"VPS kernel fetch rejected: {error}", file=sys.stderr)
        sys.exit(1)
