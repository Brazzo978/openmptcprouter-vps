# VPS 0.1164-3K refresh, 2026-11-09

This refresh replaces the published installation archive and updates the release
checksum file and installation instructions. The source tag and production
branch follow the refreshed source; the original release source was
`c903eb1d6080d64a4fb5aa9502bdd8837dce7421`.

Included changes since the original archive:

- `omr-rth` guided IPv4 return-to-home manager, with the installation client
  first, reference-style client wizard and connected-client display.
- The previous `omr-wg-manager` command is a compatibility alias.
- Default MTU 1320 and keepalive 25 for new configuration; explicit inherited
  values and existing profiles/keys are preserved.
- Admin API `0.18+20261030-3k8` retires obsolete LAN prefixes after an accepted
  subnet change, limited to the previous route and matching tunnel gateway and
  interface. The client-side CIDR collector correction is a separate client fix.

The kernel, headers, frozen 21 OMR packages, three helper artifacts, MQVPN
version, and existing profile/firewall features are unchanged. Their SHA-256
locks remain authoritative.

Validation includes guided-manager and LAN-route tests, candidate-preparation
guards, isolated real WireGuard/firewall checks, and live manager deployment and
LAN synchronization checks on an existing VPS. Release packaging verifies the
built API version and payload against the source, prepares the frozen local
repository and verifies the kernel pair without installing on the build host.
This refreshed archive has not been clean-installed from scratch.

Existing installations do not update automatically when GitHub assets change.
The main release one-liner is the installation entry point, not a promise of
disruption-free in-place upgrades. The live manager hotfix was deployed
separately with existing profiles and running tunnels preserved.
