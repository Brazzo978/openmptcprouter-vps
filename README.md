# OpenMPTCProuter VPS 0.1164-3K

Server release paired with [client v0.64.3-3K](https://github.com/Brazzo978/openmptcprouter/releases/tag/v0.64.3-3K). The tested platform is **Debian 13 amd64 with an x86-64-v3 CPU**. The kernel and binary package set remain frozen; the admin API is **0.18+20261030-3k7**.

## Install

Run this copyable command as root. It downloads the complete versioned bundle and its release checksum file, verifies the archive, and only then starts installation:

```sh
workdir=$(mktemp -d) && wget -P "$workdir" https://github.com/Brazzo978/openmptcprouter-vps/releases/download/v0.1164-3K/openmptcprouter-vps-0.1164-3K.tar.gz && wget -O "$workdir/SHA256SUMS" https://github.com/Brazzo978/openmptcprouter-vps/releases/download/v0.1164-3K/SHA256SUMS-vps-0.1164-3K && (cd "$workdir" && grep '  openmptcprouter-vps-0.1164-3K.tar.gz$' SHA256SUMS | sha256sum -c -) && tar -xzf "$workdir/openmptcprouter-vps-0.1164-3K.tar.gz" -C "$workdir" && cd "$workdir/openmptcprouter-vps-0.1164-3K" && ./run-vps-3k.sh install
```

Installation changes networking, services and the kernel. Debian APT access is required for operating-system dependencies. Reboot after installation to use the frozen kernel. SSH uses **65222**. Router connection settings are generated in `/root/openmptcprouter_config.txt`; the initial remote WireGuard profile is `/root/wireguard-client.conf`.

For manual preparation, extract the release archive and run `./run-vps-3k.sh prepare`; this rebuilds/verifies the API package without installing it. A Git clone alone does not include all frozen binary assets.

## Included behavior

- Kernel and headers **6.18.41-20261013.x64v3-omr-3k**, with **BBRv3 (`bbr`) as the default**.
- **21 frozen OMR packages** and three frozen helpers, checked against SHA-256 locks. Canonical download assets are hosted on the 3K mirror or Brazzo release; the installed OMR APT source is local. Pinned Ysurac source ancestry remains documented in source locks.
- Native MQVPN **0.16.2-3k2**, compiled FEC capability and LAN-prefix handling. FEC configuration is independent from compiled capability. The primary router defaults to **10.255.220.2** when available; explicit addresses and other users are preserved.
- Profiles API v2, transport/proxy coordination, confirmation/rollback and forwarding/WireGuard target updates for MQVPN, Glorytun TCP and No tunnel. Use the paired client for the profile UI.
- Independent Xray TCP reverse forwarding, native VPN forwarding, authenticated diagnostics with sensitive values redacted, and the existing removal of VPS router-backup endpoints.
- A Bash WireGuard client manager with individual permissions, IPv4 full-tunnel Internet support and a separate global LAN gate.

## WireGuard clients

Run `omr-wg-manager` as root for the menu. Scriptable examples:

```sh
omr-wg-manager status
omr-wg-manager add phone
omr-wg-manager add laptop --full
omr-wg-manager lan phone allow
omr-wg-manager disable phone
omr-wg-manager enable phone
omr-wg-manager remove phone
```

`show NAME` and `qr NAME` deliberately display private profile material. Use a private terminal; `qr` requires `qrencode`. See [the manager guide](docs/WIREGUARD-REMOTE-MANAGER.md) for export, migration and recovery details.

New split profiles route `10.255.0.0/16` and permit only the router GUI on its current tunnel address, TCP 80/443. New clients cannot access LAN devices by default. IPv4 Internet through the VPS is available with `--full` / `AllowedIPs = 0.0.0.0/0`, without granting LAN access.

LAN access requires **both** `omr-wg-manager lan NAME allow` and the router's global checkbox, or `wg-remote-lan-route --lan-access allow` on the VPS. Disabling either blocks existing LAN exchanges as well as new connections. Split profiles must also include the synchronized LAN subnet; re-export after enabling it. Existing legacy clients retain their documented migration behavior. No tunnel intentionally suspends tunnel-based router GUI/LAN access; manage that transition from the LAN or an independent path.

## Validation and limits

The API/kernel/frozen payload was clean-installed on Debian 13 and rebooted before the paired tests. Subsequent tests with the actual VMware r7 client passed native/independent Xray forwarding (17 checks), WireGuard GUI/full IPv4 Internet/peer lifecycle and a distinct Windows LAN permission/revocation matrix (28), and all six client profiles including real WireGuard GUI retargeting. The frozen hashes, installed package versions and service health were rechecked. The 0.1164 archive preserves those binaries; its release labels, source packaging and preparation are verified separately.

The x86 lab does not establish physical multi-WAN throughput, IPv6, mobile QR onboarding or arbitrary legacy upgrades. On the tested VMnet2 NAT path, MPTCP options were lost between the client and VPS; the other WAN negotiated MPTCP correctly. Source patches 030/040/050 are retained for MQVPN client maintenance; the frozen VPS server binary remains 0.16.2-3k2.
