# OpenMPTCProuter VPS 0.1163-3K

This `omr-vps-0.1163-3K-next` branch also retains the candidate
`patches/mqvpn/030-3k-smooth-failover.patch` for future source builds. It changes
MQVPN client/path/socket behavior and preserves the wire protocol; paired lab
tests used a rebuilt baseline server. The frozen lock, installer and DEB payload
below remain the published 0.1163-3K/0.16.2-3k2 versions. No new VPS package or
release is delivered by adding the source patch. The existing repack tool checks
patches 010/020 only; a future candidate repack must explicitly include patch 030
and record its binary/source provenance before changing any frozen package lock.

Stable release paired with [client v0.64.2-3K](https://github.com/Brazzo978/openmptcprouter/releases/tag/v0.64.2-3K). Run as root on **Debian 13 amd64 with an x86-64-v3 CPU**. The command downloads the complete bundle and verifies its SHA-256 checksum before running the installer:

```sh
workdir=$(mktemp -d) && wget -O "$workdir/vps.tar.gz" https://github.com/Brazzo978/openmptcprouter-vps/releases/download/v0.1163-3K/openmptcprouter-vps-0.1163-3K.tar.gz && echo "5cfffea16a826a678b5fead2da7e8647aa062de7da0f1f49a6723e8546a893a7  $workdir/vps.tar.gz" | sha256sum -c - && tar -xzf "$workdir/vps.tar.gz" -C "$workdir" && cd "$workdir/openmptcprouter-vps-0.1163-3K" && ./run-vps-3k.sh install
```

Installation changes networking, services and the kernel. Debian dependencies require APT access. Once installation completes, **reboot the VPS** to use the included kernel; SSH uses port **65222**. The generated router connection settings are in `/root/openmptcprouter_config.txt`; the PC/phone WireGuard profile is in `/root/wireguard-client.conf`.

## Features

- Kernel and headers **6.18.41-20261013.x64v3-omr-3k**, pinned to this release; **BBRv3 (`bbr`) by default**, 18 congestion control algorithms and NanBBR variants.
- **21 frozen OMR packages**, verified with SHA-256 checksums. The bundle includes the kernel, packages and API; the verified installation required no OMR downloads from Ysurac's repositories. Operating system dependencies come from Debian.
- Native MQVPN **0.16.2-3k2**, with FEC/XOR/RSC/PKM support compiled in and LAN-prefix routing. Runtime FEC remains configurable.
- Primary router IP **10.255.220.2** by default when available; explicit addresses and any other users are preserved.
- API **0.18+20261016-3k4**, authenticated diagnostic logs with sensitive values redacted, and TCP reverse forwarding through the separate XRay backend and MQVPN tunnel.
- Remote WireGuard access to the OMR GUI. LAN access is denied by default and can be enabled using the client checkbox or the VPS helper/API. An IPv4 full tunnel with `AllowedIPs = 0.0.0.0/0` can use the VPS public IP without enabling LAN access.
- Router backups to the VPS and their API endpoints have been removed; automatic OMR updates are blocked to preserve the frozen build.

## Validation

Installation from a clean Debian 13 snapshot completed with exit code 0, followed by a reboot into the frozen kernel and verification of all 21 packages. **67 live checks passed**: 31 installation/API/service checks, 8 checks using the actual MQVPN engine with a handshake and traffic to a test LAN, and 28 WireGuard checks covering external HTTPS/DNS, GUI access, LAN blocking, explicit access and revocation of established connections. The report adds archive identity verification, for **68 checks in total**. API suite: **1042 tests passed, 9 skipped**.

SHA-256 of the exact bundle installed and published: `5cfffea16a826a678b5fead2da7e8647aa062de7da0f1f49a6723e8546a893a7`.

The WireGuard checks use simulated OMR GUI/LAN endpoints; native MQVPN routing was tested separately with actual packets. The previous physical fiber + 5G test client was deleted by the user and was not paired again after the clean installation. Earlier physical-client and TCP forwarding checks are documented in the client release. No controlled aggregated-throughput benchmark or long-term XRay stability proof is claimed.

## Source and installation

Default branch: [`omr-vps-0.1163-3K`](https://github.com/Brazzo978/openmptcprouter-vps/tree/omr-vps-0.1163-3K). The `v0.1163-3K` tag identifies the source code in the verified bundle; the branch also contains these installation instructions. A plain clone does not include all frozen binaries: use the command above or the complete release bundle.

See [README-3K.md](https://github.com/Brazzo978/openmptcprouter-vps/blob/omr-vps-0.1163-3K/README-3K.md) for manual installation and WireGuard details. Verify the other assets with `SHA256SUMS-vps-0.1163-3K`.
