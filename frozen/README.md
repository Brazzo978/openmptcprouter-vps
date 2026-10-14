# OMR 3K frozen VPS packages

`omr-amd64.lock.json` fixes the exact version, URL, size and SHA-256 of the 21 selected amd64 OMR packages. Three scheduler/ACME helper scripts are checked in with their hashes. The BPF weight package is intentionally **1.1-1**: the official file named `weight_1.0-1` contains internal Debian Version `1.1-1`.

Before running the VPS installer from this server directory, run:

```sh
python3 frozen/freeze.py fetch
python3 frozen/freeze.py verify
```

`fetch` downloads only URLs already in the committed lock and fails if any byte changes. It produces `assets/Packages.gz` for the local APT repository. For an offline release, ship the verified `assets/` directory alongside the source. The installer checks all hashes again, copies the bundle to `/usr/share/omr-server-3k/frozen`, and uses only that local repository for OMR packages. Debian OS and security dependencies remain under Debian APT. The legacy installer currently adds a Debian Bullseye source for old runtime dependencies such as libmbedcrypto3 and libpcre3; this is not an OMR binary input frozen by this lock, and must be reviewed separately before claiming a Debian-13-only dependency graph. The kernel and locally built API debs have separate release locks.

`refresh-lock` is an explicit maintainer action that reads the current upstream Packages index and rewrites the lock; never use it during installation. Binary debs are omitted from Git and must be present in the release artifact or fetched before install.


The canonical lock now resolves its 21 deb URLs from the versioned 3K HTTPS mirror.
Each entry retains `origin_url` for upstream provenance. Before switching, every
mirror response was checked from the build host against the original size and
SHA-256. The mirrored binaries are byte-identical to the archived source
payloads; the checked-in helper scripts remain local. Never retarget the
mirror without rechecking all payload hashes and issuing a new versioned path.


The installer preflight restricts frozen 3K to Debian 13 amd64, kernel 6.18,
`SOURCES=no`, `LOCALFILES=yes`, and `CHINA=no`. Consequently, the legacy
floating `pip -U` branches (Debian 12/Ubuntu/older Debian) are unreachable.
On the supported path, FastAPI, Starlette, jsonschema, python-multipart,
uvicorn, passlib, netaddr, uvloop and the other Python runtime dependencies
come from Debian APT. EasyRSA, iperf3 and mptcpize also come from Debian APT;
their GitHub/source-download branches are unreachable. These distribution
packages receive normal Debian updates and are not byte-frozen by this OMR
asset lock. The isolated API unit-test venv is not evidence of exact package
versions on a fresh Debian 13 VPS.


The server retains MLVPN for older clients even though the new router image
does not offer MLVPN or OpenVPN bonding. Therefore `omr-mlvpn` is included as
the 21st locked OMR deb, and its failed APT install cannot fall back to an
unverified download. Its official archived bytes were checked against the
upstream index and the published 3K mirror was independently verified by
HTTPS status, size and SHA-256 before switching its canonical `url`.
