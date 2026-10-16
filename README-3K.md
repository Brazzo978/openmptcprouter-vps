# OpenMPTCProuter VPS 0.1163-3K

This final VPS release pairs with client v0.64.2-3K. It retains the reviewed Debian 13 amd64/x86-64-v3 frozen base and kernel 6.18.41-20261013.x64v3-omr-3k from 0.1162-3K. The OMR package set remains 21 packages; the mqvpn executable package is the native 0.16.2-3k2 candidate with LAN-prefix handling and XQUIC FEC capability reporting. The separate libmqvpn0 package stays at upstream 0.16.2-1. FEC capability reporting does not itself enable redundant traffic.

The API package is omr-vps-admin 0.18+20261016-3k4. It retains the authenticated diagnostic logs, WireGuard remote access and LAN gate, and the existing XRay reverse forwarding path. The main MQVPN user's fixed IP defaults to 10.255.220.2 only when no explicit IP is configured and no other user owns that address. Existing MQVPN users and explicit addresses are preserved. The installer keeps the frozen source and kernel checks.

## Preparation and installation

On Debian 13 amd64 with an x86-64-v3 CPU, verify SHA256SUMS-vps-0.1163-3K against the downloaded release assets. Extract openmptcprouter-vps-0.1163-3K.tar.gz and enter its directory. Run ./run-vps-3k.sh prepare to rebuild the local API package without installation. An intentional installation uses ./run-vps-3k.sh install as root; it modifies networking, services and the kernel, and the kernel change requires a reboot. Debian APT access remains necessary for OS dependencies.

The archive contains the locked kernel image and headers, 21 frozen OMR packages, helper files, the API package and this source. The native MQVPN DEB and its provenance are also separate release assets. The versioned frozen lock points to the release asset for future fetches. The API and frozen payloads must match the release manifest and SHA-256 checksums.

## Validation scope

The 0.1161-3K clean baseline and kernel validation remain historical evidence; 0.1162-3K received a targeted API upgrade check. The new API package, MQVPN executable and frozen lock require their own unit tests, package verification, fresh-install or controlled upgrade checks, and final router reconnect/port-forward verification. See the attached 0.1163 validation report for completed checks. Two WANs have carried traffic on the live test topology; no aggregated-throughput benchmark has been established. Long-term XRay stability requires continued observation.

The WireGuard LAN gate is independent of native MQVPN LAN route registration. Disabling the remote WireGuard LAN permission still permits the router GUI and public Internet paths according to their existing rules. The full-tunnel helper and policy table 24612 are retained.

## Remote WireGuard access

The generated /root/wireguard-client.conf starts with AllowedIPs = 10.255.0.0/16. Once OMR is paired, the VPS permits only the router GUI on its tunnel IPv4 address, TCP ports 80 and 443. Access to LAN devices is denied on the VPS, even if a client selects AllowedIPs = 0.0.0.0/0.

For IPv4 Internet through the VPS, change the client's AllowedIPs to 0.0.0.0/0 and use a public DNS server, for example 1.1.1.1. The VPS forwards and NATs this traffic to its WAN public IPv4 address. This does not enable OMR LAN access.

The authenticated VPS API also exposes `GET /wireguard/remote-access` and `POST /wireguard/remote-access` with `{"lan_access": true}` or `false`. The router GUI checkbox uses these endpoints. Only the primary writable user or primary administrator can change this global setting; other authenticated users can read it. The response reflects the helper state after applying the change; failed changes return an error.

Run as root on the VPS to control the persistent LAN permission:

    wg-remote-lan-route --lan-access status
    wg-remote-lan-route --lan-access allow
    wg-remote-lan-route --lan-access deny

The state file is /etc/openmptcprouter-vps-admin/wg-remote-lan-access.enabled (mode 0600). An absent file means deny. The helper refreshes the router GUI/LAN addresses from the locally synchronized OMR configuration and uses policy table 24612 for LAN routes. For MQVPN, `/lan` registers each configured user's LAN prefixes with the native MQVPN server, regardless of this WireGuard checkbox. The timer replays those routes after an MQVPN restart; before opening remote WireGuard LAN access it also verifies the primary user's registered prefixes and single active session. Existing OMR port forwards using public-port DNAT to the router's MQVPN address followed by router-side DNAT to a LAN host already work with the stock MQVPN server. Native LAN-prefix registration adds direct routing for packets that still have a LAN destination address when they reach the MQVPN server, including remote WireGuard client traffic. For a split tunnel, add the desired OMR LAN subnet to the client's AllowedIPs as well; a full IPv4 tunnel already covers it, but the VPS gate must still be enabled. Disabling the permission leaves GUI access and public Internet available.