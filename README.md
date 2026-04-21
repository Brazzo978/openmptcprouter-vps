# OpenMPTCProuter VPS scripts (omr-vps-0.1150-def)

This is the VPS part of OpenMPTCProuter, with my edits and custom repo and installation file.
The ideal client part for this release is 0.62.4-3K which is the latest stable release with all my edit , see the end of the file for the list of modification.

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
  https://raw.githubusercontent.com/Brazzo978/openmptcprouter-vps/omr-vps-0.1048-def/debian9-x86_64.sh \
  -o /root/debian9-x86_64.sh
chmod +x /root/debian9-x86_64.sh

KERNEL=6.12 /root/debian9-x86_64.sh

# or if you want to set your domain/FQDN used by OMR for some obfuscation / weird proxy stuff
VPS_DOMAIN="put.your.domain.here" KERNEL=6.12 /root/debian9-x86_64.sh
```

## What did i edit

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

## Patched client images

The `0.62.4-3K` client images used with this VPS branch include these patches:

- scheduler/CC sync fix in `openmptcprouter-vps` client init script
- `opkg`/`apk` feed regeneration pinned to the original `v0.62` feed paths
- tracker fixes for route recovery and state handling (`defaultgw`, IPv6 route lookup, `multipath` fallback, typo fixes, MTU helper cleanup)
- `omr-test-speed` updated to use repo-managed host lists first
- primary speed-test host lists now prefer local italian repo , Hetzner and Clouvider endpoints
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
