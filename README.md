# OpenMPTCProuter VPS 0.1164-3K

Server release paired with [client v0.64.3-3K](https://github.com/Brazzo978/openmptcprouter/releases/tag/v0.64.3-3K). The tested platform is **Debian 13 amd64 with an x86-64-v3 CPU**. The archive refreshed on **2026-11-09** includes `omr-rth` and admin API **0.18+20261030-3k9**. The kernel and frozen VPN package set are unchanged.

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
- The `omr-rth` guided return-to-home WireGuard manager, with the installation client first, add/list/remove, connected-client display, individual permissions, IPv4 full-tunnel Internet support and a separate global LAN gate.
- Retirement of obsolete router LAN routes after an accepted subnet change, constrained to the previous prefix and the same VPN gateway/interface. API 3k9 also validates and normalizes the legacy double-mask LAN payload; see [LAN subnet synchronization](docs/LAN-SUBNET-SYNC.md).

## WireGuard clients

After activating a remote WireGuard profile, open the router's current tunnel
address in your browser. With the standard primary MQVPN router this is
**https://10.255.220.2/** or **http://10.255.220.2/**; log in with the router's
normal LuCI credentials. GUI access on TCP 80/443 works even with LAN access
disabled. The router's LAN address (for example `10.1.1.1`) is a LAN destination
and requires LAN permission, just like other LAN devices. Ping/SSH are not part
of the default GUI-only permission.

LAN access requires the router's **Allow remote WireGuard access to LAN**
checkbox, the individual client grant in `omr-rth`, and matching client routes.
Using `AllowedIPs = 0.0.0.0/0` sends IPv4 Internet through the VPS but does not
unlock the LAN. See [RTH access behavior and setup](docs/WIREGUARD-REMOTE-MANAGER.md#access-the-router-after-connecting).

The published **v0.64.3-3K client is compatible with this RTH manager** and its
unchanged remote-access API. API **3k9** also accepts the old client's specific
`IPv4/prefix/retained-mask` LAN payload, so that subnet-change case no longer
requires a client rebuild. The source-level client collector correction is
scheduled for v0.64.4-3K. Updating the VPS does not replace existing firmware.

The archive refreshed on **2026-11-09** includes the `omr-rth` command and
guided menu below. Earlier downloads used `omr-wg-manager`.

Run `omr-rth` as root for the guided menu. The installation client is listed first, followed by existing additional clients. The previous `omr-wg-manager` command remains an alias. Scriptable examples:

```sh
omr-rth status
omr-rth add phone
omr-rth add laptop --full
omr-rth lan phone allow
omr-rth disable phone
omr-rth enable phone
omr-rth remove phone
```

`show NAME` and `qr NAME` deliberately display private profile material. Use a private terminal; `qr` requires `qrencode`. See [the manager guide](docs/WIREGUARD-REMOTE-MANAGER.md) for export, migration and recovery details.

RTH profiles default to MTU **1320** and keepalive **25 seconds**. Newly generated profiles preserve explicit values inherited from the installation profile, including keepalive `0`/`off`. Existing client profiles and keys are preserved.

New split profiles route `10.255.0.0/16` and permit only the router GUI on its current tunnel address, TCP 80/443. New clients cannot access LAN devices by default. IPv4 Internet through the VPS is available with `--full` / `AllowedIPs = 0.0.0.0/0`, without granting LAN access.

LAN access requires **both** `omr-rth lan NAME allow` and the router's global checkbox, or `wg-remote-lan-route --lan-access allow` on the VPS. Disabling either blocks existing LAN exchanges as well as new connections. Split profiles must also include the synchronized LAN subnet; re-export after enabling it. Existing legacy clients retain their documented migration behavior. No tunnel intentionally suspends tunnel-based router GUI/LAN access; manage that transition from the LAN or an independent path.

## Validation and limits

The API/kernel/frozen payload was clean-installed on Debian 13 and rebooted before the paired tests. Subsequent tests with the actual VMware r7 client passed native/independent Xray forwarding (17 checks), WireGuard GUI/full IPv4 Internet/peer lifecycle and a distinct Windows LAN permission/revocation matrix (28), and all six client profiles including real WireGuard GUI retargeting. The frozen hashes, installed package versions and service health were rechecked.

The 2026-11-09 refresh adds the LAN route-retirement API fix and guided manager. The manager passed 92 automated tests, 41 isolated real WireGuard/firewall traffic checks, and 14 deployment checks on an existing VPS. The LAN fix passed helper/kernel route tests and live subnet-change verification. Packaging preparation, API package contents, frozen hashes and kernel checks are verified separately; this refreshed archive has not been clean-installed from scratch.

The x86 lab does not establish physical multi-WAN throughput, IPv6, mobile QR onboarding or arbitrary legacy upgrades. On the tested VMnet2 NAT path, MPTCP options were lost between the client and VPS; the other WAN negotiated MPTCP correctly. Source patches 030/040/050 are retained for MQVPN client maintenance; the frozen VPS server binary remains 0.16.2-3k2.
