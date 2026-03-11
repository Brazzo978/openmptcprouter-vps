# Client 0.62 Failover And Master Selection Notes

This note documents the client-side WAN failover logic observed in the `0.62 / 6.6` images used with the `omr-vps-0.1049-def` server stack.

## Scope

These behaviors are implemented on the client, not on the VPS:

- `etc/init.d/omr-tracker`
- `usr/share/omr/post-tracking.d/002-error`
- `usr/share/omr/post-tracking.d/003-up`
- `usr/share/omr/post-tracking.d/021-latencies`
- `usr/share/omr/lib/common-post-tracking.sh`

The VPS does not decide which WAN becomes the client master. The client tracker does.

## Tracker Defaults

Default tracker settings from `etc/config/omr-tracker`:

- `timeout=2`
- `count=2`
- `tries=3`
- `interval=2`
- `tries_up=5`
- `failure_interval=20`
- `reliability=1`

The client continuously probes multiple IPv4/IPv6 hosts. When a link is considered failed, the tracker runs the error hooks. When a link recovers, the up hooks run.

## Hard Failover

When a WAN is marked `ERROR`, `post-tracking.d/002-error` does the following:

- marks the interface state as `down`
- emits an iface hotplug `disconnecting` event
- removes server routes attached to the failed WAN
- marks Glorytun UDP path addresses as down when relevant
- restarts the bound VPN service when needed (`openvpn`, `glorytun`, `glorytun-udp`, `mlvpn`, `dsvpn`)
- rebuilds default and server routes using the remaining healthy WANs

Result:

- if the current master WAN fails, traffic is moved automatically to another available WAN
- if `openmptcprouter.settings.master=balancing`, ECMP-style routes are rebuilt across all healthy links
- otherwise, default/server routes are reassigned to surviving interfaces

This is route-driven failover, not bandwidth-scored failover.

## Soft Master Switch By Latency

`post-tracking.d/021-latencies` can promote a non-master WAN to `master` without a hard outage.

This only runs when:

- the candidate interface is currently `multipath='on'`
- `openmptcprouter.settings.master` is `change`, `dynamic`, or empty

Current logic:

### `master=change` (or empty)

The new interface becomes master if:

- `new_latency < current_master_latency / 1.5`

In practice, the candidate must be about 33% better than the current master.

### `master=dynamic`

The new interface becomes master if:

- `new_latency < current_master_latency / 2`
- `latency_previous < current_master_latency / 2`

This is stricter and requires two good samples to reduce flapping.

When the switch happens:

- previous master is set back to `on`
- candidate interface is set to `master`
- the change is logged

## Recovery Behavior

When an interface comes back up, `post-tracking.d/003-up` restores its routing role:

- if the interface is configured as `master`, it can reclaim the default route
- in `balancing`, weighted default routes are rebuilt
- in non-balancing modes, server routes are restored on the recovered link

So a preferred master can take its role back after recovery.

## Practical Summary

- If the master WAN actually fails, failover is automatic.
- If another WAN has much lower latency, it can become master automatically in `change` or `dynamic`.
- `balancing` behaves differently: it rebuilds multipath routes across available links instead of treating a single WAN as the long-term master.
- The decision is based mainly on tracker state, route availability, and latency. It is not based on measured throughput.

## Known Fragility

There are minor code-quality issues in the client scripts:

- a typo exists in `usr/share/omr/post-tracking.d/003-up` (`openmtpcprouter` instead of `openmptcprouter`)
- some routing checks fall back between `openmptcprouter.*.multipath` and `network.*.multipath`, which can be fragile if those diverge

These do not invalidate the failover logic, but they are worth keeping in mind when debugging edge cases.
