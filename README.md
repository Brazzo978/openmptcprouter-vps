# OpenMPTCProuter VPS scripts (omr-vps-0.1156-def)

This is the VPS part of OpenMPTCProuter, with my edits and custom repo and installation file.

This VPS release is intended for the `OpenMPTCProuter v0.62.14-3K` client release.
Use `0.1156-def` with client `.14`.

## Requirements

- Debian 12 or Debian 13
- Root shell
- Public IPv4 VPS

Note: on a fresh install, Debian 12 is auto-upgraded to Debian 13 by the installer policy.

## Quick install (new VPS)

`0.1156-def` is fresh-install only. It intentionally refuses to run on an
existing OpenMPTCProuter VPS; reinstall the VPS from a clean Debian image first.

- The installer always uses the pinned OMR 6.12 kernel; it is not selectable.
- No in-place OMR updater or update service is installed.
- The VPS is provisioned for one OpenMPTCProuter user, without multi-tenant
  client backup/restore assets.
- MLVPN, UBOND and Pi-hole are not installed or configured.

```bash
apt-get update
apt-get install -y curl ca-certificates

curl -fsSL \
  https://raw.githubusercontent.com/Brazzo978/openmptcprouter-vps/omr-vps-0.1156-def/debian9-x86_64.sh \
  -o /root/debian9-x86_64.sh
chmod +x /root/debian9-x86_64.sh

/root/debian9-x86_64.sh

# or if you want to set your domain/FQDN used by OMR for some obfuscation / weird proxy stuff
VPS_DOMAIN="put.your.domain.here" /root/debian9-x86_64.sh
```

## What did i edit

- `0.1156-def` is compatible with client `v0.62.14-3K`.
- MQVPN defaults to CUBIC while BBR2 remains an experimental opt-in.
- Includes the XQUIC BBR2 64-bit loss-round counter fix and bounded idle polling.
- Limits MQVPN systemd restart bursts to avoid persistent recovery storms.
- Blocks in-place upgrades from older VPS releases; this release must be installed on a clean Debian VPS.
- Ships the rebuilt `6.12.67-x64v3-net-perf-3k-xanmod1-v2` kernel package (`6.12.67-10`) with MPTCP BPF scheduler support, the fixed NanBBR profiles and `nanbbr1_var`, `nanbbr2_var`, `nanbbr3_var`.
- Keeps `bbr` as BBRv3/default, and adds synced test choices `bbr1` and `bbr2` for client/server MPTCP congestion-control testing.
- Adds MQVPN server installation, config, systemd unit, Shorewall interface/SNAT handling and health checks.
- Pins the patched MQVPN server artifact with `[Routes]` support, scheduler `backup`/`rap`, CC selection, and MTU/PMTUD packet-size controls required by client `.14`.
- Exposes MQVPN config through `omr-admin`; client `.14` synchronizes key, port, scheduler, CC, MTU, effective packet-size profile, PMTUD and log level.
- Keeps MQVPN FEC internal/default only; it is not exposed as a user GUI/server toggle.
- Adds an opt-in MQVPN2 experiment based on upstream MQVPN `0.14.0`
  (`535100137ad1931ab07d5ec4787f23744349b3e6`) without replacing MQVPN.
- Supports client `.14` forced TCP port-forward over dedicated Xray reverse path.
- Rejects forced Xray reverse TCP port-forward ranges with a clean API error; use one TCP source port per force-Xray rule.
- Keeps UDP port-forward on the active VPN tunnel even when the client rule has the force-Xray flag enabled.
- Preserves DNAT destination port for forwarded ports, e.g. public `2222` to router `22`.
- Uses my repo for packages/artifacts.
- Installs and enables the MPTCP compat bridge (`omr-mptcp-compat`) needed for scheduler and CC sync from client to vps.
- Loads BPF MPTCP schedulers from `/usr/share/bpf/scheduler` Custom kernel based on the default one ,recompiled kernel with bpf support on the vps side.
- Removed legacy and newer stull that only makes confusion
- fixed glorytun tcp/udp on debian 13 (now forced to use deb13)
- Installs `gtun-swap` for post-install Glorytun TCP binary swap tests (switch the default glorytun tcp with my own alpha version , my version is optimized to prefer stability over anything , switch needs to be done both on server and on client for things to work , will not affect other tunnel types).

## Built-in health check

The installer also installs `omr-check` automatically in `/usr/bin/omr-check`.

You can run it directly:

```bash
omr-check
```
<img width="595" height="220" alt="image" src="https://github.com/user-attachments/assets/1faed682-df20-4224-b26d-a6495cf1a1d9" />

It shows:

- current MPTCP scheduler on the VPS
- current TCP congestion control
- which VPN is currently in use
- per-VPN service state
- whether a VPN peer is currently reachable
- detected active peer endpoints when present

## Compatible client images

The `v0.62.14-3K` client images used with this VPS branch include these patches:

- scheduler/CC sync fix in `openmptcprouter-vps` client init script
- `opkg`/`apk` feed regeneration pinned to the original `v0.62` feed paths
- tracker fixes for route recovery and state handling (`defaultgw`, IPv6 route lookup, `multipath` fallback, typo fixes, MTU helper cleanup)
- `omr-test-speed` updated to use repo-managed host lists first
- primary speed-test host lists now prefer local italian repo , Hetzner and Clouvider endpoints
- MQVPN client integration with automatic key/config sync from VPS API
- MQVPN scheduler/CC/MTU profile GUI: safe, default, performance, extreme
- forced TCP port-forward over dedicated Xray reverse path
- force-Xray range guard: one TCP source port per rule, range requests are rejected cleanly
- UDP fallback to the active VPN tunnel when force-Xray is enabled on a mixed TCP/UDP rule
- AND A LOT, LOT , LOT, LOT , LOT of more [Changelog](Vanilla-Changelog.md).

## Experimental MQVPN2

MQVPN2 is enabled by default on this beta branch and is integrated with
`omr-admin` and the client as a mutually exclusive experimental VPN. It
coexists with the stable package
and files using:

- binary `/usr/local/bin/mqvpn2`
- config `/etc/mqvpn2/server.conf`
- service `mqvpn2-server.service`
- UDP port `65412`
- subnet `10.255.248.0/24`
- TUN interface `mqvpn2`
- scheduler `wlb` and congestion control `cubic`

The installer is fresh-only and must be run on a clean test VPS. To make the
default explicit:

```bash
MQVPN2=yes VPS_DOMAIN="put.your.domain.here" \
  /root/debian9-x86_64.sh
```

With no `MQVPN2_BINARY_URL`, the installer builds the pinned upstream commit
from source with the hybrid TCP lane and server TCP egress disabled:

```text
BUILD_TESTING=OFF
MQVPN_ENABLE_HYBRID_TCP_LANE=OFF
MQVPN_ENABLE_HYBRID_TCP_EGRESS=OFF
XQC_ENABLE_UNLIMITED=OFF
XQC_ENABLE_FEC=ON
XQC_ENABLE_XOR=ON
```

The pinned source references the XQUIC BBR2 callback unconditionally, so XQUIC
must still be compiled with `XQC_ENABLE_BBR2=ON`; MQVPN2 does not select it at
runtime because its server profile is pinned to `CC = cubic`.

Before building, the installer downloads `mqvpn2-datagram-stability.patch` from
the configured `OMR_VPS_BRANCH`, verifies its pinned SHA-256 and applies it
fail-closed to the clean upstream checkout. This is the same patch used by the
client package: it provides the 64-bit BBR2 loss-round counter, bounded idle
timers and CUBIC defaults. FEC and XOR remain enabled because the client exposes
the `backup_fec` scheduler; the hybrid TCP lane and egress remain disabled.

No MQVPN2 artifact is included in this repository. An optional
`MQVPN2_BINARY_URL` must point to a self-contained tarball containing
`bin/mqvpn2`, `bin/mqvpn`, `mqvpn2`, or `mqvpn`; the installer always installs
that executable as `/usr/local/bin/mqvpn2` and never imports bundled
`libmqvpn` libraries.

## Glorytun swap helper

`gtun-swap` is installed automatically on the VPS (`/usr/bin/gtun-swap`).

It snapshots the current `glorytun-tcp` binary to:

- `/usr/local/lib/gtun-swap/glorytun-tcp.original`

Optional custom binary slot:

- `/usr/local/lib/gtun-swap/glorytun-tcp.omrdev5`

On `0.1150`, installer also tries to install `omr-glorytun-tcp-omrdev5` from your APT repo and auto-populates the slot.

Usage:

```bash
gtun-swap status
gtun-swap import /root/glorytun-2.0.0-omrdev5-linux-glibc
gtun-swap omrdev5
gtun-swap orig
```
