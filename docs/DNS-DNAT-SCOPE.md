# VPS-only DNS and Internet forwarding correction

Admin API **0.18+20261030-3k10**, included in the **2026-11-10** refresh of
VPS **v0.1164-3K**, corrects the destination scope of generated DNAT rules.
Existing client firmware, including v0.64.3-3K, needs no rebuild for this fix.

With bulk redirection enabled, the earlier rules matched any packet with a
destination port in the forwarded range, including a router's outbound DNS
request to an external resolver. The VPS could redirect that request back to
the router instead of sending it to the Internet. Individual forwarded ports,
including entries requested through UPnP, could have the same effect on
matching outbound traffic.

Generated bulk and individual DNAT rules now require `fib daddr type local`:
the original destination must be an address owned by the VPS. This applies
to IPv4 and IPv6, TCP and UDP. Explicit destination/source restrictions,
selected tunnel targets and INPUT acceptance rules retain their behavior.
The bulk forwarding setting is not enabled by this correction.

An incoming connection to a published VPS address still matches its forward.
A VPN client's request to an external DNS or HTTP server does not. The test
also allows traffic from VPN clients addressed to the VPS itself to remain
eligible for forwarding; hairpin return routing and filtering still depend
on the installation's existing configuration.

## Validation and limits

- The combined API and VPS source suite passes 1,253 tests; nine optional
  integration cases are skipped. The standalone VPS suite accounts for 148
  of the passing tests.
- Ten regression cases check the renderer's destination scope across both IP
  families and protocols, plus preserved acceptance and explicit match fields.
- Eleven real packet checks in isolated Linux namespaces cover the broken
  baseline, corrected bulk and individual forwarding, DNS/Internet egress,
  public TCP/UDP forwarding and hairpin with an explicit lab return path.
- On an affected existing VPS, the renderer was replaced and only the admin
  API restarted. Generated DNAT rules were reloaded atomically after an
  `nft -c` check. DNS through MQVPN and the router's local resolver recovered
  with bulk forwarding still enabled. Configuration, WireGuard peers and the
  running MQVPN process were preserved.

The refreshed release is prepared and checked without installing it on the
build host. This refresh has not received a new clean installation test;
earlier release installation tests are baseline evidence only. Existing VPS
installations do not update automatically when GitHub release assets change.

Run the packet regression lab as root on a Linux QA host with `iproute2` and
`nftables`: `python3 tests/run_dnat_scope_netns.py`. It creates uniquely named
network namespaces, exercises their private rules and links, and removes
them afterwards; it does not modify the host's firewall or routes.
