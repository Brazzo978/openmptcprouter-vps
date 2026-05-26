# OpenMPTCProuter VPS scripts (omr-vps-0.1155-def)

This is the VPS part of OpenMPTCProuter, with my edits and custom repo and installation file.

This VPS release is intended for the `OpenMPTCProuter v0.62.13-3K` client release.
Use `0.1155-def` with client `.13` when testing MQVPN scheduler/CC/MTU profiles and forced TCP port-forward over Xray reverse path.

## Requirements

- Debian 12 or Debian 13
- Root shell
- Public IPv4 VPS

Note: on fresh install (`update=0`), Debian 12 is auto-upgraded to Debian 13 by the installer policy.

## Quick install (new VPS)

```bash
apt-get update
apt-get install -y curl ca-certificates

curl -fsSL \
  https://raw.githubusercontent.com/Brazzo978/openmptcprouter-vps/omr-vps-0.1155-def/debian9-x86_64.sh \
  -o /root/debian9-x86_64.sh
chmod +x /root/debian9-x86_64.sh

KERNEL=6.12 /root/debian9-x86_64.sh

# or if you want to set your domain/FQDN used by OMR for some obfuscation / weird proxy stuff
VPS_DOMAIN="put.your.domain.here" KERNEL=6.12 /root/debian9-x86_64.sh
```

## What did i edit

- `0.1155-def` is compatible with client `v0.62.13-3K`.
- Ships the rebuilt `6.12.67-x64v3-net-perf-3k-xanmod1-v2` kernel package (`6.12.67-9`) with MPTCP BPF scheduler support and BBR/NanBBR sidecars.
- Keeps `bbr` as BBRv3/default, and adds synced test choices `bbr1` and `bbr2` for client/server MPTCP congestion-control testing.
- Adds MQVPN server installation, config, systemd unit, Shorewall interface/SNAT handling and health checks.
- Pins the patched MQVPN server artifact with `[Routes]` support, scheduler `backup`/`rap`, CC selection, and MTU/PMTUD packet-size controls required by client `.13`.
- Exposes MQVPN config through `omr-admin` so client `.13` can auto-sync key, port and tunnel IPs.
- Keeps MQVPN FEC internal/default only; it is not exposed as a user GUI/server toggle.
- Supports client `.13` forced TCP port-forward over dedicated Xray reverse path.
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

The `v0.62.13-3K` client images used with this VPS branch include these patches:

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
