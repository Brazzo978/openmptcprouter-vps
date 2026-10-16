#!/usr/bin/env python3
"""Validate an offline 3K VPS image/headers pair before installer mutations."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

CC_NAMES = (
    "BBR1", "BBR2", "NANQINLANG",
    *(f"NANBBR{family}_{profile}"
      for family in (1, 2, 3)
      for profile in ("LIGHT", "DEF", "AGGR", "VAR")),
)


def control(deb, field):
    return subprocess.check_output(
        ["dpkg-deb", "-f", deb, field], text=True).strip()


def image_contents(deb, release):
    process = subprocess.Popen(
        ["dpkg-deb", "--fsys-tarfile", deb], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    config = None
    modules = set()
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                filename = member.name.lstrip("./")
                if filename == f"boot/config-{release}":
                    fileobj = archive.extractfile(member)
                    if fileobj is not None:
                        config = fileobj.read().decode("ascii")
                if filename.startswith(f"lib/modules/{release}/"):
                    match = re.search(
                        r"/(tcp_[A-Za-z0-9_]+)\.ko(?:\.(?:xz|gz|zst))?$",
                        filename,
                    )
                    if match:
                        modules.add(match.group(1))
        if process.wait() != 0:
            raise ValueError("cannot extract image package contents")
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait()
    if config is None:
        raise ValueError(f"missing boot/config-{release} in image")
    return config, modules


def sha256_file(filename):
    digest = hashlib.sha256()
    with open(filename, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_package_lock(image, headers, lock_path=None):
    lock_path = lock_path or Path(__file__).with_name("package-lock.json")
    if not lock_path.is_file():
        raise ValueError(f"missing reviewed kernel package lock: {lock_path}")
    data = json.loads(lock_path.read_text())
    if data.get("schema") != 1 or data.get("release") != "6.18.41-20261013.x64v3-omr-3k":
        raise ValueError("unexpected kernel package lock schema or release")
    packages = data.get("packages")
    if not isinstance(packages, dict) or set(packages) != {"image", "headers"}:
        raise ValueError("kernel package lock must contain image and headers")
    for kind, filename in (("image", image), ("headers", headers)):
        if not isinstance(packages[kind], dict):
            raise ValueError(f"invalid {kind} entry in kernel package lock")
        expected = packages[kind].get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"invalid {kind} SHA256 in kernel package lock")
        expected_size = packages[kind].get("size")
        if not isinstance(expected_size, int) or Path(filename).stat().st_size != expected_size:
            raise ValueError(f"{kind} package size differs from reviewed lock")
        if packages[kind].get("package") != f"linux-{kind}-{data['release']}":
            raise ValueError(f"{kind} package name differs from reviewed lock")
        if packages[kind].get("version") != control(filename, "Version"):
            raise ValueError(f"{kind} package version differs from reviewed lock")
        digest = sha256_file(filename)
        if digest != expected:
            raise ValueError(f"{kind} package SHA256 differs from reviewed lock")


def verify(image, headers):
    verify_package_lock(image, headers)
    image_pkg = control(image, "Package")
    headers_pkg = control(headers, "Package")
    match = re.fullmatch(
        r"linux-image-(6\.18\.41-20261013\.x64v3-omr-3k)",
        image_pkg)
    if not match:
        raise ValueError(f"unexpected image package: {image_pkg}")
    release = match.group(1)
    if headers_pkg != f"linux-headers-{release}":
        raise ValueError("image and headers releases differ")
    if control(image, "Architecture") != "amd64" or control(headers, "Architecture") != "amd64":
        raise ValueError("3K VPS kernel packages must be amd64")
    if control(image, "Version") != control(headers, "Version"):
        raise ValueError("image and headers versions differ")
    config, modules = image_contents(image, release)
    required = ("CONFIG_MPTCP=y", "CONFIG_TCP_CONG_BBR=y",
                "CONFIG_TCP_CONG_ADVANCED=y", "CONFIG_DEFAULT_BBR=y",
                'CONFIG_DEFAULT_TCP_CONG="bbr"')
    for setting in required:
        if setting not in config.splitlines():
            raise ValueError(f"missing {setting}")
    for name in CC_NAMES:
        flag = re.search(rf"^CONFIG_TCP_CONG_{name}=([ym])$", config, re.MULTILINE)
        if not flag:
            raise ValueError(f"missing custom CC {name}")
        if flag.group(1) == "m" and "tcp_" + name.lower() not in modules:
            raise ValueError(f"missing custom CC module tcp_{name.lower()}")
    return release


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("headers")
    args = parser.parse_args()
    try:
        print(verify(args.image, args.headers))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print(f"Invalid 3K VPS kernel pair: {error}", file=sys.stderr)
        sys.exit(1)
