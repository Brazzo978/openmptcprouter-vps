# OpenMPTCProuter VPS scripts (omr-vps-0.1048-def)

This is the VPS part of OpenMPTCProuter, with my edits and custom repo and installation file.

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

## Built-in health check

The installer also installs `omr-check` automatically in `/usr/bin/omr-check`.

You can run it directly:

```bash
omr-check
```

It shows:

- current MPTCP scheduler on the VPS
- current TCP congestion control
- which VPN is currently in use
- per-VPN service state
- whether a VPN peer is currently reachable
- detected active peer endpoints when present

## Patched client images

The `0.62.1-3KTEST` client images used with this VPS branch include these patches:

- scheduler/CC sync fix in `openmptcprouter-vps` client init script
- `opkg`/`apk` feed regeneration pinned to the original `v0.62` feed paths
- tracker fixes for route recovery and state handling (`defaultgw`, IPv6 route lookup, `multipath` fallback, typo fixes, MTU helper cleanup)
- `omr-test-speed` updated to use repo-managed host lists first
- primary speed-test host lists now prefer local italian repo , Hetzner and Clouvider endpoints
- AND A LOT, LOT , LOT, LOT , LOT of more fixes will provide a changelog later.
