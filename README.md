# OpenMPTCProuter VPS scripts (omr-vps-0.1049-def)

This is the VPS part of OpenMPTCProuter, with defaults moved to the `Brazzo978` namespace and `repoomr.3klab.com`.

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
  https://raw.githubusercontent.com/Brazzo978/openmptcprouter-vps/omr-vps-0.1049-def/debian9-x86_64.sh \
  -o /root/debian9-x86_64.sh
chmod +x /root/debian9-x86_64.sh

# set your domain/FQDN used by OMR
VPS_DOMAIN=vps.example.com KERNEL=6.12 /root/debian9-x86_64.sh
```

## Update an existing VPS

```bash
cd /root
rm -f /root/debian9-x86_64.sh
curl -fsSL \
  https://raw.githubusercontent.com/Brazzo978/openmptcprouter-vps/omr-vps-0.1049-def/debian9-x86_64.sh \
  -o /root/debian9-x86_64.sh
chmod +x /root/debian9-x86_64.sh

update=1 KERNEL=6.12 /root/debian9-x86_64.sh
```

## What this branch adds

- Uses your fork namespace (`Brazzo978`) by default.
- Uses `repoomr.3klab.com` for packages/artifacts.
- Installs and enables the MPTCP compat bridge (`omr-mptcp-compat`).
- Loads BPF MPTCP schedulers from `/usr/share/bpf/scheduler`.

## Post-install checks

```bash
uname -r
cat /proc/sys/net/mptcp/available_schedulers
cat /proc/sys/net/ipv4/tcp_congestion_control
systemctl --no-pager --full status mptcp-bpf-schedulers.service omr-mptcp-compat.timer
```

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
- primary speed-test host lists now prefer `repoomr.3klab.com` plus Hetzner and Clouvider endpoints

Artifacts prepared locally for this client build:

- `openmptcprouter-v0.62.1-3KTEST-6.6-r0+28431-92e020b50f-x86-64-generic-ext4-combined.img.gz`
- `openmptcprouter-v0.62.1-3KTEST-6.6-r0+28431-92e020b50f-x86-64-generic-ext4-combined-efi.img.gz`
- `openmptcprouter-v0.62.1-3KTEST-6.6-r0+28431-92e020b50f-x86-64-generic-ext4-combined.ova`
- `openmptcprouter-v0.62.1-3KTEST-6.6-r0+28431-92e020b50f-x86-64-generic-ext4-combined-efi.ova`
