# OpenMPTCProuter VPS 0.1161-3K

Release 0.1161-3K pairs with OpenMPTCProuter v0.64.2-3K-rc2. The VPS base is official stable 0.1081 at 44958fbac2c1c06c2759aa699b37cc537120fa13. Existing older 3K branches remain separate.

The VPS kernel is 6.18.41-20261013.x64v3-omr-3k, derived from Ysurac/linux commit 1db16030b9d4f56787cd01d52adeeaa650ea5994 and the official x64v3 configuration. The vendored stack includes the selected XanMod patches, stable 6.18.41, OMR MPTCP/BBRv3 and 15 custom TCP controls. BBRv3, named bbr, is the default. All source inputs and binary image/headers are locked under cc/.

The API source and deterministic Debian builder are included in admin/. The port adds verified congestion selection with rollback, NanBBR VAR 1..100, effective XRay TCP reverse forwarding, and a WireGuard remote client path through the VPS to the OMR GUI.

The 21 OMR packages have fixed version, architecture, size, SHA256 and versioned HTTPS mirror URL in frozen/omr-amd64.lock.json. Original upstream URLs remain recorded. The installer uses verified local assets and refuses unverified OMR fallbacks. API /update and omr-update refuse upstream updates on marked frozen installations.

## Preparation and use

From this repository, run ./run-vps-3k.sh prepare to build the API package without installation. Run python3 ./frozen/freeze.py fetch to fetch and verify locked OMR packages, or python3 ./cc/fetch-packages.py to fetch and verify the reviewed kernel pair.

The install mode fetches missing locked kernel files, verifies the pair and API before installer execution, and is intended for an explicit deployment. A disposable Debian 13 VM is used for installation verification; consult the release fresh-install report for the exact result.

For independent source review or compilation, use separate empty workdirs:
./cc/build-kernel.sh prepare /tmp/omr-3k-source-review
OMR_3K_BUILD_JOBS=12 ./cc/build-kernel.sh build /tmp/omr-3k-kernel-build

The binary lock accepts the published reviewed artifacts. Local rebuilt binaries can differ with compiler and build metadata and require an intentional lock update after validation. Generated .deb files are excluded from Git.

## Validation and limits

The complete updated API suite passed: 1008 passed, 9 skipped. Exact source-stack replay, patch checksums, binary package contents, BBRv3/BBR1 BTF IDs and corrupt-file rejection were verified. All 21 OMR mirror assets and the final kernel pair were downloaded via HTTPS and matched their locked hashes.

The exact final VPS image was booted in isolated QEMU: BBRv3 default, 15/15 custom modules loaded, 18/18 real TCP loopback transfers passed, no BUG/Oops/panic. All three native NanBBR VAR module parameters accepted and read back 1, 25, 50, 80 and 100, rejected 0 and 101 without changing the previous value, and restored 50. See validation/vps-kernel-boot.json. XRay reverse forwarding also passed a real TLS loopback test.

WAN behavior and the complete remote WireGuard GUI path remain deployment checks. Clean-install and reboot results are recorded in the release verification report. Production systems were not installed or rebooted.

The supported frozen installer path is Debian13 amd64 with local files and SOURCES=no. OMR inputs are fixed while normal OS security updates remain separate. The installer retains legacy Bullseye runtime dependencies such as libmbedcrypto3/libpcre3. Server MLVPN/OpenVPN bonding remain for older clients; their removal is client-only.

## Release bundle

Download openmptcprouter-vps-0.1161-3K.tar.gz and SHA256SUMS-vps-0.1161-3K from the GitHub release. The archive includes the exact kernel/headers, local API package, all 21 locked OMR packages and helper files.

On Debian 13 amd64 with an x86-64-v3 capable CPU, verify the archive, extract it, and enter the extracted directory:

    sha256sum --ignore-missing -c SHA256SUMS-vps-0.1161-3K
    tar -xzf openmptcprouter-vps-0.1161-3K.tar.gz
    cd openmptcprouter-vps-0.1161-3K
    ./run-vps-3k.sh prepare

Preparation rebuilds only the local API package and does not install services. For an intentional VPS deployment, run the following as root:

    ./run-vps-3k.sh install

The installer changes networking/services and installs the bundled kernel. A reboot is required to use the new kernel. Debian APT access is still required for OS dependencies; only the OMR payloads are bundled and locked. Run the wrapper rather than downloading or piping the legacy upstream installer. This prerelease still requires real multi-WAN and complete remote WireGuard GUI validation. Consult the attached report for full VPS installation results.

## Independence corrections in 0.1161

Frozen installation and API metadata discovery use explicit settings or local interface/hostname data. No Ysurac metadata endpoint, APT key refresh or automatic upstream OMR update is used in the supported frozen path. The kernel source is preserved at the identical commit in Brazzo978/openmptcprouter-linux with tag3k-base-6.18-1db1603. Original upstream references remain as provenance. Debian OS/security dependencies still come from Debian repositories.

The API builder works with umask022 or077 and produces the same package. A clean install skips removal of nonexistent legacy iperf packages. All additional 3K TCP modules are loaded persistently at boot.

Fresh servers without a connected router keep the remote WireGuard route helper idle. TCP congestion changes queue service restarts after validation so slow tunnel stops cannot exceed the router API timeout. Glorytun TCP uses a minimum 65536-byte buffer and a five-second stop timeout.

## Remote WireGuard access

The generated /root/wireguard-client.conf starts with AllowedIPs = 10.255.0.0/16. Once OMR is paired, the VPS permits only the router GUI on its tunnel IPv4 address, TCP ports 80 and 443. Access to LAN devices is denied on the VPS, even if a client selects AllowedIPs = 0.0.0.0/0.

For IPv4 Internet through the VPS, change the client's AllowedIPs to 0.0.0.0/0 and use a public DNS server, for example 1.1.1.1. The VPS forwards and NATs this traffic to its WAN public IPv4 address. This does not enable OMR LAN access.

Run as root on the VPS to control the persistent LAN permission:

    wg-remote-lan-route --lan-access status
    wg-remote-lan-route --lan-access allow
    wg-remote-lan-route --lan-access deny

The state file is /etc/openmptcprouter-vps-admin/wg-remote-lan-access.enabled (mode 0600). An absent file means deny. The helper refreshes the router GUI/LAN addresses from the locally synchronized OMR configuration and uses policy table 24612 for LAN routes. For a split tunnel, add the desired OMR LAN subnet to the client's AllowedIPs as well; a full IPv4 tunnel already covers it, but the VPS gate must still be enabled. Disabling the permission leaves GUI access and public Internet available.
