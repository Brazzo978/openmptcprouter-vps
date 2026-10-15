# Native MQVPN LAN route candidate for VPS

The patch in this directory is an exact copy of the router feed's
`mqvpn/patches/010-omr-native-lan-routes.patch`. Its SHA-256 is
`416aa9768b6a774b3edb7ab7e03043fdf0fb79118d3a1bcbe1510ce7a1feae50`.
It applies to MQVPN 0.16.2 source commit
`ee78205d3db491ca7727b974bda0c91ae1523236`. The new control API
registers a private LAN prefix to one authenticated user; the VPS `/lan`
API and the route timer replay that registration independently of the
WireGuard LAN checkbox. Ordinary OMR public-port forwarding with DNAT to
the router's MQVPN address and router-side DNAT to a LAN host already
works on stock MQVPN. The native patch adds direct dispatch when packets
reach the server with a LAN destination address.

## Build and stage

Use the original OpenWrt build host's cached MQVPN source dependency tree
for XQUIC and BoringSSL. The original cached archive `mqvpn-0.16.2.tar.zst` includes both dependency trees; its SHA-256 is
`3864a72f92d0d1c567c2dc21030121e195883a4415aea86a48323b90e8d8d680`.
The archive was preserved on the build host and locally. Individual dependency
Git metadata was unavailable. Preserve/mirror this exact archive with the final
source assets and record CMake/toolchain versions before producing a release. Start with a clean checkout at the base
commit. In these commands `$source` is that checkout, `$repo` is this
VPS repository, `$xquic_build` and `$boringssl_build` are the original
cached build directories, and `$stock_deb` is the frozen upstream
`mqvpn_0.16.2-1_amd64.deb`:

```sh
test "$(git -C "$source" rev-parse HEAD)" = ee78205d3db491ca7727b974bda0c91ae1523236
git -C "$source" diff --quiet
sha256sum "$repo/patches/mqvpn/010-omr-native-lan-routes.patch"
git -C "$source" apply --check "$repo/patches/mqvpn/010-omr-native-lan-routes.patch"
git -C "$source" apply "$repo/patches/mqvpn/010-omr-native-lan-routes.patch"
cmake -S "$source" -B "$source/build-3k" -DCMAKE_BUILD_TYPE=Release \
  -DXQUIC_BUILD_DIR="$xquic_build" -DBORINGSSL_BUILD_DIR="$boringssl_build" \
  -DBUILD_TESTING=ON
cmake --build "$source/build-3k" -j2
ctest --test-dir "$source/build-3k" --output-on-failure
sha256sum "$source/build-3k/mqvpn"
python3 "$repo/frozen/repack-mqvpn-native.py" \
  --stock-deb "$stock_deb" \
  --built-executable "$source/build-3k/mqvpn" \
  --built-sha256 "<digest reported by sha256sum>" \
  --output "$candidate_dir/mqvpn_0.16.2-3k1_amd64.deb"
```

The repacker verifies the patch hash, the stock DEB's frozen SHA-256
(`d7627312d75e47d0930a7a74ace4ab72d10e44d77a50fce725f877761fc1db81`),
the independently recorded ELF executable hash, package identity and
unchanged dependency field. It replaces only `/usr/bin/mqvpn`, changes
the package version to `0.16.2-3k1`, and writes a sidecar JSON with the
candidate DEB hash and provenance. It refuses to overwrite outputs.
The sibling `libmqvpn0_0.16.2-1_amd64.deb` remains upstream stock.

This is a candidate build recipe, not an installer. Before final release,
verify the generated DEB contents and metadata, test a clean VPS install
and reboot plus router connectivity, double-DNAT port forwarding,
direct LAN routing and WireGuard checkbox allow/deny, and then add the
candidate as its **own verified asset** to the final frozen bundle and
lock. The currently published `frozen/omr-amd64.lock.json` still points
to the stock MQVPN DEB and must not be represented as containing this
patch.

The candidate repack was exercised on the Linux build host on 2026-10-15.
It produced a 1451624-byte DEB with SHA-256
`526d33a9201f2cfc3372917d7b9298c579e068609465a27bb0a469019f4fd1e0`
from the server ELF SHA-256
`5d090b29ce51691ce190372582ab8a316abc6014a80da01dda503920de218a93`.
This confirms packaging, not a clean installation of this candidate.
