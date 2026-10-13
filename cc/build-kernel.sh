#!/usr/bin/env bash
# Recreate the reviewed OMR/XanMod/3K VPS kernel source. No host package install.
set -euo pipefail
mode="${1:-prepare}"
case "$mode" in prepare|build) ;; *) echo "usage: $0 [prepare|build] [workdir]" >&2; exit 2 ;; esac
cd "$(dirname "$0")"
cc_dir="$PWD"
workdir="${2:-$cc_dir/work}"
mkdir -p "$workdir"
workdir="$(realpath "$workdir")"
sha256sum -c SHA256SUMS
source_commit=1db16030b9d4f56787cd01d52adeeaa650ea5994
release=6.18.41-20261013.x64v3-omr-3k
src="$workdir/omr-linux"
if [ ! -d "$src/.git" ]; then
    mkdir -p "$src"
    git -C "$src" init -q
    git -C "$src" remote add origin https://github.com/Ysurac/linux.git
    git -C "$src" fetch --depth=1 origin "$source_commit"
    git -C "$src" checkout -q --detach "$source_commit"
else
    actual="$(git -C "$src" rev-parse HEAD)"
    [ "$actual" = "$source_commit" ] || {
        echo "Source checkout is not at pinned OMR commit: $actual" >&2
        exit 1
    }
    [ -z "$(git -C "$src" status --porcelain)" ] || {
        echo "Source checkout has changes; use an empty workdir" >&2
        exit 1
    }
fi
[ "$(git -C "$src" rev-parse HEAD)" = "$source_commit" ]
export GIT_COMMITTER_NAME="OMR 3K offline builder"
export GIT_COMMITTER_EMAIL="offline-builder@example.invalid"
applied=0
skipped=0
while IFS="$(printf '\t')" read -r decision patch_name; do
    [ -n "$decision" ] || continue
    patch_file="$cc_dir/patches/xanmod/$patch_name"
    [ -f "$patch_file" ] || { echo "Missing $patch_file" >&2; exit 1; }
    case "$decision:$patch_name" in
        applied:*)
            git -C "$src" am --3way "$patch_file"
            applied=$((applied + 1))
            ;;
        skipped:net/tcp/bbr3/0001-tcp_bbr-v3-update-TCP-bbr-congestion-control-module-.patch|skipped:userns/0001-sysctl-add-sysctl-to-disallow-unprivileged-CLONE_NEW.patch|skipped:xanmod/0007-XANMOD-sched-Add-yield_type-sysctl-to-reduce-or-disa.patch)
            skipped=$((skipped + 1))
            ;;
        *) echo "Unexpected XanMod patch decision: $decision $patch_name" >&2; exit 1 ;;
    esac
done < "$cc_dir/patches/xanmod-apply.tsv"
[ "$applied" -eq 36 ] && [ "$skipped" -eq 3 ] || {
    echo "Wrong XanMod selection count: $applied applied, $skipped skipped" >&2
    exit 1
}
cd "$src"
xz -dc "$cc_dir/patches/stable-6.18.41.patch.xz" | patch --batch --fuzz=1 -p1
grep -q '^SUBLEVEL = 41$' Makefile
patch --batch --forward -p1 < "$cc_dir/patches/omr/mptcp-bpf-scheduler.patch"
# The OMR patch carries sequential edits to these files and GNU patch leaves backups.
rm -f net/mptcp/protocol.c.orig net/mptcp/protocol.h.orig
patch --batch --forward -p1 < "$cc_dir/patches/omr/tcp-bbr-v3.patch"
grep -Eq '^#define BBR_VERSION[[:space:]]+3$' net/ipv4/tcp_bbr.c
patch --batch --forward -p1 < "$cc_dir/patches/3k-tcp-custom-cc.patch"
grep -Eq '^#define ICSK_CA_PRIV_SIZE[[:space:]]+\(216\)$' include/net/inet_connection_sock.h
if find . -name '*.rej' -print -quit | grep -q .; then
    echo "Patch rejects found" >&2
    exit 1
fi
git diff --check -- include/net/inet_connection_sock.h net/ipv4
cp "$cc_dir/config/omr-6.18.41-x64v3.config" .config
for name in BBR1 BBR2 NANQINLANG \
    NANBBR1_LIGHT NANBBR1_DEF NANBBR1_AGGR NANBBR1_VAR \
    NANBBR2_LIGHT NANBBR2_DEF NANBBR2_AGGR NANBBR2_VAR \
    NANBBR3_LIGHT NANBBR3_DEF NANBBR3_AGGR NANBBR3_VAR; do
    scripts/config --module "TCP_CONG_$name"
done
scripts/config --set-str LOCALVERSION -20261013.x64v3-omr-3k --disable LOCALVERSION_AUTO
make olddefconfig
[ "$(make -s kernelrelease)" = "$release" ] || {
    echo "Kernel release changed unexpectedly" >&2
    exit 1
}
cmp .config "$cc_dir/config/3k-6.18.41-x64v3.config" || {
    echo "Generated config differs from reviewed config" >&2
    exit 1
}
if [ "$mode" = prepare ]; then
    echo "Reviewed source ready in $src, release $release"
    exit 0
fi
# No apt install or host module loading. Debian package dependency checks can
# require libdw-dev even when BTF compilation succeeds with the available tools.
DPKG_FLAGS=-d make -j"${OMR_3K_BUILD_JOBS:-4}" bindeb-pkg
shopt -s nullglob
images=("$workdir"/linux-image-"$release"_*.deb)
headers=("$workdir"/linux-headers-"$release"_*.deb)
[ "${#images[@]}" -eq 1 ] && [ "${#headers[@]}" -eq 1 ] || {
    echo "Expected exactly one image and headers package" >&2
    exit 1
}
mkdir -p "$cc_dir/packages"
cp "${images[0]}" "$cc_dir/packages/image.deb"
cp "${headers[0]}" "$cc_dir/packages/headers.deb"
python3 "$cc_dir/verify-3k-kernel.py" "$cc_dir/packages/image.deb" "$cc_dir/packages/headers.deb"
sha256sum "$cc_dir/packages/image.deb" "$cc_dir/packages/headers.deb"
