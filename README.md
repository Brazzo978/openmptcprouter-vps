# OpenMPTCProuter VPS scripts (omr-vps-0.1048-def)

This is the VPS part of [OpenMPTCProuter](https://www.openmptcprouter.com/), with defaults moved to the `Brazzo978` namespace and `repoomr.3klab.com`.

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

# set your domain/FQDN used by OMR
VPS_DOMAIN=vps.example.com KERNEL=6.12 /root/debian9-x86_64.sh
```

## Update an existing VPS

```bash
cd /root
rm -f /root/debian9-x86_64.sh
curl -fsSL \
  https://raw.githubusercontent.com/Brazzo978/openmptcprouter-vps/omr-vps-0.1048-def/debian9-x86_64.sh \
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
