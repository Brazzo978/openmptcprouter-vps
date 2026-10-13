# OpenMPTCProuter VPS 3K frozen base

This branch pairs with the OpenMPTCProuter v0.64.2-3K router build. The VPS base is official stable 0.1081 at 44958fbac2c1c06c2759aa699b37cc537120fa13. Existing older 3K branches remain separate.

The server kernel starts from Ysurac/linux commit 1db16030b9d4f56787cd01d52adeeaa650ea5994 and the official 6.18.41 x64v3 configuration. The vendored stack includes the selected XanMod patches, stable 6.18.41, OMR MPTCP BPF schedulers, BBRv3 and the 15 custom 3K TCP controls. The output release is 6.18.41-20261013.x64v3-omr-3k. See cc/source-lock.json and cc/SHA256SUMS.

OMR binary inputs have fixed URL, version, architecture, size and SHA-256 in frozen/omr-amd64.lock.json. Fetching rejects replaced or corrupted files. The frozen installer uses a local APT repository and rejects unverified OMR download fallbacks. API /update and omr-update refuse upstream updates on installations marked /etc/omr-vps-3k-frozen.json.

The reviewed API source and its deterministic Debian builder are included in admin/. Features include transactional congestion-control selection and NanBBR VAR 1..100, effective XRay TCP reverse forwarding, and a WireGuard remote client path through the VPS to the OMR router GUI.

## Preparation

Run ./run-vps-3k.sh prepare to build the API package without installation.
Run ./cc/build-kernel.sh prepare to verify and prepare the exact kernel source.
Run ./cc/build-kernel.sh build to compile the image and headers offline.
Run python3 ./frozen/freeze.py fetch to materialize and verify frozen OMR packages.

Generated packages are excluded from Git. The install mode requires the verified 3K image and headers pair and locked OMR assets. Preparation never installs a kernel, restarts production services or changes live routing.

## Validation and remaining checks

The complete API test suite passed: 980 passed, 9 skipped. The frozen OMR assets and source-stack replay were verified. The router firmware compiled and booted in an isolated VM; advanced diagnostics and NanBBR VAR were inspected in LuCI. XRay reverse forwarding passed a real TLS loopback test.

Kernel package compilation, installation in an isolated VPS, real multi-WAN behavior and the complete WireGuard remote-GUI path must be recorded before treating this as a production release. This branch is a reviewable frozen source base.

The lock freezes OMR inputs, not all Debian packages. Normal OS security updates remain separate. The existing installer still uses Debian Bullseye for legacy runtime dependencies such as libmbedcrypto3/libpcre3; a Debian13-only dependency closure needs separate work.
