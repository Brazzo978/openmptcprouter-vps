# 3K VPS kernel source lock

`source-lock.json` pins Ysurac/linux commit
`1db16030b9d4f56787cd01d52adeeaa650ea5994`, XanMod patch catalog
commit `6e34b2e14adc928990d23aa57d7b751116175374`, stable 6.18.41,
the official stock OMR image/config, and the expected 3K release. `SHA256SUMS`
verifies every vendored patch, selection list, and config. The source sequence
is 36 XanMod patches, stable 6.18.41, OMR MPTCP BPF, OMR BBRv3, then 3K custom
CC, the private-symbol namespace patch, the module metadata patch, and the BBR1 kfunc callback fix. The three known upstream XanMod skips are frozen in `xanmod-apply.tsv`;
the script refuses any other skip. The stable patch requires GNU patch fuzz 1
in `block/blk-wbt.c`. This recreates the reviewed stack, not a claim of
bit-identical stock July 2026 binaries.

Run `./build-kernel.sh prepare` to fetch the pinned commit, verify the
checksums, apply patches, and compare the generated config byte-for-byte with
the reviewed config. Run `./build-kernel.sh build` in a fresh workdir to
compile image and headers into `cc/packages/`. It does not install host
packages or change host kernel, modules, sysctls, firewall, or routes.
`check-bbr-btf.py` needs `nm`, `readelf`, and `bpftool` in the offline build environment. It checks all nine stock BBRv3 kfunc IDs, all eight BBR1 kfunc IDs, and BTF sections for all 15 custom modules before the built .deb files are accepted. `DPKG_FLAGS=-d` bypasses a packaging dependency check for libdw-dev, but
does not supply missing compiler dependencies. `OMR_3K_BUILD_JOBS` controls
the make job count.

Use separate empty directories for source review and compilation, for example from the VPS repository root:

```sh
./cc/build-kernel.sh prepare /tmp/omr-3k-source-review
OMR_3K_BUILD_JOBS=12 ./cc/build-kernel.sh build /tmp/omr-3k-kernel-build
```

The script preserves existing source trees; a tree already patched by prepare cannot be used as a fresh input to build. Rebuilt binaries can differ with toolchain and build metadata. The committed binary lock accepts the reviewed release artifacts; a new local build requires an intentional lock update after verification.

`python3 verify-3k-kernel.py packages/image.deb packages/headers.deb`
requires committed `package-lock.json` SHA256 values for both .deb files, then checks the pair, all 15 custom CC config flags, the BBRv3 default config, and the actual custom .ko files in the image. The standalone top-level
`run-vps-3k.sh prepare` packages the vendored API under `admin/`.
Its `install` mode uses the verified kernel pair and makes target-system
changes; it is reserved for the approved deployment.

The live build host was inspected read-only and currently advertises only
`reno bbr`. Isolated QEMU boot of the exact locked VPS image confirmed
BBRv3 as default, all 15 custom modules loaded, 18/18 real loopback TCP
transfers with iperf3, and no kernel BUG/Oops/panic. Production VPS boot,
VAR sysfs behavior, VPS API capability/readback, and WAN operation still
require validation during deployment.


The image and headers .deb files are binary artifacts and are not tracked in Git. Their exact SHA256, size, package name, version, and versioned HTTPS download URL are recorded in committed `package-lock.json`. `fetch-packages.py` downloads only missing files, verifies them before acceptance, and rejects a changed local file. The installer repeats the package check before any system changes. The API package has its own fixed SHA256 gate in the installer. A new kernel build requires review and an intentional lock update before deployment.

The BBR1 kfunc patch registers the actual bbr1_bbr_tso_segs callback. The older bbr1_bbr_min_tso_segs helper is inlined on x64v3, which left a zero BTF ID and caused insmod tcp_bbr1.ko to return EINVAL in isolated boot QA.
