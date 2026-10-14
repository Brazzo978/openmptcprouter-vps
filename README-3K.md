# OpenMPTCProuter VPS 0.1160-3K

Release 0.1160-3K pairs with OpenMPTCProuter v0.64.2-3K-rc1. The VPS base is official stable 0.1081 at 44958fbac2c1c06c2759aa699b37cc537120fa13. Existing older 3K branches remain separate.

The VPS kernel is 6.18.41-20261013.x64v3-omr-3k, derived from Ysurac/linux commit 1db16030b9d4f56787cd01d52adeeaa650ea5994 and the official x64v3 configuration. The vendored stack includes the selected XanMod patches, stable 6.18.41, OMR MPTCP/BBRv3 and 15 custom TCP controls. BBRv3, named bbr, is the default. All source inputs and binary image/headers are locked under cc/.

The API source and deterministic Debian builder are included in admin/. The port adds verified congestion selection with rollback, NanBBR VAR 1..100, effective XRay TCP reverse forwarding, and a WireGuard remote client path through the VPS to the OMR GUI.

The 21 OMR packages have fixed version, architecture, size, SHA256 and versioned HTTPS mirror URL in frozen/omr-amd64.lock.json. Original upstream URLs remain recorded. The installer uses verified local assets and refuses unverified OMR fallbacks. API /update and omr-update refuse upstream updates on marked frozen installations.

## Preparation and use

From this repository, run ./run-vps-3k.sh prepare to build the API package without installation. Run python3 ./frozen/freeze.py fetch to fetch and verify locked OMR packages, or python3 ./cc/fetch-packages.py to fetch and verify the reviewed kernel pair.

The install mode fetches missing locked kernel files, verifies the pair and API before installer execution, and is intended for an explicit deployment. No installation was executed during development.

For independent source review or compilation, use separate empty workdirs:
./cc/build-kernel.sh prepare /tmp/omr-3k-source-review
OMR_3K_BUILD_JOBS=12 ./cc/build-kernel.sh build /tmp/omr-3k-kernel-build

The binary lock accepts the published reviewed artifacts. Local rebuilt binaries can differ with compiler and build metadata and require an intentional lock update after validation. Generated .deb files are excluded from Git.

## Validation and limits

The complete API suite passed: 980 passed, 9 skipped. Exact source-stack replay, patch checksums, binary package contents, BBRv3/BBR1 BTF IDs and corrupt-file rejection were verified. All 21 OMR mirror assets and the final kernel pair were downloaded via HTTPS and matched their locked hashes.

The exact final VPS image was booted in isolated QEMU: BBRv3 default, 15/15 custom modules loaded, 18/18 real TCP loopback transfers passed, no BUG/Oops/panic. All three native NanBBR VAR module parameters accepted and read back 1, 25, 50, 80 and 100, rejected 0 and 101 without changing the previous value, and restored 50. See validation/vps-kernel-boot.json. XRay reverse forwarding also passed a real TLS loopback test.

Installation on a real VPS, WAN behavior, VAR sysfs/API behavior on the deployed system and the complete remote WireGuard GUI path remain deployment checks. This is a frozen base for testing; production systems were not installed or rebooted.

The supported frozen installer path is Debian13 amd64 with local files and SOURCES=no. OMR inputs are fixed while normal OS security updates remain separate. The installer retains legacy Bullseye runtime dependencies such as libmbedcrypto3/libpcre3. Server MLVPN/OpenVPN bonding remain for older clients; their removal is client-only.

## Release bundle

Download openmptcprouter-vps-0.1160-3K.tar.gz and SHA256SUMS-vps-0.1160-3K from the GitHub release. The archive includes the exact kernel/headers, local API package, all 21 locked OMR packages and helper files.

On Debian 13 amd64 with an x86-64-v3 capable CPU, verify the archive, extract it, and enter the extracted directory:

    sha256sum --ignore-missing -c SHA256SUMS-vps-0.1160-3K
    tar -xzf openmptcprouter-vps-0.1160-3K.tar.gz
    cd openmptcprouter-vps-0.1160-3K
    ./run-vps-3k.sh prepare

Preparation rebuilds only the local API package and does not install services. For an intentional VPS deployment, run the following as root:

    ./run-vps-3k.sh install

The installer changes networking/services and installs the bundled kernel. A reboot is required to use the new kernel. Debian APT access is still required for OS dependencies; only the OMR payloads are bundled and locked. Run the wrapper rather than downloading or piping the legacy upstream installer. This prerelease still requires real multi-WAN, complete remote WireGuard GUI and full VPS installation validation.
