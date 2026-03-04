# Proxy UDP Notes

This file documents the client-side proxy behavior that matters when pairing the `0.62` client tree with the custom VPS stack.

## Scope

These notes describe how UDP is handled by:
- Shadowsocks
- V2Ray
- XRay

They are based on the patched `0.62` client tree and its current tracker / proxy logic.

## Shadowsocks UDP behavior

The `Shadowsocks UDP` checkbox in the client UI does **not** make Shadowsocks the normal UDP path.

UI label:
- `When proxy shadowsocks is used, use it for UDP if VPN down`

That description is accurate.

### What it really does

When this setting is enabled:
- `openmptcprouter.settings.shadowsocksudp=1`

the client tracker enables UDP redirection through Shadowsocks **only when the default VPN tunnel is detected as down**.

On tunnel failure:
- the tracker sets `shadowsocks-libev.ss_rules.redir_udp='hi1'`
- then reloads the Shadowsocks rules

On tunnel recovery:
- the tracker deletes `shadowsocks-libev.ss_rules.redir_udp`
- then reloads the Shadowsocks rules again

Relevant client logic:
- `omr-tracker/files/usr/share/omr/post-tracking.d/002-error`
- `omr-tracker/files/usr/share/omr/post-tracking.d/003-up`

### Practical consequence

With `proxy=shadowsocks`:
- TCP uses the Shadowsocks proxy path
- UDP normally stays on the default VPN path
- UDP is moved to Shadowsocks only as a fallback when the VPN is down

This fallback requires:
- Shadowsocks proxy up
- `shadowsocks-libev.hi1.mode='tcp_and_udp'`
- no obfs on `sss0`

### Aggregation impact

When UDP falls back to Shadowsocks:
- it uses the native UDP handling of Shadowsocks
- it is **not** wrapped into a TCP stream
- it therefore does **not** benefit from MPTCP-style aggregation on that proxy path

So this checkbox is best understood as:
- emergency UDP continuity
- not aggregated UDP transport

## V2Ray / XRay UDP behavior

V2Ray and XRay behave differently.

When `redirect_udp=1`:
- UDP is handled by the V2Ray/XRay transparent proxy path
- it does not wait for the VPN to fail first

In this OMR configuration:
- UDP enters the local transparent inbound (`dokodemo-door`)
- then is forwarded through the configured outbound

The default outbound settings in this tree use a stream-based transport:
- `ss_network='tcp'`

### Practical consequence

With `proxy=v2ray` or `proxy=xray` and UDP redirect enabled:
- application UDP is proxied by the V2Ray/XRay engine
- that UDP is effectively carried through the outbound stream path
- in this setup, that is functionally much closer to `UDP over TCP`

### Aggregation impact

Because the outbound path is stream-based in this configuration:
- UDP sent through V2Ray/XRay can ride the same TCP/MPTCP-capable transport path
- this is the proxy mode that can preserve the benefit of an aggregated stream path for UDP-like traffic

## Summary

- `Shadowsocks UDP checkbox`:
  - fallback only
  - activates only if the VPN is down
  - UDP stays native UDP on the Shadowsocks path
  - no MPTCP aggregation benefit on that fallback

- `V2Ray / XRay UDP redirect`:
  - active while the proxy is enabled
  - UDP is handled directly by the proxy engine
  - in this tree it is carried through a stream/TCP-based outbound
  - this is the path that can keep the benefit of the aggregated stream transport
