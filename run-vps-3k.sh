#!/bin/sh
# Prepare the local reviewed server package; install only when explicitly asked.
set -eu
cd "$(dirname "$0")"
mode=${1:-prepare}
case "$mode" in prepare|install) ;; *) echo "usage: $0 [prepare|install]" >&2; exit 2 ;; esac
if [ -f ./admin/build-3k-deb.py ]; then
    admin_builder=./admin/build-3k-deb.py
elif [ -f ../admin/build-3k-deb.py ]; then
    admin_builder=../admin/build-3k-deb.py
else
    echo "Missing reviewed 3K VPS API source" >&2
    exit 1
fi
python3 "$admin_builder" --output "$PWD/debian"
export OMR_ADMIN_BINARY_VERSION=0.18+20261013-3k1
export OMR_ADMIN_LOCAL_DEB="$PWD/debian/omr-vps-admin_${OMR_ADMIN_BINARY_VERSION}_all.deb"
export LOCALFILES=yes
export SOURCES=no
export WIREGUARD=yes
[ -f "$OMR_ADMIN_LOCAL_DEB" ] || exit 1
sh -n ./debian9-x86_64.sh
if [ "$mode" = prepare ]; then
    echo "3K VPS API package prepared. Kernel pair must be built into cc/packages before install."
    exit 0
fi
[ -f ./frozen/omr-amd64.lock.json ] && [ -f ./frozen/freeze.py ] || {
    echo "Missing reviewed frozen VPS package lock" >&2
    exit 1
}
python3 ./frozen/freeze.py fetch
export OMR_3K_KERNEL_IMAGE_DEB="$PWD/cc/packages/image.deb"
export OMR_3K_KERNEL_HEADERS_DEB="$PWD/cc/packages/headers.deb"
[ -f "$OMR_3K_KERNEL_IMAGE_DEB" ] && [ -f "$OMR_3K_KERNEL_HEADERS_DEB" ] || {
    echo "Missing offline 3K VPS kernel pair in $PWD/cc/packages" >&2
    exit 1
}
python3 ./cc/verify-3k-kernel.py "$OMR_3K_KERNEL_IMAGE_DEB" "$OMR_3K_KERNEL_HEADERS_DEB"
export OMR_3K_FROZEN=yes
exec ./debian9-x86_64.sh
