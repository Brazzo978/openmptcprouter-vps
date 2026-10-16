#!/usr/bin/env python3
"""Verified native-MQVPN candidate repack. Does not change the frozen lock."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BASE = "ee78205d3db491ca7727b974bda0c91ae1523236"
FEC_PATCH_SHA = "530d2112b87845f624f9db79d670e84315f7634b6ba81bbbd524d97d547ce268"
FEC_FEATURES = ("XQC_ENABLE_FEC", "XQC_ENABLE_XOR", "XQC_ENABLE_RSC", "XQC_ENABLE_PKM")
PATCH_SHA = "416aa9768b6a774b3edb7ab7e03043fdf0fb79118d3a1bcbe1510ce7a1feae50"
SOURCE_ARCHIVE_SHA = "3864a72f92d0d1c567c2dc21030121e195883a4415aea86a48323b90e8d8d680"
STOCK_SHA = "d7627312d75e47d0930a7a74ace4ab72d10e44d77a50fce725f877761fc1db81"
PATCH = Path(__file__).resolve().parent.parent / "patches/mqvpn/010-omr-native-lan-routes.patch"

FEC_PATCH = PATCH.with_name("020-report-linked-fec-capability.patch")

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def field(deb, name):
    return subprocess.check_output(["dpkg-deb", "-f", str(deb), name], text=True).strip()

def validate(path, expected):
    actual = sha(path)
    if actual != expected:
        raise ValueError(f"{path}: SHA256 {actual} != {expected}")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stock-deb", type=Path, required=True)
    p.add_argument("--built-executable", type=Path, required=True)
    p.add_argument("--built-sha256", required=True)
    p.add_argument("--xquic-config", type=Path, required=True,
                   help="generated xqc_configure.h used for this executable build")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if not re.fullmatch("[0-9a-f]{64}", a.built_sha256):
        p.error("--built-sha256 must be a lowercase SHA256 digest")
    if a.output.name != "mqvpn_0.16.2-3k2_amd64.deb":
        p.error("output filename must be mqvpn_0.16.2-3k2_amd64.deb")
    validate(PATCH, PATCH_SHA)
    validate(FEC_PATCH, FEC_PATCH_SHA)
    xquic_config = a.xquic_config.read_text(encoding="utf-8")
    for feature in FEC_FEATURES:
        if not re.search(r"(?m)^\s*#\s*define\s+" + feature + r"(?:\s+1)?\s*$", xquic_config):
            raise ValueError(f"generated XQUIC header does not enable {feature}")
    validate(a.stock_deb, STOCK_SHA)
    validate(a.built_executable, a.built_sha256)
    with a.built_executable.open("rb") as f:
        if f.read(4) != b"\x7fELF":
            raise ValueError("built executable is not ELF")
    identity = tuple(field(a.stock_deb, k) for k in ("Package", "Version", "Architecture"))
    if identity != ("mqvpn", "0.16.2-1", "amd64"):
        raise ValueError(f"unexpected stock package identity: {identity}")
    provenance_path = a.output.with_suffix(a.output.suffix + ".json")
    if a.output.exists() or provenance_path.exists():
        raise FileExistsError("candidate DEB or provenance already exists")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mqvpn-3k2-") as td:
        root = Path(td) / "pkg"
        subprocess.run(["dpkg-deb", "-R", str(a.stock_deb), str(root)], check=True)
        target = root / "usr/bin/mqvpn"
        if not target.is_file() or target.is_symlink():
            raise ValueError("stock package lacks regular /usr/bin/mqvpn")
        mode = target.stat().st_mode
        shutil.copyfile(a.built_executable, target)
        os.chmod(target, mode)
        md5sums = root / "DEBIAN/md5sums"
        if md5sums.exists():
            lines = md5sums.read_text(encoding="ascii").splitlines()
            changed = 0
            for index, line in enumerate(lines):
                parts = line.split(None, 1)
                if len(parts) == 2 and parts[1].lstrip("./") == "usr/bin/mqvpn":
                    parts[0] = hashlib.md5(target.read_bytes()).hexdigest()
                    lines[index] = f"{parts[0]}  {parts[1]}"
                    changed += 1
            if changed != 1:
                raise ValueError("stock md5sums lacks one usr/bin/mqvpn entry")
            md5sums.write_text("\n".join(lines) + "\n", encoding="ascii")
        control = root / "DEBIAN/control"
        updated, count = re.subn(rb"(?m)^Version: 0\.16\.2-1$", b"Version: 0.16.2-3k2", control.read_bytes())
        if count != 1:
            raise ValueError("unexpected control Version field")
        control.write_bytes(updated)
        candidate = Path(td) / a.output.name
        env = dict(os.environ, SOURCE_DATE_EPOCH="1700000000")
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(root), str(candidate)], check=True, env=env)
        new_identity = tuple(field(candidate, k) for k in ("Package", "Version", "Architecture"))
        if new_identity != ("mqvpn", "0.16.2-3k2", "amd64"):
            raise ValueError(f"unexpected candidate identity: {new_identity}")
        stock_depends = field(a.stock_deb, "Depends")
        if field(candidate, "Depends") != stock_depends:
            raise ValueError("dependency metadata changed")
        provenance = {
            "package": "mqvpn", "version": "0.16.2-3k2", "architecture": "amd64",
            "source_base_commit": BASE, "source_patch_sha256": PATCH_SHA,
            "source_archive_sha256": SOURCE_ARCHIVE_SHA,
            "fec_patch_sha256": FEC_PATCH_SHA,
            "xquic_generated_config_sha256": sha(a.xquic_config),
            "xquic_fec_features": {feature: True for feature in FEC_FEATURES},
            "stock_deb_sha256": STOCK_SHA, "stock_depends": stock_depends,
            "built_executable_sha256": a.built_sha256,
            "candidate_deb_sha256": sha(candidate), "candidate_deb_size": candidate.stat().st_size,
        }
        shutil.copyfile(candidate, a.output)
        provenance_path.write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance, sort_keys=True, indent=2))

if __name__ == "__main__":
    main()
