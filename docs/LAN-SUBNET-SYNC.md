# LAN subnet synchronization hotfix — 2026-11-09

Changing a router LAN through LuCI can retain `network.lan.netmask` while storing
`network.lan.ipaddr` in CIDR form. The former client joined both values
unconditionally: `10.1.1.1/23` and `255.255.254.0` became
`10.1.1.1/23/255.255.254.0`. The VPS rejected POST `/lan` with HTTP 422 and kept
the earlier LAN configuration. Periodic reconcilers then retained the old routes.

The client now keeps an existing CIDR suffix, appends a separate mask only to
bare IPv4 addresses, supports multiple configured addresses, and matches LAN-zone
interface names exactly. The package revision is incremented to `0.95-r5`.

A second issue affected the VPS: `omr-service` added each configured LAN route
but did not remove a route after its prefix disappeared from configuration.
The authenticated `/lan` handler now retires obsolete main-table routes after
saving/accepting the update. Removal requires an exact previous prefix, exact
previous tunnel gateway and an OMR VPN device. Prefixes still configured by
another user, unrelated routes and default routes are preserved. Command
failures produce an explicit warning. The existing service continues to add
current main-table routes; the WG timer updates its separate policy table.

For `10.1.1.1/23`, the normalized network is **10.1.0.0/23**, covering
10.1.0.0–10.1.1.255. A route displayed as `10.1.0.0/23` is correct.

## Validation

- 15 client shell regression tests passed with Bash/Dash fixtures, exercising
  the production collector and setter. The actual failing configuration and
  corrected payload were also executed on the installed router's BusyBox shell.
- 12 VPS regression tests passed for exact route removal, prefix ownership,
  gateway/device restrictions, default-route preservation and failure handling.
- Five real Linux network-namespace checks passed: remove the old prefix,
  preserve the new /23, preserve an unrelated VPN route, preserve the default
  gateway and repeat safely. No production routes were used by this test.
- Live acceptance on the affected ARM 0.64.2 installation and paired 3k7 API:
  authenticated `/lan` accepted the corrected prefix; MQVPN route grants and
  main/WG policy tables contained the new /23, with the old /24 removed.
  Router GUI TCP 80/443 worked over both tunnel and LAN addresses. The router
  and existing LAN devices in both halves of the /23 answered ICMP probes.
- The global WG LAN permission remained enabled. These incident checks did
  not create an external WireGuard peer or claim a fresh full WG-client test.
- Only the API service was restarted for the server hotfix; MQVPN's process and
  the VPS default route remained unchanged. The router network configuration
  was not modified. Both installed source files have root-only backup locations.

## Packaging status

The VPS 0.1164 archive refreshed on 2026-11-09 includes this server correction
in admin package **0.18+20261030-3k8**, with matching installer/preparation
version checks. The original targeted hotfix on the affected VPS patched the
Python source directly and still reports 3k7; its deployment evidence records
the source hash. Frozen kernel and VPN binaries are unchanged.

The client collector fix is a separate source change and installed hotfix.
Updating the VPS archive does not add that client-side correction to the
previously published 0.64.3 firmware images.
