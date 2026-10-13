#!/usr/bin/env python3
"""Package the local reviewed 3K API without installing it on the build host."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

VERSION = "0.18+20261013-3k1"
SOURCE_DATE_EPOCH = int(datetime(2026, 10, 13, tzinfo=timezone.utc).timestamp())
ROOT = Path(__file__).resolve().parent
SERVER = ROOT.parent if (ROOT.parent / "debian9-x86_64.sh").is_file() else ROOT.parent / "server"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=SERVER / "debian")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    review = SERVER / ".review"
    review.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="admin-deb-", dir=review) as work:
        stage = Path(work) / "root"
        files = {
            "omradmin.py": "usr/bin/omradmin.py",
            "omr-admin-config.json": "usr/share/omr-admin/omr-admin-config.json",
            "debian/omr-admin.service": "lib/systemd/system/omr-admin.service",
            "debian/omr-admin-resync.conf": "lib/systemd/system/nftables.service.d/omr-admin-resync.conf",
        }
        for source, dest in files.items():
            target = stage / dest
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, target)
            target.chmod(0o755 if source == "omradmin.py" else 0o644)
        config = stage / "etc/openmptcprouter-vps-admin/omr-admin-config.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "omr-admin-config.json", config)
        config.chmod(0o600)
        debian = stage / "DEBIAN"
        debian.mkdir()
        control = """Package: omr-vps-admin
Version: {version}
Section: net
Priority: optional
Architecture: all
Maintainer: OpenMPTCProuter 3K
Depends: python3, python3-uvicorn, python3-netaddr, python3-pip, python3-netifaces, python3-aiofiles, python3-psutil, jq, ipcalc, nftables
Description: OpenMPTCProuter VPS API with 3K TCP XRay reverse forwarding
 Local source package based on official VPS API 0.18.
""".format(version=VERSION)
        (debian / "control").write_text(control)
        shutil.copyfile(ROOT / "debian/postinst", debian / "postinst")
        (debian / "postinst").chmod(0o755)
        (debian / "conffiles").write_text("/etc/openmptcprouter-vps-admin/omr-admin-config.json\n")
        for staged in sorted(stage.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            os.utime(staged, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))
        os.utime(stage, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))
        artifact = output / ("omr-vps-admin_" + VERSION + "_all.deb")
        build_env = dict(os.environ, SOURCE_DATE_EPOCH=str(SOURCE_DATE_EPOCH), TZ="UTC")
        subprocess.run(
            ["dpkg-deb", "--root-owner-group", "--build", str(stage), str(artifact)],
            check=True, env=build_env,
        )
        metadata = {"version": VERSION, "path": str(artifact), "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    "source_sha256": hashlib.sha256((ROOT / "omradmin.py").read_bytes()).hexdigest(), "installed": False}
        (output / "omr-vps-admin-3k.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps(metadata))
if __name__ == "__main__":
    main()
