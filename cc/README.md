# 3K VPS kernel source lock

`source-lock.json` pins Ysurac/linux commit
`1db16030b9d4f56787cd01d52adeeaa650ea5994`, XanMod patch catalog
commit `6e34b2e14adc928990d23aa57d7b751116175374`, stable 6.18.41,
the official stock OMR image/config, and the expected 3K release. `SHA256SUMS`
verifies every vendored patch, selection list, and config. The source sequence
is 36 XanMod patches, stable 6.18.41, OMR MPTCP BPF, OMR BBRv3, then 3K custom
CC. The three known upstream XanMod skips are frozen in `xanmod-apply.tsv`;
the script refuses any other skip. The stable patch requires GNU patch fuzz 1
in `block/blk-wbt.c`. This recreates the reviewed stack, not a claim of
bit-identical stock July 2026 binaries.

Run `./build-kernel.sh prepare` to fetch the pinned commit, verify the
checksums, apply patches, and compare the generated config byte-for-byte with
the reviewed config. Run `./build-kernel.sh build` in a fresh workdir to
compile image and headers into `cc/packages/`. It does not install host
packages or change host kernel, modules, sysctls, firewall, or routes.
`DPKG_FLAGS=-d` bypasses a packaging dependency check for libdw-dev, but
does not supply missing compiler dependencies. `OMR_3K_BUILD_JOBS` controls
the make job count.

`python3 verify-3k-kernel.py packages/image.deb packages/headers.deb`
checks the pair, all 15 custom CC config flags, and the actual custom .ko files in the image. The standalone top-level
`run-vps-3k.sh prepare` packages the vendored API under `admin/`.
Its `install` mode uses the verified kernel pair and makes target-system
changes; it is reserved for the approved deployment.

The live build host was inspected read-only and currently advertises only
`reno bbr`. Custom CC and VAR sysfs runtime behavior remain untested
until deployment and reboot. Then verify the active release, available CC,
VAR sysfs parameters, and VPS API capability/readback before selecting one.
