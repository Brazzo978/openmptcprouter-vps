#!/usr/bin/env python3
"""Validate an offline 3K VPS image/headers pair before installer mutations."""
import argparse
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

def verify(image, headers):
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
                "CONFIG_TCP_CONG_ADVANCED=y")
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
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print(f"Invalid 3K VPS kernel pair: {error}", file=sys.stderr)
        sys.exit(1)
