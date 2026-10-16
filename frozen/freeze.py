#!/usr/bin/env python3
"""Prepare and verify the immutable OMR 3K amd64 package bundle.

The checked-in lock is the authority.  Only the explicit refresh-lock command
consults upstream package indexes; prepare never silently updates a version.
Debian 13 distribution/security dependencies remain managed by Debian APT.
"""
import argparse
import gzip
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
LOCK = HERE / "omr-amd64.lock.json"
ASSETS = HERE / "assets"
ORIGIN = "https://repo.openmptcprouter.com"
INDEX = ORIGIN + "/dists/buster/main/binary-amd64/Packages.gz"
WEB_DEBS = "https://www.openmptcprouter.com/debian/"
ACME_URL = "https://raw.githubusercontent.com/acmesh-official/acme.sh/807da6498377ee5e0cf43a78091f46f12dc59a89/acme.sh"
ACME_SHA256 = "c7d68b021cfd6380ea83a82962abde5b484779fee0b97d38681dfa1396bbc8d7"
SELECTED = {
    "mptcp-bpf-bkup": "1.0-1", "mptcp-bpf-burst": "1.0-1",
    "mptcp-bpf-first": "1.0-1", "mptcp-bpf-red": "1.0-1",
    "mptcp-bpf-rr": "1.0-1", "mptcp-bpf-dscp": "1.0-1",
    "mptcp-bpf-weight": "1.1-1", "mptcp-bpf-weight-rr": "1.0-1",
    "mqvpn": "0.16.2-1", "libmqvpn0": "0.16.2-1",
    "libjson-c3": "0.12.1+ds-2",
    "omr-glorytun": "0.3.4-5", "omr-glorytun-tcp": "0.0.35-6",
    "omr-dsvpn": "0.1.4-2", "omr-mlvpn": "3.0.0+20211028.git.ddafba3",
    "omr-shadowsocks-libev": "3.3.5-3",
    "omr-simple-obfs": "0.0.5-1", "shadowsocks-go": "1.14.0",
    "v2ray": "5.32.0", "xray": "26.7.11", "tracebox": "0.4.4",
}
WEB_ONLY = {"mptcp-bpf-dscp", "mptcp-bpf-weight", "mptcp-bpf-weight-rr"}
HELPERS = {
    "mptcp-scheduler-dscp.sh": HERE.parent.parent.parent / "feeds/openmptcprouter/mptcp-dscp-manager/files/usr/sbin/mptcp-scheduler-dscp.sh",
    "mptcp-scheduler-weight.sh": HERE.parent.parent.parent / "feeds/openmptcprouter/mptcp-weight-manager/files/usr/sbin/mptcp-scheduler-weight.sh",
}

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def get(url, target):
    req = urllib.request.Request(url, headers={"User-Agent": "omr-3k-freeze/1"})
    with urllib.request.urlopen(req, timeout=90) as response, open(target, "wb") as out:
        shutil.copyfileobj(response, out)

def paragraphs(raw):
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        fields = {}
        for line in block.splitlines():
            if re.match(r"^[A-Za-z][A-Za-z0-9-]*: ", line):
                k, v = line.split(": ", 1)
                fields[k] = v
        if fields.get("Package"):
            yield fields

def refresh_lock():
    with urllib.request.urlopen(INDEX, timeout=60) as r:
        raw = gzip.decompress(r.read()).decode()
    repo = {(x["Package"], x["Version"]): x for x in paragraphs(raw)}
    entries = []
    ASSETS.mkdir(exist_ok=True)
    for name, version in sorted(SELECTED.items()):
        filename = f"{name}_{version}_amd64.deb"
        if name in WEB_ONLY:
            url = WEB_DEBS + filename
            upstream_sha = None
        else:
            x = repo.get((name, version))
            if not x:
                raise RuntimeError(f"missing exact package in official index: {name}={version}")
            url = ORIGIN + "/" + x["Filename"]
            upstream_sha = x.get("SHA256")
            if not upstream_sha:
                raise RuntimeError(f"no official SHA256: {name}={version}")
        target = ASSETS / filename
        if not target.exists() or (upstream_sha and digest(target) != upstream_sha):
            with tempfile.NamedTemporaryFile(dir=ASSETS, delete=False) as f:
                tmp = pathlib.Path(f.name)
            try:
                get(url, tmp)
                if upstream_sha and digest(tmp) != upstream_sha:
                    raise RuntimeError(f"upstream SHA256 mismatch: {name}")
                tmp.replace(target)
            finally:
                tmp.unlink(missing_ok=True)
        fields = [subprocess.check_output(["dpkg-deb", "-f", str(target), key], text=True).strip() for key in ("Package", "Version", "Architecture")]
        if fields != [name, version, "amd64"]:
            raise RuntimeError(f"deb metadata mismatch: {target}: {fields}")
        entries.append({"package": name, "version": version, "architecture": "amd64",
                        "file": filename, "sha256": digest(target),
                        "size": target.stat().st_size, "url": url})
    helper_entries = []
    helper_dir = HERE / "helpers"
    helper_dir.mkdir(exist_ok=True)
    for name, source in sorted(HELPERS.items()):
        if not source.exists():
            raise RuntimeError(f"missing pinned feed helper: {source}")
        dest = helper_dir / name
        shutil.copyfile(source, dest)
        helper_entries.append({"file": "helpers/" + name, "sha256": digest(dest),
                               "size": dest.stat().st_size})
    acme = helper_dir / "acme.sh"
    if not acme.is_file() or digest(acme) != ACME_SHA256:
        with tempfile.NamedTemporaryFile(dir=helper_dir, delete=False) as f:
            tmp = pathlib.Path(f.name)
        try:
            get(ACME_URL, tmp)
            if digest(tmp) != ACME_SHA256:
                raise RuntimeError("pinned acme.sh hash mismatch")
            tmp.replace(acme)
        finally:
            tmp.unlink(missing_ok=True)
    helper_entries.append({"file": "helpers/acme.sh", "sha256": ACME_SHA256,
                           "size": acme.stat().st_size, "url": ACME_URL})
    data = {"schema": 1, "architecture": "amd64",
            "source_index": INDEX, "source_feed_commit": "818fa5116eefc99325e0f231e819dc51b062ef85",
            "packages": entries, "helpers": helper_entries,
            "scope": "OMR packages only; Debian 13 OS/security dependencies intentionally remain distribution-managed"}
    LOCK.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"locked {len(entries)} OMR debs and {len(helper_entries)} vendored helpers")

def verify(root=HERE):
    data = json.loads((root / LOCK.name).read_text())
    if data.get("schema") != 1 or data.get("architecture") != "amd64":
        raise RuntimeError("unsupported freeze lock")
    allowed = {entry["file"] for entry in data["packages"]}
    actual = {path.name for path in (root / "assets").glob("*.deb")}
    if actual != allowed:
        raise RuntimeError(f"frozen assets have missing/extra debs: {sorted(actual ^ allowed)}")
    for entry in data["packages"]:
        path = root / "assets" / entry["file"]
        if not path.is_file() or path.stat().st_size != entry["size"] or digest(path) != entry["sha256"]:
            raise RuntimeError(f"missing/mismatched frozen deb: {path}")
        fields = [subprocess.check_output(["dpkg-deb", "-f", str(path), key], text=True).strip() for key in ("Package", "Version", "Architecture")]
        if fields != [entry["package"], entry["version"], "amd64"]:
            raise RuntimeError(f"mismatched deb metadata: {path}")
    # Every runtime dependency owned by the OMR repository must be present
    # in this same local repository; base Debian dependencies are external.
    selected = {entry["package"] for entry in data["packages"]}
    for entry in data["packages"]:
        path = root / "assets" / entry["file"]
        depends = subprocess.check_output(["dpkg-deb", "-f", str(path), "Depends"], text=True).strip()
        for atom in re.split(r"[,|]", depends):
            name = re.match(r"\s*([a-z0-9][a-z0-9+.-]*)", atom)
            if not name:
                continue
            dependency = name.group(1)
            if dependency.startswith(("omr-", "mptcp-bpf-")) or dependency in {"mqvpn", "libmqvpn0", "libjson-c3"}:
                if dependency not in selected:
                    raise RuntimeError(f"unlocked OMR dependency: {entry['package']} -> {dependency}")
    for entry in data["helpers"]:
        path = root / entry["file"]
        if not path.is_file() or path.stat().st_size != entry["size"] or digest(path) != entry["sha256"]:
            raise RuntimeError(f"missing/mismatched helper: {path}")
    return data

def fetch():
    """Materialize the checked-in lock; refuse any upstream payload drift."""
    data = json.loads(LOCK.read_text())
    ASSETS.mkdir(exist_ok=True)
    for entry in data["packages"]:
        target = ASSETS / entry["file"]
        if target.is_file() and target.stat().st_size == entry["size"] and digest(target) == entry["sha256"]:
            continue
        with tempfile.NamedTemporaryFile(dir=ASSETS, delete=False) as f:
            tmp = pathlib.Path(f.name)
        try:
            get(entry["url"], tmp)
            if tmp.stat().st_size != entry["size"] or digest(tmp) != entry["sha256"]:
                raise RuntimeError(f"upstream payload drift: {entry['package']}={entry['version']}")
            tmp.replace(target)
        finally:
            tmp.unlink(missing_ok=True)
    prepare()

def prepare():
    data = verify()
    ASSETS.mkdir(exist_ok=True)
    stanzas = []
    for entry in data["packages"]:
        control = subprocess.check_output(["dpkg-deb", "-f", str(ASSETS / entry["file"])], text=True).rstrip()
        stanzas.append(control + "\nFilename: ./" + entry["file"] +
                       "\nSize: " + str(entry["size"]) +
                       "\nSHA256: " + entry["sha256"] + "\n")
    output = ("\n".join(stanzas) + "\n").encode()
    indexed = re.findall(rb"^Package: (.+)$", output, re.M)
    wanted = {x["package"].encode() for x in data["packages"]}
    if len(indexed) != len(wanted) or set(indexed) != wanted:
        raise RuntimeError("local APT index package set differs from lock")
    (ASSETS / "Packages").write_bytes(output)
    with gzip.GzipFile(filename=str(ASSETS / "Packages.gz"), mode="wb", mtime=0) as f:
        f.write(output)
    print(f"verified {len(data['packages'])} frozen debs; generated local APT index")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["refresh-lock", "fetch", "verify", "prepare"])
    args = parser.parse_args()
    if args.action == "refresh-lock":
        refresh_lock()
    elif args.action == "fetch":
        fetch()
    elif args.action == "verify":
        data = verify()
        print(f"verified {len(data['packages'])} frozen debs and {len(data['helpers'])} helpers")
    else:
        prepare()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"OMR 3K freeze error: {exc}", file=sys.stderr)
        sys.exit(1)
