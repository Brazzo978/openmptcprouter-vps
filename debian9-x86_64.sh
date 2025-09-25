#!/bin/sh
#
# Copyright (C) 2018-2021 Ycarus (Yannick Chabanois) <ycarus@zugaina.org> for OpenMPTCProuter
#
# This is free software, licensed under the GNU General Public License v3 or later.
# See /LICENSE for more information.
#

UPSTREAM=${UPSTREAM:-no}
SHADOWSOCKS_PASS=${SHADOWSOCKS_PASS:-$(head -c 32 /dev/urandom | base64 -w0)}
GLORYTUN_PASS=${GLORYTUN_PASS:-$(od -vN "32" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
DSVPN_PASS=${DSVPN_PASS:-$(od -vN "32" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
#NBCPU=${NBCPU:-$(nproc --all | tr -d "\n")}
NBCPU=${NBCPU:-$(grep -c '^processor' /proc/cpuinfo | tr -d "\n")}
OBFS=${OBFS:-yes}
V2RAY_PLUGIN=${V2RAY_PLUGIN:-yes}
V2RAY=${V2RAY:-yes}
V2RAY_UUID=${V2RAY_UUID:-$(cat /proc/sys/kernel/random/uuid | tr -d "\n")}
UPDATE_OS=${UPDATE_OS:-yes}
UPDATE=${UPDATE:-yes}
TLS=${TLS:-yes}
OMR_ADMIN=${OMR_ADMIN:-yes}
OMR_ADMIN_PASS=${OMR_ADMIN_PASS:-$(od -vN "32" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
OMR_ADMIN_PASS_ADMIN=${OMR_ADMIN_PASS_ADMIN:-$(od -vN "32" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
MLVPN=${MLVPN:-yes}
MLVPN_PASS=${MLVPN_PASS:-$(head -c 32 /dev/urandom | base64 -w0)}
UBOND=${UBOND:-no}
UBOND_PASS=${UBOND_PASS:-$(head -c 32 /dev/urandom | base64 -w0)}
OPENVPN=${OPENVPN:-yes}
DSVPN=${DSVPN:-yes}
WIREGUARD=${WIREGUARD:-yes}
SOURCES=${SOURCES:-no}
if [ "$UPSTREAM" = "yes" ]; then
	SOURCES="yes"
fi
NOINTERNET=${NOINTERNET:-no}
REINSTALL=${REINSTALL:-yes}
SPEEDTEST=${SPEEDTEST:-yes}
LOCALFILES=${LOCALFILES:-no}
OMR_STATIC_DEB_BASE=${OMR_STATIC_DEB_BASE:-https://github.com/Brazzo978/openmptcprouter-vps/raw/refs/heads/omr-vps-0.1028-def/Pack}
if [ -z "${USE_OMR_REPO+x}" ]; then
        if [ -n "$OMR_STATIC_DEB_BASE" ]; then
                USE_OMR_REPO=no
        else
                USE_OMR_REPO=yes
        fi
fi
OMR_REQUIRE_STATIC=${OMR_REQUIRE_STATIC:-no}
INTERFACE=${INTERFACE:-$(ip -o -4 route show to default | grep -m 1 -Po '(?<=dev )(\S+)' | tr -d "\n")}
KERNEL_VERSION="5.4.207"
KERNEL_PACKAGE_VERSION="1.22"
KERNEL_RELEASE="${KERNEL_VERSION}-mptcp_${KERNEL_PACKAGE_VERSION}"
if [ "$UPSTREAM" = "yes" ]; then
	KERNEL_VERSION="5.15.57"
	KERNEL_PACKAGE_VERSION="1.6"
	KERNEL_RELEASE="${KERNEL_VERSION}-mptcp_${KERNEL_VERSION}-${KERNEL_PACKAGE_VERSION}"
fi
GLORYTUN_UDP_VERSION="32267e86a6da05b285bb3bf2b136c105dc0af4bb"
GLORYTUN_UDP_BINARY_VERSION="0.3.4-5"
GLORYTUN_TCP_BINARY_VERSION="0.0.35-3"
#MLVPN_VERSION="8f9720978b28c1954f9f229525333547283316d2"
MLVPN_VERSION="8aa1b16d843ea68734e2520e39a34cb7f3d61b2b"
MLVPN_BINARY_VERSION="3.0.0+20211028.git.ddafba3"
UBOND_VERSION="f9fb6aa0a65e8e20950977bda970c90012f830d7"
OBFS_VERSION="486bebd9208539058e57e23a12f23103016e09b4"
OBFS_BINARY_VERSION="0.0.5-1"
OMR_ADMIN_VERSION="4f8dc4f997c6c95971beea9d52512ed91c77479b"
OMR_ADMIN_BINARY_VERSION="0.3+20220827"
DSVPN_VERSION="3b99d2ef6c02b2ef68b5784bec8adfdd55b29b1a"
DSVPN_BINARY_VERSION="0.1.4-2"
V2RAY_VERSION="4.43.0"
V2RAY_PLUGIN_VERSION="4.43.0"
EASYRSA_VERSION="3.0.6"
SHADOWSOCKS_VERSION="7407b214f335f0e2068a8622ef3674d868218e17"
if [ "$UPSTREAM" = "yes" ]; then
	SHADOWSOCKS_VERSION="410950d87d8cdf8502d8f59a79dc0ff4c7677543"
fi
IPROUTE2_VERSION="29da83f89f6e1fe528c59131a01f5d43bcd0a000"
SHADOWSOCKS_BINARY_VERSION="3.3.5-3"
LIBJSON_C3_VERSION="0.12.1+ds-2"
LIBSODIUM18_VERSION="1.0.13-1"
LIBUV1_VERSION="1.34.2-1"
PYTHON3_FLASK_VERSION="1.0.2"
PYTHON3_FLASK_JWT_SIMPLE_VERSION="0.0.3"
PYTHON3_ITSDANGEROUS_VERSION="1.1.0"
PYTHON3_JINJA2_VERSION="2.10"
PYTHON3_MARKUPSAFE_VERSION="1.1.1"
PYTHON3_PYJWT_VERSION="1.7.1"
PYTHON3_UVICORN_VERSION="0.11.5-1"
PYTHON3_UVLOOP_VERSION="0.14.0+ds1-1"
PYTHON3_WATCHGOD_VERSION="0.6-1"
PYTHON3_WERKZEUG_VERSION="0.15.1"
OMR_LIBIPERF0_BINARY_VERSION="3.7-2"
OMR_LIBSHADOWSOCKS_LIBEV2_BINARY_VERSION="3.3.5-3"
OMR_LIBSHADOWSOCKS_LIBEV_DEV_BINARY_VERSION="3.3.5-3"
OPENVPN_BINARY_VERSION="2.6.14-1"
DEFAULT_USER="openmptcprouter"
VPS_DOMAIN=${VPS_DOMAIN:-$(wget -4 -qO- -T 2 http://hostname.openmptcprouter.com)}
VPSPATH="server"
VPS_PUBLIC_IP=${VPS_PUBLIC_IP:-$(wget -4 -qO- -T 2 http://ip.openmptcprouter.com)}
VPSURL="https://www.openmptcprouter.com/"
REPO="repo.openmptcprouter.com"
CHINA=${CHINA:-no}

OMR_VERSION="0.1028"

DIR=$( pwd )
#"
find_latest_pack_file() {
    prefix="$1"
    suffix="$2"
    best=""
    best_version=""
    if [ -d "${DIR}/Pack" ]; then
        for path in "${DIR}/Pack/"*; do
            [ -f "$path" ] || continue
            file=${path##*/}
            case "$file" in
                ${prefix}*${suffix})
                    version=${file#${prefix}}
                    version=${version%${suffix}}
                    if [ -z "$best" ] || dpkg --compare-versions "$version" gt "$best_version"; then
                        best="$file"
                        best_version="$version"
                    fi
                ;;
            esac
        done
    fi
    printf "%s" "$best"
}

select_static_deb_file() {
    default="$1"
    prefix="$2"
    suffix="$3"
    if [ -n "$default" ] && [ -f "${DIR}/Pack/${default}" ]; then
        printf "%s" "$default"
        return
    fi
    alt=$(find_latest_pack_file "$prefix" "$suffix")
    if [ -n "$alt" ]; then
        printf "%s" "$alt"
        return
    fi
    printf "%s" "$default"
}

get_static_deb_url() {
    base="$1"
    file="$2"
    if [ -n "$base" ] && [ -n "$file" ]; then
        printf "%s/%s" "${base%/}" "$file"
    fi
}

LIBSHADOWSOCKS_LIBEV2_VERSION=${LIBSHADOWSOCKS_LIBEV2_VERSION:-$OMR_LIBSHADOWSOCKS_LIBEV2_BINARY_VERSION}
LIBSHADOWSOCKS_LIBEV2_DEB_FILE=${LIBSHADOWSOCKS_LIBEV2_DEB_FILE:-$(select_static_deb_file "libshadowsocks-libev2_${LIBSHADOWSOCKS_LIBEV2_VERSION}_amd64.deb" "libshadowsocks-libev2_" "_amd64.deb")}
LIBSHADOWSOCKS_LIBEV2_DEB_URL=${LIBSHADOWSOCKS_LIBEV2_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$LIBSHADOWSOCKS_LIBEV2_DEB_FILE")}

install_omr_package() {
    pkg="$1"
    version="$2"
    filename="$3"
    url="$4"
    shift 4
    dest=""
    if [ "$LOCALFILES" = "yes" ] && [ -n "$filename" ] && [ -f "${DIR}/Pack/${filename}" ]; then
        dest="/tmp/${filename}"
        cp "${DIR}/Pack/${filename}" "$dest"
    elif [ -n "$url" ]; then
        if [ -n "$filename" ]; then
            dest="/tmp/${filename}"
        else
            dest="/tmp/$(basename "$url")"
        fi
        wget -O "$dest" "$url"
    fi
    if [ -n "$dest" ]; then
        set -- "$@"
        dpkg_opts=""
        while [ $# -gt 0 ]; do
            case "$1" in
                -o)
                    shift
                    opt="$1"
                    case "$opt" in
                        Dpkg::Options::=--*)
                            dpkg_opts="$dpkg_opts --${opt#Dpkg::Options::=--}"
                            ;;
                    esac
                    ;;
                *)
                    ;;
            esac
            shift
        done
        if ! dpkg $dpkg_opts -i "$dest"; then
            rc=$?
        else
            rc=0
        fi
        rm -f "$dest"
        return $rc
    fi
    if [ "$OMR_REQUIRE_STATIC" = "yes" ] && [ "$USE_OMR_REPO" != "yes" ]; then
        echo "Static package $pkg requested but no static file or URL provided" >&2
        return 1
    fi
    if [ -n "$version" ]; then
        apt-get -y "$@" install "${pkg}=${version}"
    else
        apt-get -y "$@" install "${pkg}"
    fi
}

LINUX_IMAGE_DEB_FILE=${LINUX_IMAGE_DEB_FILE:-linux-image-${KERNEL_RELEASE}_amd64.deb}
LINUX_IMAGE_DEB_URL=${LINUX_IMAGE_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$LINUX_IMAGE_DEB_FILE")}
LINUX_HEADERS_DEB_FILE=${LINUX_HEADERS_DEB_FILE:-linux-headers-${KERNEL_RELEASE}_amd64.deb}
LINUX_HEADERS_DEB_URL=${LINUX_HEADERS_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$LINUX_HEADERS_DEB_FILE")}

LIBJSON_C3_DEB_FILE=${LIBJSON_C3_DEB_FILE:-$(select_static_deb_file "libjson-c3_${LIBJSON_C3_VERSION}_amd64.deb" "libjson-c3_" "_amd64.deb")}
LIBJSON_C3_DEB_URL=${LIBJSON_C3_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$LIBJSON_C3_DEB_FILE")}
LIBSODIUM18_DEB_FILE=${LIBSODIUM18_DEB_FILE:-$(select_static_deb_file "libsodium18_${LIBSODIUM18_VERSION}_amd64.deb" "libsodium18_" "_amd64.deb")}
LIBSODIUM18_DEB_URL=${LIBSODIUM18_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$LIBSODIUM18_DEB_FILE")}
LIBUV1_DEB_FILE=${LIBUV1_DEB_FILE:-$(select_static_deb_file "libuv1_${LIBUV1_VERSION}_amd64.deb" "libuv1_" "_amd64.deb")}
LIBUV1_DEB_URL=${LIBUV1_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$LIBUV1_DEB_FILE")}
TRACEBOX_DEB_FILE=${TRACEBOX_DEB_FILE:-tracebox_0.4.4_amd64.deb}
TRACEBOX_DEB_URL=${TRACEBOX_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$TRACEBOX_DEB_FILE")}
OMR_IPERF3_DEB_FILE=${OMR_IPERF3_DEB_FILE:-omr-iperf3_3.7-2_amd64.deb}
OMR_IPERF3_DEB_URL=${OMR_IPERF3_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_IPERF3_DEB_FILE")}
OMR_LIBIPERF0_DEB_FILE=${OMR_LIBIPERF0_DEB_FILE:-$(select_static_deb_file "omr-libiperf0_${OMR_LIBIPERF0_BINARY_VERSION}_amd64.deb" "omr-libiperf0_" "_amd64.deb")}
OMR_LIBIPERF0_DEB_URL=${OMR_LIBIPERF0_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_LIBIPERF0_DEB_FILE")}
OMR_SHADOWSOCKS_DEB_FILE=${OMR_SHADOWSOCKS_DEB_FILE:-omr-shadowsocks-libev_${SHADOWSOCKS_BINARY_VERSION}_amd64.deb}
OMR_SHADOWSOCKS_DEB_URL=${OMR_SHADOWSOCKS_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_SHADOWSOCKS_DEB_FILE")}
OMR_LIBSHADOWSOCKS_LIBEV2_DEB_FILE=${OMR_LIBSHADOWSOCKS_LIBEV2_DEB_FILE:-$(select_static_deb_file "omr-libshadowsocks-libev2_${OMR_LIBSHADOWSOCKS_LIBEV2_BINARY_VERSION}_amd64.deb" "omr-libshadowsocks-libev2_" "_amd64.deb")}
OMR_LIBSHADOWSOCKS_LIBEV2_DEB_URL=${OMR_LIBSHADOWSOCKS_LIBEV2_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_LIBSHADOWSOCKS_LIBEV2_DEB_FILE")}
OMR_LIBSHADOWSOCKS_LIBEV_DEV_DEB_FILE=${OMR_LIBSHADOWSOCKS_LIBEV_DEV_DEB_FILE:-$(select_static_deb_file "omr-libshadowsocks-libev-dev_${OMR_LIBSHADOWSOCKS_LIBEV_DEV_BINARY_VERSION}_amd64.deb" "omr-libshadowsocks-libev-dev_" "_amd64.deb")}
OMR_LIBSHADOWSOCKS_LIBEV_DEV_DEB_URL=${OMR_LIBSHADOWSOCKS_LIBEV_DEV_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_LIBSHADOWSOCKS_LIBEV_DEV_DEB_FILE")}
PYTHON3_FLASK_DEB_FILE=${PYTHON3_FLASK_DEB_FILE:-$(select_static_deb_file "python3-flask_${PYTHON3_FLASK_VERSION}_all.deb" "python3-flask_" "_all.deb")}
PYTHON3_FLASK_DEB_URL=${PYTHON3_FLASK_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_FLASK_DEB_FILE")}
PYTHON3_FLASK_JWT_SIMPLE_DEB_FILE=${PYTHON3_FLASK_JWT_SIMPLE_DEB_FILE:-$(select_static_deb_file "python3-flask-jwt-simple_${PYTHON3_FLASK_JWT_SIMPLE_VERSION}_all.deb" "python3-flask-jwt-simple_" "_all.deb")}
PYTHON3_FLASK_JWT_SIMPLE_DEB_URL=${PYTHON3_FLASK_JWT_SIMPLE_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_FLASK_JWT_SIMPLE_DEB_FILE")}
PYTHON3_ITSDANGEROUS_DEB_FILE=${PYTHON3_ITSDANGEROUS_DEB_FILE:-$(select_static_deb_file "python3-itsdangerous_${PYTHON3_ITSDANGEROUS_VERSION}_all.deb" "python3-itsdangerous_" "_all.deb")}
PYTHON3_ITSDANGEROUS_DEB_URL=${PYTHON3_ITSDANGEROUS_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_ITSDANGEROUS_DEB_FILE")}
PYTHON3_JINJA2_DEB_FILE=${PYTHON3_JINJA2_DEB_FILE:-$(select_static_deb_file "python3-jinja2_${PYTHON3_JINJA2_VERSION}_all.deb" "python3-jinja2_" "_all.deb")}
PYTHON3_JINJA2_DEB_URL=${PYTHON3_JINJA2_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_JINJA2_DEB_FILE")}
PYTHON3_MARKUPSAFE_DEB_FILE=${PYTHON3_MARKUPSAFE_DEB_FILE:-$(select_static_deb_file "python3-markupsafe_${PYTHON3_MARKUPSAFE_VERSION}_amd64.deb" "python3-markupsafe_" "_amd64.deb")}
PYTHON3_MARKUPSAFE_DEB_URL=${PYTHON3_MARKUPSAFE_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_MARKUPSAFE_DEB_FILE")}
PYTHON3_PYJWT_DEB_FILE=${PYTHON3_PYJWT_DEB_FILE:-$(select_static_deb_file "python3-pyjwt_${PYTHON3_PYJWT_VERSION}_all.deb" "python3-pyjwt_" "_all.deb")}
PYTHON3_PYJWT_DEB_URL=${PYTHON3_PYJWT_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_PYJWT_DEB_FILE")}
PYTHON3_UVICORN_DEB_FILE=${PYTHON3_UVICORN_DEB_FILE:-$(select_static_deb_file "python3-uvicorn_${PYTHON3_UVICORN_VERSION}_all.deb" "python3-uvicorn_" "_all.deb")}
PYTHON3_UVICORN_DEB_URL=${PYTHON3_UVICORN_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_UVICORN_DEB_FILE")}
PYTHON3_UVLOOP_DEB_FILE=${PYTHON3_UVLOOP_DEB_FILE:-$(select_static_deb_file "python3-uvloop_${PYTHON3_UVLOOP_VERSION}_amd64.deb" "python3-uvloop_" "_amd64.deb")}
PYTHON3_UVLOOP_DEB_URL=${PYTHON3_UVLOOP_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_UVLOOP_DEB_FILE")}
PYTHON3_WATCHGOD_DEB_FILE=${PYTHON3_WATCHGOD_DEB_FILE:-$(select_static_deb_file "python3-watchgod_${PYTHON3_WATCHGOD_VERSION}_all.deb" "python3-watchgod_" "_all.deb")}
PYTHON3_WATCHGOD_DEB_URL=${PYTHON3_WATCHGOD_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_WATCHGOD_DEB_FILE")}
PYTHON3_WERKZEUG_DEB_FILE=${PYTHON3_WERKZEUG_DEB_FILE:-$(select_static_deb_file "python3-werkzeug_${PYTHON3_WERKZEUG_VERSION}_all.deb" "python3-werkzeug_" "_all.deb")}
PYTHON3_WERKZEUG_DEB_URL=${PYTHON3_WERKZEUG_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$PYTHON3_WERKZEUG_DEB_FILE")}
OMR_VPS_ADMIN_DEB_FILE=${OMR_VPS_ADMIN_DEB_FILE:-omr-vps-admin_${OMR_ADMIN_BINARY_VERSION}_all.deb}
OMR_VPS_ADMIN_DEB_URL=${OMR_VPS_ADMIN_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_VPS_ADMIN_DEB_FILE")}
OMR_SIMPLE_OBFS_DEB_FILE=${OMR_SIMPLE_OBFS_DEB_FILE:-omr-simple-obfs_${OBFS_BINARY_VERSION}_amd64.deb}
OMR_SIMPLE_OBFS_DEB_URL=${OMR_SIMPLE_OBFS_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_SIMPLE_OBFS_DEB_FILE")}
OMR_MLVPN_DEB_FILE=${OMR_MLVPN_DEB_FILE:-omr-mlvpn_${MLVPN_BINARY_VERSION}_amd64.deb}
OMR_MLVPN_DEB_URL=${OMR_MLVPN_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_MLVPN_DEB_FILE")}
OMR_GLORYTUN_DEB_FILE=${OMR_GLORYTUN_DEB_FILE:-omr-glorytun_${GLORYTUN_UDP_BINARY_VERSION}_amd64.deb}
OMR_GLORYTUN_DEB_URL=${OMR_GLORYTUN_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_GLORYTUN_DEB_FILE")}
OMR_GLORYTUN_TCP_DEB_FILE=${OMR_GLORYTUN_TCP_DEB_FILE:-omr-glorytun-tcp_${GLORYTUN_TCP_BINARY_VERSION}_amd64.deb}
OMR_GLORYTUN_TCP_DEB_URL=${OMR_GLORYTUN_TCP_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_GLORYTUN_TCP_DEB_FILE")}
OMR_DSVPN_DEB_FILE=${OMR_DSVPN_DEB_FILE:-omr-dsvpn_${DSVPN_BINARY_VERSION}_amd64.deb}
OMR_DSVPN_DEB_URL=${OMR_DSVPN_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_DSVPN_DEB_FILE")}
V2RAY_DEB_FILE=${V2RAY_DEB_FILE:-v2ray-${V2RAY_VERSION}-amd64.deb}
V2RAY_DEB_URL=${V2RAY_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$V2RAY_DEB_FILE")}
V2RAY_PLUGIN_DEB_FILE=${V2RAY_PLUGIN_DEB_FILE:-v2ray-plugin_${V2RAY_PLUGIN_VERSION}_amd64.deb}
V2RAY_PLUGIN_DEB_URL=${V2RAY_PLUGIN_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$V2RAY_PLUGIN_DEB_FILE")}
OMR_SERVER_DEB_FILE=${OMR_SERVER_DEB_FILE:-$(select_static_deb_file "omr-server_${OMR_VERSION}_all.deb" "omr-server_" "_all.deb")}
OMR_SERVER_DEB_URL=${OMR_SERVER_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OMR_SERVER_DEB_FILE")}
OPENVPN_DEB_FILE=${OPENVPN_DEB_FILE:-$(select_static_deb_file "openvpn_${OPENVPN_BINARY_VERSION}_amd64.deb" "openvpn_" "_amd64.deb")}
OPENVPN_DEB_URL=${OPENVPN_DEB_URL:-$(get_static_deb_url "$OMR_STATIC_DEB_BASE" "$OPENVPN_DEB_FILE")}

set -e
umask 0022
export LC_ALL=C
export PATH=$PATH:/sbin
export DEBIAN_FRONTEND=noninteractive 

echo "Check user..."
if [ "$(id -u)" -ne 0 ]; then echo 'Please run as root.' >&2; exit 1; fi

# Check Linux version
echo "Check Linux version..."
if test -f /etc/os-release ; then
        . /etc/os-release
else
        . /usr/lib/os-release
fi
if [ "$ID" != "debian" ] || [ "$VERSION_ID" != "11" ]; then
        echo "This script only works with Debian Bullseye (11.x)"
        exit 1
fi

echo "Check architecture..."
ARCH=$(dpkg --print-architecture | tr -d "\n")
if [ "$ARCH" != "amd64" ]; then
	echo "Only x86_64 (amd64) is supported"
	exit 1
fi

echo "Check virtualized environment"
VIRT="$(systemd-detect-virt 2>/dev/null || true)"
if [ -z "$(uname -a | grep mptcp)" ] && [ -n "$VIRT" ] && ([ "$VIRT" = "openvz" ] || [ "$VIRT" = "lxc" ] || [ "$VIRT" = "docker" ]); then
	echo "Container are not supported: kernel can't be modified."
	exit 1
fi

# Check if DPKG is locked and for broken packages
#dpkg -i /dev/zero 2>/dev/null
#if [ "$?" -eq 2 ]; then
#	echo "E: dpkg database is locked. Check that an update is not running in background..."
#	exit 1
#fi
echo "Check about broken packages..."
apt-get check >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
	echo "E: \`apt-get check\` failed, you may have broken packages. Aborting..."
	exit 1
fi

# Fix old string...
if [ -f /etc/motd ] && grep --quiet 'OpenMPCTProuter VPS' /etc/motd ; then
	sed -i 's/OpenMPCTProuter/OpenMPTCProuter/g' /etc/motd
fi
if [ -f /etc/motd.head ] && grep --quiet 'OpenMPCTProuter VPS' /etc/motd.head ; then
	sed -i 's/OpenMPCTProuter/OpenMPTCProuter/g' /etc/motd.head
fi

# Check if OpenMPTCProuter VPS is already installed
echo "Check if OpenMPTCProuter VPS is already installed..."
update="0"
if [ "$UPDATE" = "yes" ]; then
	if [ -f /etc/motd ] && grep --quiet 'OpenMPTCProuter VPS' /etc/motd ; then
		update="1"
	elif [ -f /etc/motd.head ] && grep --quiet 'OpenMPTCProuter VPS' /etc/motd.head ; then
		update="1"
	elif [ -f /root/openmptcprouter_config.txt ]; then
		update="1"
	fi
	echo "Update mode"
fi
# Force update key
[ "$USE_OMR_REPO" = "yes" ] && [ -f /etc/apt/sources.list.d/openmptcprouter.list ] && {
        echo "Update OpenMPTCProuter repo key"
        wget -O - http://repo.openmptcprouter.com/openmptcprouter.gpg.key | apt-key add -
}

CURRENT_OMR="$(grep -s 'OpenMPTCProuter VPS' /etc/* | awk '{print $4}')"
if [ "$REINSTALL" = "no" ] && [ "$CURRENT_OMR" = "$OMR_VERSION" ]; then
	exit 1
fi

[ "$USE_OMR_REPO" = "yes" ] && [ -f /etc/apt/sources.list.d/openmptcprouter.list ] && {
        echo "Update ${REPO} key"
        if [ "$CHINA" = "yes" ]; then
                #wget -O - https://gitee.com/ysurac/openmptcprouter-vps-debian/raw/main/openmptcprouter.gpg.key | apt-key add -
                wget -O - https://gitlab.com/ysurac/openmptcprouter-vps-debian/raw/main/openmptcprouter.gpg.key | apt-key add -
        else
                wget -O - https://${REPO}/openmptcprouter.gpg.key | apt-key add -
        fi
}

echo "Remove lock and update packages list..."
rm -f /var/lib/dpkg/lock
rm -f /var/lib/dpkg/lock-frontend
rm -f /var/cache/apt/archives/lock
apt-get update --allow-releaseinfo-change
rm -f /var/lib/dpkg/lock
rm -f /var/lib/dpkg/lock-frontend
rm -f /var/cache/apt/archives/lock
echo "Install apt-transport-https, gnupg and openssh-server..."
apt-get -y install apt-transport-https gnupg openssh-server

# Remove legacy distribution upgrade paths as the script now targets Debian 11 only

# Add OpenMPTCProuter repo
echo "Add OpenMPTCProuter repo..."
if [ "$USE_OMR_REPO" = "yes" ]; then
        if [ "$CHINA" = "yes" ]; then
        echo "Install git..."
        apt-get -y install git
        if [ ! -d /var/lib/openmptcprouter-vps-debian ]; then
		#git clone https://gitee.com/ysurac/openmptcprouter-vps-debian.git /var/lib/openmptcprouter-vps-debian
		git clone https://gitlab.com/ysurac/openmptcprouter-vps-debian.git /var/lib/openmptcprouter-vps-debian
	fi
	cd /var/lib/openmptcprouter-vps-debian
	git pull
#	if [ "$VPSPATH" = "server-test" ]; then
#		git checkout develop
#	else
#		git checkout main
#	fi
	echo "deb [arch=amd64] file:/var/lib/openmptcprouter-vps-debian ./" > /etc/apt/sources.list.d/openmptcprouter.list
	cat /var/lib/openmptcprouter-vps-debian/openmptcprouter.gpg.key | apt-key add -
	if [ ! -d /usr/share/omr-server-git ]; then
		#git clone https://gitee.com/ysurac/openmptcprouter-vps.git /usr/share/omr-server-git
		git clone https://gitlab.com/ysurac/openmptcprouter-vps.git /usr/share/omr-server-git
	fi
	cd /usr/share/omr-server-git
	git pull
	if [ "$VPSPATH" = "server-test" ]; then
		git checkout develop
	else
		git checkout master
fi
LOCALFILES="yes"
TLS="no"
DIR="/usr/share/omr-server-git"

echo "deb [arch=amd64] https://${REPO} bullseye main" > /etc/apt/sources.list.d/openmptcprouter.list
cat <<-EOF | tee /etc/apt/preferences.d/openmptcprouter.pref
	Explanation: Prefer OpenMPTCProuter provided packages over the Debian native ones
	Package: *
	Pin: origin ${REPO}
	Pin-Priority: 1001
EOF

	if [ -n "$(echo $OMR_VERSION | grep test)" ]; then
		echo "deb [arch=amd64] https://${REPO} next main" > /etc/apt/sources.list.d/openmptcprouter-test.list
		cat <<-EOF | tee /etc/apt/preferences.d/openmptcprouter.pref
			Explanation: Prefer OpenMPTCProuter provided packages over the Debian native ones
			Package: *
			Pin: origin ${REPO}
			Pin-Priority: 1002
		EOF
	else
		rm -f /etc/apt/sources.list.d/openmptcprouter-test.list
        fi
        wget -O - https://${REPO}/openmptcprouter.gpg.key | apt-key add -
        fi
else
        rm -f /etc/apt/sources.list.d/openmptcprouter.list
        rm -f /etc/apt/sources.list.d/openmptcprouter-test.list
        rm -f /etc/apt/preferences.d/openmptcprouter.pref
fi

# Install mptcp kernel and shadowsocks
echo "Install mptcp kernel and shadowsocks..."
apt-get update --allow-releaseinfo-change
sleep 2
apt-get -y install dirmngr patch rename curl libcurl4 unzip pkg-config

if [ -z "$(dpkg-query -l | grep grub)" ]; then
	if [ -d /boot/grub2 ]; then
		apt-get -y install grub2
	elif [ -d /boot/grub ]; then
		apt-get -y install grub-legacy
	fi
	[ -n "$(grep 'net.ifnames=0' /boot/grub/grub.cfg)" ] && [ ! -f /etc/default/grub ] && {
		echo 'GRUB_CMDLINE_LINUX="net.ifnames=0 biosdevname=0"' > /etc/default/grub
	}
fi


if [ -z "$(dpkg-query -l | grep grub)" ]; then
	if [ -d /boot/grub2 ]; then
		apt-get -y install grub2
	elif [ -d /boot/grub ]; then
		apt-get -y install grub-legacy
	fi
	[ -n "$(grep 'net.ifnames=0' /boot/grub/grub.cfg)" ] && [ ! -f /etc/default/grub ] && {
		echo 'GRUB_CMDLINE_LINUX="net.ifnames=0 biosdevname=0"' > /etc/default/grub
	}
fi
if [ "$SOURCES" = "yes" ]; then
	wget -O /tmp/linux-image-${KERNEL_RELEASE}_amd64.deb ${VPSURL}kernel/linux-image-${KERNEL_RELEASE}_amd64.deb
	wget -O /tmp/linux-headers-${KERNEL_RELEASE}_amd64.deb ${VPSURL}kernel/linux-headers-${KERNEL_RELEASE}_amd64.deb
	# Rename bzImage to vmlinuz, needed when custom kernel was used
	cd /boot
	apt-get -y install git
	rename 's/^bzImage/vmlinuz/s' * >/dev/null 2>&1
	#apt-get -y install linux-mptcp
	#dpkg --remove --force-remove-reinstreq linux-image-${KERNEL_VERSION}-mptcp
	#dpkg --remove --force-remove-reinstreq linux-headers-${KERNEL_VERSION}-mptcp
	if [ "$(dpkg -l | grep linux-image-${KERNEL_VERSION} | grep ${KERNEL_PACKAGE_VERSION})" = "" ]; then
		echo "Install kernel linux-image-${KERNEL_RELEASE} source release"
		echo "\033[1m !!! if kernel install fail run: dpkg --remove --force-remove-reinstreq linux-image-${KERNEL_VERSION}-mptcp !!! \033[0m"
		dpkg --force-all -i -B /tmp/linux-headers-${KERNEL_RELEASE}_amd64.deb
		dpkg --force-all -i -B /tmp/linux-image-${KERNEL_RELEASE}_amd64.deb
	fi
else
	cd /boot
	rename 's/^bzImage/vmlinuz/s' * >/dev/null 2>&1
        if [ "$(dpkg -l | grep linux-image-${KERNEL_VERSION} | grep ${KERNEL_PACKAGE_VERSION})" = "" ]; then
                echo "Install kernel linux-image-${KERNEL_RELEASE}"
                echo "\033[1m !!! if kernel install fail run: dpkg --remove --force-remove-reinstreq linux-image-${KERNEL_VERSION}-mptcp !!! \033[0m"
                install_omr_package "linux-image-${KERNEL_VERSION}-mptcp" "${KERNEL_PACKAGE_VERSION}" "$LINUX_IMAGE_DEB_FILE" "$LINUX_IMAGE_DEB_URL"
                install_omr_package "linux-headers-${KERNEL_VERSION}-mptcp" "${KERNEL_PACKAGE_VERSION}" "$LINUX_HEADERS_DEB_FILE" "$LINUX_HEADERS_DEB_URL"
        fi
fi

# Check if mptcp kernel is grub default kernel
echo "Set MPTCP kernel as grub default..."
if [ "$LOCALFILES" = "no" ]; then
	wget -O /tmp/update-grub.sh ${VPSURL}${VPSPATH}/update-grub.sh
	cd /tmp
else
	cd ${DIR}
fi
[ -f /boot/grub/grub.cfg ] && [ -z "$(grep ${KERNEL_VERSION}-mptcp /boot/grub/grub.cfg)" ] && [ -n "$(which grub-mkconfig)" ] && grub-mkconfig -o /boot/grub/grub.cfg
rm -f /etc/grub.d/30_os-prober
bash update-grub.sh ${KERNEL_VERSION}-mptcp
bash update-grub.sh ${KERNEL_RELEASE}
[ -f /boot/grub/grub.cfg ] && sed -i 's/default="1>0"/default="0"/' /boot/grub/grub.cfg 2>&1 >/dev/null

echo "Install tracebox OpenMPTCProuter edition"
apt-get -y install liblua5.2-0 libpcap0.8 libnetfilter-queue1 libcurl4-gnutls-dev
install_omr_package "libjson-c3" "$LIBJSON_C3_VERSION" "$LIBJSON_C3_DEB_FILE" "$LIBJSON_C3_DEB_URL" "--allow-downgrades"
install_omr_package "tracebox" "" "$TRACEBOX_DEB_FILE" "$TRACEBOX_DEB_URL" "-o" "Dpkg::Options::=--force-overwrite"
echo "Install iperf3 OpenMPTCProuter edition"
apt-get -y install libsctp1
install_omr_package "omr-libiperf0" "$OMR_LIBIPERF0_BINARY_VERSION" "$OMR_LIBIPERF0_DEB_FILE" "$OMR_LIBIPERF0_DEB_URL" "-o" "Dpkg::Options::=--force-overwrite"
install_omr_package "omr-iperf3" "" "$OMR_IPERF3_DEB_FILE" "$OMR_IPERF3_DEB_URL" "-o" "Dpkg::Options::=--force-overwrite"

if [ "$UPSTREAM" = "yes" ]; then
	echo "Compile and install mptcpize..."
	apt-get -y install --no-install-recommends build-essential
	cd /tmp
	git clone https://github.com/Ysurac/mptcpize.git
	cd mptcpize
	make
	make install
	cd /tmp
	rm -rf /tmp/mptcpize
	echo "Compile and install iproute2..."
	apt-get -y install --no-install-recommends bison libbison-dev flex
	#wget https://mirrors.edge.kernel.org/pub/linux/utils/net/iproute2/iproute2-5.16.0.tar.gz
	#tar xzf iproute2-5.16.0.tar.gz
	#cd iproute2-5.16.0
	git clone git://git.kernel.org/pub/scm/network/iproute2/iproute2.git 
	cd iproute2
	git checkout 29da83f89f6e1fe528c59131a01f5d43bcd0a000
	make
	make install
	cd /tmp
	rm -rf iproute2
	echo "MPTCPize iperf3..."
	mptcpize enable iperf3
fi

apt-get -y remove shadowsocks-libev

if [ "$SOURCES" = "yes" ]; then
	#apt -t stretch-backports -y install shadowsocks-libev
	## Compile Shadowsocks
	#rm -rf /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}
	#wget -O /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}.tar.gz http://github.com/shadowsocks/shadowsocks-libev/releases/download/v${SHADOWSOCKS_VERSION}/shadowsocks-libev-${SHADOWSOCKS_VERSION}.tar.gz
	cd /tmp
	rm -rf shadowsocks-libev
	git clone https://github.com/Ysurac/shadowsocks-libev.git
	cd shadowsocks-libev
	git checkout ${SHADOWSOCKS_VERSION}
	git submodule update --init --recursive
	#tar xzf shadowsocks-libev-${SHADOWSOCKS_VERSION}.tar.gz
	#cd shadowsocks-libev-${SHADOWSOCKS_VERSION}
	#wget https://raw.githubusercontent.com/Ysurac/openmptcprouter-feeds/master/shadowsocks-libev/patches/020-NOCRYPTO.patch
	#patch -p1 < 020-NOCRYPTO.patch
	#wget https://github.com/Ysurac/shadowsocks-libev/commit/31b93ac2b054bc3f68ea01569649e6882d72218e.patch
	#patch -p1 < 31b93ac2b054bc3f68ea01569649e6882d72218e.patch
	#wget https://github.com/Ysurac/shadowsocks-libev/commit/2e52734b3bf176966e78e77cf080a1e8c6b2b570.patch
	#patch -p1 < 2e52734b3bf176966e78e77cf080a1e8c6b2b570.patch
	#wget https://github.com/Ysurac/shadowsocks-libev/commit/dd1baa91e975a69508f9ad67d75d72624c773d24.patch
	#patch -p1 < dd1baa91e975a69508f9ad67d75d72624c773d24.patch
	# Shadowsocks eBPF support
	#wget https://raw.githubusercontent.com/Ysurac/openmptcprouter-feeds/master/shadowsocks-libev/patches/030-eBPF.patch
	#patch -p1 < 030-eBPF.patch
	#rm -f /var/lib/dpkg/lock
	#apt-get install -y --no-install-recommends build-essential git ca-certificates libcap-dev libelf-dev libpcap-dev
	#cd /tmp
	#rm -rf libbpf
	#git clone https://github.com/libbpf/libbpf.git
	#cd libbpf
	#if [ "$ID" = "debian" ]; then
	#	rm -f /var/lib/dpkg/lock
	#	apt -y -t stretch-backports install linux-libc-dev
	#elif [ "$ID" = "ubuntu" ]; then
	#	rm -f /var/lib/dpkg/lock
	#	apt-get -y install linux-libc-dev
	#fi
	#BUILD_SHARED=y make -C src CFLAGS="$CFLAGS -DCOMPAT_NEED_REALLOCARRAY"
	#cp /tmp/libbpf/src/libbpf.so /usr/lib
	#cp /tmp/libbpf/src/*.h /usr/include/bpf
	#cd /tmp
	#rm -rf /tmp/libbpf
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	apt-get -y install --no-install-recommends devscripts equivs apg libcap2-bin libpam-cap libc-ares2 libc-ares-dev libev4 haveged libpcre3-dev
	apt-get -y install --no-install-recommends asciidoc-base asciidoc-common docbook-xml docbook-xsl libev-dev libmbedcrypto3 libmbedtls-dev libmbedtls12 libmbedx509-0 libxml2-utils libxslt1.1 pkg-config sgml-base sgml-data xml-core xmlto xsltproc
	sleep 1
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	systemctl enable haveged
	
        rm -f /var/lib/dpkg/lock
        rm -f /var/lib/dpkg/lock-frontend
        apt-get -y install libsodium-dev
	#cd /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	mk-build-deps --install --tool "apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends -y"
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	dpkg-buildpackage -b -us -uc
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	cd /tmp
	#dpkg -i shadowsocks-libev_*.deb
	dpkg -i omr-shadowsocks-libev_*.deb 2>&1 >/dev/null
	#mkdir -p /usr/lib/shadowsocks-libev
	#cp -f /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}/src/*.ebpf /usr/lib/shadowsocks-libev
	#rm -rf /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}
	rm -rf /tmp/shadowsocks-libev
else
        install_omr_package "libsodium18" "$LIBSODIUM18_VERSION" "$LIBSODIUM18_DEB_FILE" "$LIBSODIUM18_DEB_URL" "--allow-downgrades"
        install_omr_package "libshadowsocks-libev2" "$LIBSHADOWSOCKS_LIBEV2_VERSION" "$LIBSHADOWSOCKS_LIBEV2_DEB_FILE" "$LIBSHADOWSOCKS_LIBEV2_DEB_URL" "-o" "Dpkg::Options::=--force-overwrite"
        install_omr_package "omr-libshadowsocks-libev2" "$OMR_LIBSHADOWSOCKS_LIBEV2_BINARY_VERSION" "$OMR_LIBSHADOWSOCKS_LIBEV2_DEB_FILE" "$OMR_LIBSHADOWSOCKS_LIBEV2_DEB_URL" "-o" "Dpkg::Options::=--force-overwrite"
        install_omr_package "omr-libshadowsocks-libev-dev" "$OMR_LIBSHADOWSOCKS_LIBEV_DEV_BINARY_VERSION" "$OMR_LIBSHADOWSOCKS_LIBEV_DEV_DEB_FILE" "$OMR_LIBSHADOWSOCKS_LIBEV_DEV_DEB_URL" "-o" "Dpkg::Options::=--force-overwrite"
        install_omr_package "omr-shadowsocks-libev" "${SHADOWSOCKS_BINARY_VERSION}" "$OMR_SHADOWSOCKS_DEB_FILE" "$OMR_SHADOWSOCKS_DEB_URL" "-o" "Dpkg::Options::=--force-confold" "-o" "Dpkg::Options::=--force-confdef" "-o" "Dpkg::Options::=--force-overwrite"
fi

# Load OLIA Congestion module at boot time
if ! grep -q olia /etc/modules ; then
	echo mptcp_olia >> /etc/modules
fi
# Load WVEGAS Congestion module at boot time
if ! grep -q wvegas /etc/modules ; then
	echo mptcp_wvegas >> /etc/modules
fi
# Load BALIA Congestion module at boot time
if ! grep -q balia /etc/modules ; then
	echo mptcp_balia >> /etc/modules
fi
# Load BBR Congestion module at boot time
if ! grep -q bbr /etc/modules ; then
	echo tcp_bbr >> /etc/modules
fi
# Load BBRv2 Congestion module at boot time
if ! grep -q bbr2 /etc/modules ; then
	echo tcp_bbr2 >> /etc/modules
fi
# Load mctcpdesync Congestion module at boot time
if ! grep -q mctcp_desync /etc/modules ; then
	echo mctcp_desync >> /etc/modules
fi
# Load ndiffports module at boot time
if ! grep -q mptcp_ndiffports /etc/modules ; then
	echo mptcp_ndiffports >> /etc/modules
fi
# Load redundant module at boot time
if ! grep -q mptcp_redundant /etc/modules ; then
	echo mptcp_redundant >> /etc/modules
fi
# Load rr module at boot time
if ! grep -q mptcp_rr /etc/modules ; then
	echo mptcp_rr >> /etc/modules
fi
# Load mctcp ECF scheduler at boot time
if ! grep -q mptcp_ecf /etc/modules ; then
	echo mptcp_ecf >> /etc/modules
fi
# Load mctcp BLEST scheduler at boot time
if ! grep -q mptcp_blest /etc/modules ; then
	echo mptcp_blest >> /etc/modules
fi

if systemctl -q is-active omr-admin.service; then
	systemctl -q stop omr-admin > /dev/null 2>&1
fi

if [ "$OMR_ADMIN" = "yes" ]; then
        echo 'Install OpenMPTCProuter VPS Admin'
        apt-get -y install python3-openssl python3-pip python3-setuptools python3-wheel python3-dev
        #apt-get -y install unzip gunicorn python3-flask-restful python3-openssl python3-pip python3-setuptools python3-wheel
        #apt-get -y install unzip python3-openssl python3-pip python3-setuptools python3-wheel
        install_omr_package "libuv1" "$LIBUV1_VERSION" "$LIBUV1_DEB_FILE" "$LIBUV1_DEB_URL" "--allow-downgrades"
        apt-get -y --allow-downgrades install python3-passlib python3-jwt python3-netaddr
        install_omr_package "python3-flask" "$PYTHON3_FLASK_VERSION" "$PYTHON3_FLASK_DEB_FILE" "$PYTHON3_FLASK_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-flask-jwt-simple" "$PYTHON3_FLASK_JWT_SIMPLE_VERSION" "$PYTHON3_FLASK_JWT_SIMPLE_DEB_FILE" "$PYTHON3_FLASK_JWT_SIMPLE_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-itsdangerous" "$PYTHON3_ITSDANGEROUS_VERSION" "$PYTHON3_ITSDANGEROUS_DEB_FILE" "$PYTHON3_ITSDANGEROUS_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-jinja2" "$PYTHON3_JINJA2_VERSION" "$PYTHON3_JINJA2_DEB_FILE" "$PYTHON3_JINJA2_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-markupsafe" "$PYTHON3_MARKUPSAFE_VERSION" "$PYTHON3_MARKUPSAFE_DEB_FILE" "$PYTHON3_MARKUPSAFE_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-pyjwt" "$PYTHON3_PYJWT_VERSION" "$PYTHON3_PYJWT_DEB_FILE" "$PYTHON3_PYJWT_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-uvicorn" "$PYTHON3_UVICORN_VERSION" "$PYTHON3_UVICORN_DEB_FILE" "$PYTHON3_UVICORN_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-uvloop" "$PYTHON3_UVLOOP_VERSION" "$PYTHON3_UVLOOP_DEB_FILE" "$PYTHON3_UVLOOP_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-watchgod" "$PYTHON3_WATCHGOD_VERSION" "$PYTHON3_WATCHGOD_DEB_FILE" "$PYTHON3_WATCHGOD_DEB_URL" "--allow-downgrades"
        install_omr_package "python3-werkzeug" "$PYTHON3_WERKZEUG_VERSION" "$PYTHON3_WERKZEUG_DEB_FILE" "$PYTHON3_WERKZEUG_DEB_URL" "--allow-downgrades"
        pip3 -q install uvloop
        apt-get -y --allow-downgrades install jq ipcalc python3-netifaces python3-aiofiles python3-psutil python3-requests pwgen
	echo '-- pip3 install needed python modules'
	echo "If you see any error here, I really don't care: it's about a module not used for home users"
	#pip3 install pyjwt passlib uvicorn fastapi netjsonconfig python-multipart netaddr
	#pip3 -q install fastapi netjsonconfig python-multipart uvicorn -U
	pip3 -q install netjsonconfig
	pip3 -q install fastapi -U
	pip3 -q install jsonschema -U
	pip3 -q install python-multipart jinja2 -U
	pip3 -q install starlette
	pip3 -q install starlette
	mkdir -p /etc/openmptcprouter-vps-admin/omr-6in4
	mkdir -p /etc/openmptcprouter-vps-admin/intf
	[ ! -f "/etc/openmptcprouter-vps-admin/current-vpn" ] && echo "glorytun_tcp" > /etc/openmptcprouter-vps-admin/current-vpn
	mkdir -p /var/opt/openmptcprouter
	if [ "$SOURCES" = "yes" ]; then
		wget -O /lib/systemd/system/omr-admin.service ${VPSURL}${VPSPATH}/omr-admin.service.in
		wget -O /lib/systemd/system/omr-admin-ipv6.service ${VPSURL}${VPSPATH}/omr-admin-ipv6.service.in
		wget -O /tmp/openmptcprouter-vps-admin.zip https://github.com/Ysurac/openmptcprouter-vps-admin/archive/${OMR_ADMIN_VERSION}.zip
		cd /tmp
		unzip -q -o openmptcprouter-vps-admin.zip
		cp /tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}/omr-admin.py /usr/local/bin/
		if [ -f /usr/local/bin/omr-admin.py ] || [ -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ]; then
			OMR_ADMIN_PASS2=$(grep -Po '"'"pass"'"\s*:\s*"\K([^"]*)' /etc/openmptcprouter-vps-admin/omr-admin-config.json | tr -d  "\n")
			[ -z "$OMR_ADMIN_PASS2" ] && OMR_ADMIN_PASS2=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].openmptcprouter.user_password | tr -d "\n")
			[ -n "$OMR_ADMIN_PASS2" ] && OMR_ADMIN_PASS=$OMR_ADMIN_PASS2
			OMR_ADMIN_PASS_ADMIN2=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].admin.user_password | tr -d "\n")
			[ -n "$OMR_ADMIN_PASS_ADMIN2" ] && OMR_ADMIN_PASS_ADMIN=$OMR_ADMIN_PASS_ADMIN2
		else
			cp /tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}/omr-admin.py /usr/local/bin/
			cd /etc/openmptcprouter-vps-admin
		fi
		if [ "$(grep user_password /etc/openmptcprouter-vps-admin/omr-admin-config.json)" = "" ]; then
			cp /tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}/omr-admin-config.json /etc/openmptcprouter-vps-admin/
			cp /tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}/omr-admin.py /usr/local/bin/
			cd /etc/openmptcprouter-vps-admin
		fi
		rm -rf /tmp/tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}
		chmod u+x /usr/local/bin/omr-admin.py
	else
		if [ -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ]; then
			OMR_ADMIN_PASS2=$(grep -Po '"'"pass"'"\s*:\s*"\K([^"]*)' /etc/openmptcprouter-vps-admin/omr-admin-config.json | tr -d  "\n")
			[ -z "$OMR_ADMIN_PASS2" ] && OMR_ADMIN_PASS2=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].openmptcprouter.user_password | tr -d "\n")
			[ -n "$OMR_ADMIN_PASS2" ] && [ "$OMR_ADMIN_PASS2" != "MySecretKey" ] && OMR_ADMIN_PASS=$OMR_ADMIN_PASS2
			OMR_ADMIN_PASS_ADMIN2=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].admin.user_password | tr -d "\n")
			[ -n "$OMR_ADMIN_PASS_ADMIN2" ] && [ "$OMR_ADMIN_PASS_ADMIN2" != "AdminMySecretKey" ] && OMR_ADMIN_PASS_ADMIN=$OMR_ADMIN_PASS_ADMIN2
		fi
            install_omr_package "omr-vps-admin" "${OMR_ADMIN_BINARY_VERSION}" "$OMR_VPS_ADMIN_DEB_FILE" "$OMR_VPS_ADMIN_DEB_URL" "-o" "Dpkg::Options::=--force-confold" "-o" "Dpkg::Options::=--force-confdef" "-o" "Dpkg::Options::=--force-overwrite"
		if [ ! -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ]; then
			cp /usr/share/omr-admin/omr-admin-config.json /etc/openmptcprouter-vps-admin/
		fi
		#OMR_ADMIN_PASS=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].openmptcprouter.user_password | tr -d "\n")
		#OMR_ADMIN_PASS_ADMIN=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].admin.user_password | tr -d "\n")
	fi
	if [ ! -f /etc/openmptcprouter-vps-admin/key.pem ]; then
		cd /etc/openmptcprouter-vps-admin
		openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -keyout key.pem -out cert.pem -subj "/C=US/ST=Oregon/L=Portland/O=OpenMPTCProuterVPS/OU=Org/CN=www.openmptcprouter.vps"
	fi
	sed -i "s:openmptcptouter:${DEFAULT_USER}:g" /etc/openmptcprouter-vps-admin/omr-admin-config.json
	sed -i "s:AdminMySecretKey:$OMR_ADMIN_PASS_ADMIN:g" /etc/openmptcprouter-vps-admin/omr-admin-config.json
	sed -i "s:MySecretKey:$OMR_ADMIN_PASS:g" /etc/openmptcprouter-vps-admin/omr-admin-config.json
	[ "$NOINTERNET" = "yes" ] && {
		sed -i 's/"port": 65500,/"port": 65500,\n    "internet": false,/' /etc/openmptcprouter-vps-admin/omr-admin-config.json
	}
	#[ "$(ip -6 a)" != "" ] && sed -i 's/0.0.0.0/::/g' /usr/local/bin/omr-admin.py
	[ "$(ip -6 a)" != "" ] && {
		systemctl enable omr-admin-ipv6.service
	}
	systemctl enable omr-admin.service
	if [ "$UPSTREAM" = "yes" ]; then
		mptcpize enable omr-admin.service
		[ "$(ip -6 a)" != "" ] && mptcpize enable omr-admin-ipv6.service
	fi
fi

# Get shadowsocks optimization
if [ "$LOCALFILES" = "no" ]; then
	wget -O /etc/sysctl.d/90-shadowsocks.conf ${VPSURL}${VPSPATH}/shadowsocks.conf
else
	cp ${DIR}/shadowsocks.conf /etc/sysctl.d/90-shadowsocks.conf
fi

if [ "$update" != 0 ]; then
	if [ ! -f /etc/shadowsocks-libev/manager.json ]; then
		SHADOWSOCKS_PASS=$(grep -Po '"'"key"'"\s*:\s*"\K([^"]*)' /etc/shadowsocks-libev/config.json | tr -d  "\n" | sed 's/-/+/g; s/_/\//g;')
	else
		SHADOWSOCKS_PASS=$(grep -Po '"'"65101"'":\s*"\K([^"]*)' /etc/shadowsocks-libev/manager.json | tr -d  "\n" | sed 's/-/+/g; s/_/\//g;')
	fi
fi
# Install shadowsocks config and add a shadowsocks by CPU
if [ "$update" = "0" ] || [ ! -f /etc/shadowsocks-libev/manager.json ]; then
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/shadowsocks-libev/manager.json ${VPSURL}${VPSPATH}/manager.json
	else
		cp ${DIR}/manager.json /etc/shadowsocks-libev/manager.json
	fi
	SHADOWSOCKS_PASS_JSON=$(echo $SHADOWSOCKS_PASS | sed 's/+/-/g; s/\//_/g;')
	if [ "$NBCPU" -gt "1" ]; then
		for i in $(seq 2 NBCPU); do
			sed -i '0,/65101/ s/        "65101.*/&\n&/' /etc/shadowsocks-libev/manager.json
		done
	fi
	#sed -i "s:MySecretKey:$SHADOWSOCKS_PASS_JSON:g" /etc/shadowsocks-libev/config.json
	sed -i "s:MySecretKey:$SHADOWSOCKS_PASS_JSON:g" /etc/shadowsocks-libev/manager.json
	[ "$(ip -6 a)" = "" ] && sed -i '/"\[::0\]"/d' /etc/shadowsocks-libev/manager.json
elif [ "$update" != "0" ] && [ -f /etc/shadowsocks-libev/manager.json ] && [ "$(grep -c '65101' /etc/shadowsocks-libev/manager.json | tr -d '\n')" != "$NBCPU" ] && [ -z "$(grep port_conf /etc/shadowsocks-libev/manager.json)" ]; then
	for i in $(seq 2 $NBCPU); do
		sed -i '0,/65101/ s/        "65101.*/&\n&/' /etc/shadowsocks-libev/manager.json
	done
	sed -i 's/       "65101.*"$/&,/' /etc/shadowsocks-libev/manager.json
fi
[ ! -f /etc/shadowsocks-libev/local.acl ] && touch /etc/shadowsocks-libev/local.acl
#sed -i 's:aes-256-cfb:chacha20:g' /etc/shadowsocks-libev/config.json
#sed -i 's:json:json --no-delay:g' /lib/systemd/system/shadowsocks-libev-server@.service
if [ "$LOCALFILES" = "no" ]; then
	wget -O /lib/systemd/system/shadowsocks-libev-manager@.service ${VPSURL}${VPSPATH}/shadowsocks-libev-manager@.service.in
else
	cp ${DIR}/shadowsocks-libev-manager@.service.in /lib/systemd/system/shadowsocks-libev-manager@.service
fi
if systemctl -q is-enabled shadowsocks-libev; then
	systemctl -q disable shadowsocks-libev
fi
[ -f /etc/shadowsocks-libev/config.json ] && systemctl disable shadowsocks-libev-server@config.service
systemctl enable shadowsocks-libev-manager@manager.service
if [ $NBCPU -gt 1 ]; then
	for i in $(seq 1 $NBCPU); do
		[ -f /etc/shadowsocks-libev/config$i.json ] && systemctl is-enabled shadowsocks-libev && systemctl disable shadowsocks-libev-server@config$i.service
	done
fi
if ! grep -q 'DefaultLimitNOFILE=65536' /etc/systemd/system.conf ; then
	echo 'DefaultLimitNOFILE=65536' >> /etc/systemd/system.conf
fi

if systemctl -q is-active shadowsocks-libev-manager@manager; then
	systemctl -q stop shadowsocks-libev-manager@manager > /dev/null 2>&1
fi

if [ "$LOCALFILES" = "no" ]; then
	wget -O /lib/systemd/system/omr-update.service ${VPSURL}${VPSPATH}/omr-update.service.in
	wget -O /usr/bin/omr-update ${VPSURL}${VPSPATH}/omr-update
	chmod 755 /usr/bin/omr-update
else
	cp ${DIR}/omr-update.service.in /lib/systemd/system/omr-update.service
	cp ${DIR}/omr-update /usr/bin/omr-update
	chmod 755 /usr/bin/omr-update
fi

# Install simple-obfs
if [ "$OBFS" = "yes" ]; then
	echo "Install OBFS"
	if [ "$SOURCES" = "yes" ]; then
		rm -rf /tmp/simple-obfs
		cd /tmp
                rm -f /var/lib/dpkg/lock
                rm -f /var/lib/dpkg/lock-frontend
                apt-get install -y --no-install-recommends build-essential autoconf libtool libssl-dev libpcre3-dev libev-dev asciidoc xmlto automake git ca-certificates
		git clone https://github.com/shadowsocks/simple-obfs.git /tmp/simple-obfs
		cd /tmp/simple-obfs
		git checkout ${OBFS_VERSION}
		git submodule update --init --recursive
		./autogen.sh
		./configure && make
		make install
		cd /tmp
		rm -rf /tmp/simple-obfs
	else
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
            install_omr_package "omr-simple-obfs" "${OBFS_BINARY_VERSION}" "$OMR_SIMPLE_OBFS_DEB_FILE" "$OMR_SIMPLE_OBFS_DEB_URL" "-o" "Dpkg::Options::=--force-overwrite"
	fi
	#sed -i 's%"mptcp": true%"mptcp": true,\n"plugin": "/usr/local/bin/obfs-server",\n"plugin_opts": "obfs=http;mptcp;fast-open;t=400"%' /etc/shadowsocks-libev/config.json
fi

# Install v2ray-plugin
if [ "$V2RAY_PLUGIN" = "yes" ]; then
	echo "Install v2ray plugin"
	if [ "$SOURCES" = "yes" ]; then
		rm -rf /tmp/v2ray-plugin-linux-amd64-${V2RAY_PLUGIN_VERSION}.tar.gz
		#wget -O /tmp/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz https://github.com/shadowsocks/v2ray-plugin/releases/download/${V2RAY_PLUGIN_VERSION}/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz
		#wget -O /tmp/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz ${VPSURL}${VPSPATH}/bin/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz
		wget -O /tmp/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz https://github.com/teddysun/v2ray-plugin/releases/download/v${V2RAY_PLUGIN_VERSION}/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz
		cd /tmp
		tar xzvf v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz
		cp -f v2ray-plugin_linux_amd64 /usr/local/bin/v2ray-plugin
		cd /tmp
		rm -rf /tmp/v2ray-plugin_linux_amd64
		rm -rf /tmp/v2ray-plugin-linux-amd64-${V2RAY_PLUGIN_VERSION}.tar.gz
	
		#rm -rf /tmp/v2ray-plugin
		#cd /tmp
		#rm -f /var/lib/dpkg/lock
		#apt-get install -y --no-install-recommends git ca-certificates golang-go
		#git clone https://github.com/shadowsocks/v2ray-plugin.git /tmp/v2ray-plugin
		#cd /tmp/v2ray-plugin
		#git checkout ${V2RAY_PLUGIN_VERSION}
		#git submodule update --init --recursive
		#CGO_ENABLED=0 go build -o v2ray-plugin
		#cp v2ray-plugin /usr/local/bin/v2ray-plugin
		#cd /tmp
		#rm -rf /tmp/simple-obfs
	else
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
                install_omr_package "v2ray-plugin" "${V2RAY_PLUGIN_VERSION}" "$V2RAY_PLUGIN_DEB_FILE" "$V2RAY_PLUGIN_DEB_URL"
	fi
fi

if [ "$OBFS" = "no" ] && [ "$V2RAY_PLUGIN" = "no" ]; then
	sed -i -e '/plugin/d' -e 's/,,//' /etc/shadowsocks-libev/config.json
fi

if systemctl -q is-active v2ray.service; then
	systemctl -q stop v2ray > /dev/null 2>&1
	systemctl -q disable v2ray > /dev/null 2>&1
fi

if [ "$V2RAY" = "yes" ]; then
	#apt-get -y -o Dpkg::Options::="--force-overwrite" install v2ray
	if [ "$SOURCES" = "yes" ]; then
		wget -O /tmp/v2ray-${V2RAY_VERSION}-amd64.deb ${VPSURL}/debian/v2ray-${V2RAY_VERSION}-amd64.deb
		dpkg --force-all -i -B /tmp/v2ray-${V2RAY_VERSION}-amd64.deb
		rm -f /tmp/v2ray-${V2RAY_VERSION}-amd64.deb
	else
                install_omr_package "v2ray" "${V2RAY_VERSION}" "$V2RAY_DEB_FILE" "$V2RAY_DEB_URL" "-o" "Dpkg::Options::=--force-confold" "-o" "Dpkg::Options::=--force-confdef" "-o" "Dpkg::Options::=--force-overwrite"
	fi
	if [ ! -f /etc/v2ray/v2ray-server.json ]; then
		wget -O /etc/v2ray/v2ray-server.json ${VPSURL}${VPSPATH}/v2ray-server.json
		sed -i "s:V2RAY_UUID:$V2RAY_UUID:g" /etc/v2ray/v2ray-server.json
	fi
	rm -f /etc/v2ray/config.json
	ln -s /etc/v2ray/v2ray-server.json /etc/v2ray/config.json
	if [ -f /etc/systemd/system/v2ray.service.dpkg-dist ]; then
		mv -f /etc/systemd/system/v2ray.service.dpkg-dist /etc/systemd/system/v2ray.service
	fi
	systemctl daemon-reload
	systemctl enable v2ray.service
	if [ "$UPSTREAM" = "yes" ]; then
		mptcpize enable v2ray
	fi
fi

if systemctl -q is-active mlvpn@mlvpn0.service; then
	systemctl -q stop mlvpn@mlvpn0 > /dev/null 2>&1
	systemctl -q disable mlvpn@mlvpn0 > /dev/null 2>&1
fi
echo "install mlvpn"
# Install MLVPN
if [ "$MLVPN" = "yes" ]; then
	echo 'Install MLVPN'
	mlvpnupdate="0"
	if [ -f /etc/mlvpn/mlvpn0.conf ]; then
		mlvpnupdate="1"
	fi
	mkdir -p /etc/mlvpn
	if [ "$SOURCES" = "yes" ]; then
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		apt-get -y install build-essential pkg-config autoconf automake libpcap-dev unzip git
		rm -rf /tmp/mlvpn
		cd /tmp
		#git clone https://github.com/markfoodyburton/MLVPN.git /tmp/mlvpn
		#git clone https://github.com/flohoff/MLVPN.git /tmp/mlvpn
		git clone https://github.com/zehome/MLVPN.git /tmp/mlvpn
		#git clone https://github.com/link4all/MLVPN.git /tmp/mlvpn
		cd /tmp/mlvpn
		git checkout ${MLVPN_VERSION}
		./autogen.sh
		./configure --sysconfdir=/etc
		make
		make install
		cd /tmp
		rm -rf /tmp/mlvpn
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /lib/systemd/network/mlvpn.network ${VPSURL}${VPSPATH}/mlvpn.network
			wget -O /lib/systemd/system/mlvpn@.service ${VPSURL}${VPSPATH}/mlvpn@.service.in
		else
			cp ${DIR}/mlvpn.network /lib/systemd/network/mlvpn.network
			cp ${DIR}/mlvpn@.service.in /lib/systemd/system/mlvpn@.service
		fi
		if [ "$mlvpnupdate" = "0" ]; then
			if [ "$LOCALFILES" = "no" ]; then
				wget -O /etc/mlvpn/mlvpn0.conf ${VPSURL}${VPSPATH}/mlvpn0.conf
			else
				cp ${DIR}/mlvpn0.conf /etc/mlvpn/mlvpn0.conf
			fi
		fi
	else
                install_omr_package "omr-mlvpn" "${MLVPN_BINARY_VERSION}" "$OMR_MLVPN_DEB_FILE" "$OMR_MLVPN_DEB_URL" "-o" "Dpkg::Options::=--force-confold" "-o" "Dpkg::Options::=--force-confdef"
	fi
	if [ "$mlvpnupdate" = "0" ]; then
		sed -i "s:MLVPN_PASS:$MLVPN_PASS:" /etc/mlvpn/mlvpn0.conf
	fi
	chmod 0600 /etc/mlvpn/mlvpn0.conf
	adduser --quiet --system --home /var/opt/mlvpn --shell /usr/sbin/nologin mlvpn
	mkdir -p /var/opt/mlvpn
	usermod -d /var/opt/mlvpn mlvpn
	chown mlvpn /var/opt/mlvpn
	systemctl enable mlvpn@mlvpn0.service
	systemctl enable systemd-networkd.service
	echo "install mlvpn done"
fi
if systemctl -q is-active ubond@ubond0.service; then
	systemctl -q stop ubond@ubond0 > /dev/null 2>&1
	systemctl -q disable ubond@ubond0 > /dev/null 2>&1
fi
echo "install ubond"
# Install UBOND
if [ "$UBOND" = "yes" ]; then
	echo 'Install UBOND'
	ubondupdate="0"
	if [ -f /etc/ubond/ubond0.conf ]; then
		ubondupdate="1"
	fi
#	if [ "$SOURCES" = "yes" ]; then
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		apt-get -y install build-essential pkg-config autoconf automake libpcap-dev unzip git
		rm -rf /tmp/ubond
		cd /tmp
		git clone https://github.com/markfoodyburton/ubond.git /tmp/ubond
		cd /tmp/ubond
		git checkout ${UBOND_VERSION}
		./autogen.sh
		./configure --sysconfdir=/etc
		make
		make install
		cd /tmp
		rm -rf /tmp/ubond
#	else
#		apt-get -y -o Dpkg::Options::="--force-overwrite" install ubond
#	fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /lib/systemd/network/ubond.network ${VPSURL}${VPSPATH}/ubond.network
		wget -O /lib/systemd/system/ubond@.service ${VPSURL}${VPSPATH}/ubond@.service.in
	else
		cp ${DIR}/ubond.network /lib/systemd/network/ubond.network
		cp ${DIR}/ubond@.service.in /lib/systemd/system/ubond@.service
	fi
	mkdir -p /etc/ubond
	if [ "$ubondupdate" = "0" ]; then
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /etc/ubond/ubond0.conf ${VPSURL}${VPSPATH}/ubond0.conf
		else
			cp ${DIR}/ubond0.conf /etc/ubond/ubond0.conf
		fi
		sed -i "s:UBOND_PASS:$UBOND_PASS:" /etc/ubond/ubond0.conf
	fi
	chmod 0600 /etc/ubond/ubond0.conf
	adduser --quiet --system --home /var/opt/ubond --shell /usr/sbin/nologin ubond
	mkdir -p /var/opt/ubond
	usermod -d /var/opt/ubond ubond
	chown ubond /var/opt/ubond
	systemctl enable ubond@ubond0.service
	systemctl enable systemd-networkd.service
	echo "install ubond done"
fi

if systemctl -q is-active wg-quick@wg0.service; then
	systemctl -q stop wg-quick@wg0 > /dev/null 2>&1
	systemctl -q disable wg-quick@wg0 > /dev/null 2>&1
fi

if [ "$WIREGUARD" = "yes" ]; then
	echo "Install WireGuard"
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	apt-get -y install wireguard-tools --no-install-recommends
	if [ ! -f /etc/wireguard/wg0.conf ]; then
		cd /etc/wireguard
		umask 077; wg genkey | tee vpn-server-private.key | wg pubkey > vpn-server-public.key
		cat > /etc/wireguard/wg0.conf <<-EOF
		[Interface]
		PrivateKey = $(cat /etc/wireguard/vpn-server-private.key | tr -d "\n")
		ListenPort = 65311
		Address = 10.255.247.1/24
		SaveConfig = true
		EOF
	fi
	systemctl enable wg-quick@wg0
	if [ ! -f /etc/wireguard/client-wg0.conf ]; then
		cd /etc/wireguard
		umask 077; wg genkey | tee vpn-client-private.key | wg pubkey > vpn-client-public.key
		cat > /etc/wireguard/client-wg0.conf <<-EOF
		[Interface]
		PrivateKey = $(cat /etc/wireguard/vpn-server-private.key | tr -d "\n")
		ListenPort = 65312
		Address = 10.255.246.1/24
		SaveConfig = true
		
		[Peer]
		PublicKey = $(cat /etc/wireguard/vpn-client-public.key | tr -d "\n")
		AllowedIPs = 10.255.246.2/32
		EOF
	fi
	if [ ! -f /root/wireguard-client.conf ]; then
		cat > /root/wireguard-client.conf <<-EOF
		[Interface]
		Address = 10.255.246.2/24
		PrivateKey = $(cat /etc/wireguard/vpn-client-private.key | tr -d "\n")
		
		[Peer]
		PublicKey = $(cat /etc/wireguard/vpn-server-public.key | tr -d "\n")
		Endpoint = ${VPS_PUBLIC_IP}:65312
		AllowedIPs = 0.0.0.0/0, ::/0, 192.168.100.0/24
		EOF
	fi
	systemctl enable wg-quick@client-wg0
	echo "Install wireguard done"
fi

if systemctl -q is-active openvpn-server@tun0.service; then
	systemctl -q stop openvpn-server@tun0 > /dev/null 2>&1
	systemctl -q disable openvpn-server@tun0 > /dev/null 2>&1
fi
if [ "$OPENVPN" = "yes" ]; then
	echo "Install OpenVPN"
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
        install_omr_package "openvpn" "$OPENVPN_BINARY_VERSION" "$OPENVPN_DEB_FILE" "$OPENVPN_DEB_URL" "--allow-downgrades"
        apt-get -y install easy-rsa
	#wget -O /lib/systemd/network/openvpn.network ${VPSURL}${VPSPATH}/openvpn.network
	rm -f /lib/systemd/network/openvpn.network
	#if [ ! -f "/etc/openvpn/server/static.key" ]; then
	#	wget -O /etc/openvpn/tun0.conf ${VPSURL}${VPSPATH}/openvpn-tun0.conf
	#	cd /etc/openvpn/server
	#	openvpn --genkey --secret static.key
	#fi
	if [ -f "/etc/openvpn/server/server.crt" ]; then
		if [ ! -d /etc/openvpn/ca ]; then
			make-cadir /etc/openvpn/ca
		fi
		mkdir -p /etc/openvpn/ca/pki/private /etc/openvpn/ca/pki/issued
		mv /etc/openvpn/server/ca.crt /etc/openvpn/ca/pki/ca.crt
		mv /etc/openvpn/server/ca.key /etc/openvpn/ca/pki/private/ca.key
		mv /etc/openvpn/server/server.crt /etc/openvpn/ca/pki/issued/server.crt
		mv /etc/openvpn/server/server.key /etc/openvpn/ca/pki/private/server.key
		mv /etc/openvpn/server/crl.pem /etc/openvpn/ca/pki/crl.pem
		mv /etc/openvpn/client/client.crt /etc/openvpn/ca/pki/issued/openmptcprouter.crt
		mv /etc/openvpn/client/client.key /etc/openvpn/ca/pki/private/openmptcprouter.key
	fi
	if [ ! -f "/etc/openvpn/ca/pki/issued/server.crt" ]; then
		if [ ! -d /etc/openvpn/ca ]; then
			make-cadir /etc/openvpn/ca
		fi
		cd /etc/openvpn/ca
		./easyrsa init-pki 2>&1 >/dev/null
		./easyrsa --batch build-ca nopass
		EASYRSA_CERT_EXPIRE=3650 ./easyrsa build-server-full server nopass
		EASYRSA_CERT_EXPIRE=3650 ./easyrsa build-client-full "openmptcprouter" nopass
		EASYRSA_CRL_DAYS=3650 ./easyrsa gen-crl
	fi
	if [ ! -f "/etc/openvpn/ca/pki/issued/openmptcprouter.crt" ]; then
		mv /etc/openvpn/ca/pki/issued/client.crt /etc/openvpn/ca/pki/issued/openmptcprouter.crt
		mv /etc/openvpn/ca/pki/private/client.key /etc/openvpn/ca/pki/private/openmptcprouter.key
	fi
	if [ ! -f "/etc/openvpn/server/dh2048.pem" ]; then
		openssl dhparam -out /etc/openvpn/server/dh2048.pem 2048
	fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/openvpn/tun0.conf ${VPSURL}${VPSPATH}/openvpn-tun0.conf
		wget -O /etc/openvpn/tun1.conf ${VPSURL}${VPSPATH}/openvpn-tun1.conf
		wget -O /etc/openvpn/bonding1.conf ${VPSURL}${VPSPATH}/openvpn-bonding1.conf
		wget -O /etc/openvpn/bonding2.conf ${VPSURL}${VPSPATH}/openvpn-bonding2.conf
		wget -O /etc/openvpn/bonding3.conf ${VPSURL}${VPSPATH}/openvpn-bonding3.conf
		wget -O /etc/openvpn/bonding4.conf ${VPSURL}${VPSPATH}/openvpn-bonding4.conf
		wget -O /etc/openvpn/bonding5.conf ${VPSURL}${VPSPATH}/openvpn-bonding5.conf
		wget -O /etc/openvpn/bonding6.conf ${VPSURL}${VPSPATH}/openvpn-bonding6.conf
		wget -O /etc/openvpn/bonding7.conf ${VPSURL}${VPSPATH}/openvpn-bonding7.conf
		wget -O /etc/openvpn/bonding8.conf ${VPSURL}${VPSPATH}/openvpn-bonding8.conf
	else
		cp ${DIR}/openvpn-tun0.conf /etc/openvpn/tun0.conf
		cp ${DIR}/openvpn-tun1.conf /etc/openvpn/tun1.conf
		cp ${DIR}/openvpn-bonding1.conf /etc/openvpn/bonding1.conf
		cp ${DIR}/openvpn-bonding2.conf /etc/openvpn/bonding2.conf
		cp ${DIR}/openvpn-bonding3.conf /etc/openvpn/bonding3.conf
		cp ${DIR}/openvpn-bonding4.conf /etc/openvpn/bonding4.conf
		cp ${DIR}/openvpn-bonding5.conf /etc/openvpn/bonding5.conf
		cp ${DIR}/openvpn-bonding6.conf /etc/openvpn/bonding6.conf
		cp ${DIR}/openvpn-bonding7.conf /etc/openvpn/bonding7.conf
		cp ${DIR}/openvpn-bonding8.conf /etc/openvpn/bonding8.conf
	fi
	mkdir -p /etc/openvpn/ccd
	systemctl enable openvpn@tun0.service
	systemctl enable openvpn@tun1.service
	if [ "$UPSTREAM" = "yes" ]; then
		mptcpize enable openvpn@tun0
	fi
	systemctl enable openvpn@bonding1.service
	systemctl enable openvpn@bonding2.service
	systemctl enable openvpn@bonding3.service
	systemctl enable openvpn@bonding4.service
	systemctl enable openvpn@bonding5.service
	systemctl enable openvpn@bonding6.service
	systemctl enable openvpn@bonding7.service
	systemctl enable openvpn@bonding8.service
fi

echo 'Glorytun UDP'
# Install Glorytun UDP
if systemctl -q is-active glorytun-udp@tun0.service; then
	systemctl -q stop 'glorytun-udp@*' > /dev/null 2>&1
fi
if [ "$SOURCES" = "yes" ]; then
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	rm -f /usr/bin/glorytun
	apt-get install -y --no-install-recommends build-essential git ca-certificates meson pkg-config
	rm -rf /tmp/glorytun-udp
	cd /tmp
	git clone https://github.com/angt/glorytun.git /tmp/glorytun-udp
	cd /tmp/glorytun-udp
	git checkout ${GLORYTUN_UDP_VERSION}
	git submodule update --init --recursive
	meson build
	ninja -C build install
	sed -i 's:EmitDNS=yes:EmitDNS=no:g' /lib/systemd/network/glorytun.network
	rm /lib/systemd/system/glorytun*
	rm /lib/systemd/network/glorytun*
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /usr/local/bin/glorytun-udp-run ${VPSURL}${VPSPATH}/glorytun-udp-run
	else
		cp ${DIR}/glorytun-udp-run /usr/local/bin/glorytun-udp-run
	fi
	chmod 755 /usr/local/bin/glorytun-udp-run
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /lib/systemd/system/glorytun-udp@.service ${VPSURL}${VPSPATH}/glorytun-udp%40.service.in
	else
		cp ${DIR}/glorytun-udp@.service.in /lib/systemd/system/glorytun-udp@.service
	fi
	#wget -O /lib/systemd/network/glorytun-udp.network ${VPSURL}${VPSPATH}/glorytun-udp.network
	rm -f /lib/systemd/network/glorytun-udp.network
	mkdir -p /etc/glorytun-udp
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/glorytun-udp/post.sh ${VPSURL}${VPSPATH}/glorytun-udp-post.sh
		wget -O /etc/glorytun-udp/tun0 ${VPSURL}${VPSPATH}/tun0.glorytun-udp
	else
		cp ${DIR}/glorytun-udp-post.sh /etc/glorytun-udp/post.sh
		cp ${DIR}/tun0.glorytun-udp /etc/glorytun-udp/tun0
	fi
	chmod 755 /etc/glorytun-udp/post.sh
	if [ "$update" = "0" ] || [ ! -f /etc/glorytun-udp/tun0.key ]; then
		echo "$GLORYTUN_PASS" > /etc/glorytun-udp/tun0.key
	elif [ ! -f /etc/glorytun-udp/tun0.key ] && [ -f /etc/glorytun-tcp/tun0.key ]; then
		cp /etc/glorytun-tcp/tun0.key /etc/glorytun-udp/tun0.key
	fi
	systemctl enable glorytun-udp@tun0.service
	systemctl enable systemd-networkd.service
	cd /tmp
	rm -rf /tmp/glorytun-udp
else
	rm -f /usr/local/bin/glorytun
        install_omr_package "omr-glorytun" "${GLORYTUN_UDP_BINARY_VERSION}" "$OMR_GLORYTUN_DEB_FILE" "$OMR_GLORYTUN_DEB_URL" "-o" "Dpkg::Options::=--force-confdef" "-o" "Dpkg::Options::=--force-confold" "-o" "Dpkg::Options::=--force-overwrite" "--reinstall"
	GLORYTUN_PASS="$(cat /etc/glorytun-udp/tun0.key | tr -d '\n')"
fi
[ "$(ip -6 a)" != "" ] && sed -i 's/0.0.0.0/::/g' /etc/glorytun-udp/tun0


# Add chrony for time sync
apt-get install -y chrony
systemctl enable chrony

if [ "$DSVPN" = "yes" ]; then
	echo 'A Dead Simple VPN'
	# Install A Dead Simple VPN
	if systemctl -q is-active dsvpn-server.service; then
		systemctl -q disable dsvpn-server > /dev/null 2>&1
		systemctl -q stop dsvpn-server > /dev/null 2>&1
	fi
	if [ "$SOURCES" = "yes" ]; then
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		apt-get install -y --no-install-recommends build-essential git ca-certificates
		rm -rf /tmp/dsvpn
		cd /tmp
		git clone https://github.com/jedisct1/dsvpn.git /tmp/dsvpn
		cd /tmp/dsvpn
		git checkout ${DSVPN_VERSION}
		wget https://github.com/Ysurac/openmptcprouter-feeds/raw/develop/dsvpn/patches/nofirewall.patch
		patch -p1 < nofirewall.patch
		make CFLAGS='-DNO_DEFAULT_ROUTES -DNO_DEFAULT_FIREWALL'
		make install
		rm -f /lib/systemd/system/dsvpn/*
		wget -O /usr/local/bin/dsvpn-run ${VPSURL}${VPSPATH}/dsvpn-run
		chmod 755 /usr/local/bin/dsvpn-run
		wget -O /lib/systemd/system/dsvpn-server@.service ${VPSURL}${VPSPATH}/dsvpn-server%40.service.in
		mkdir -p /etc/dsvpn
		wget -O /etc/dsvpn/dsvpn0 ${VPSURL}${VPSPATH}/dsvpn0-config
		if [ -f /etc/dsvpn/dsvpn.key ]; then
			mv /etc/dsvpn/dsvpn.key /etc/dsvpn/dsvpn0.key
		fi
		if [ "$update" = "0" ] || [ ! -f /etc/dsvpn/dsvpn0.key ]; then
			echo "$DSVPN_PASS" > /etc/dsvpn/dsvpn0.key
		fi
		systemctl enable dsvpn-server@dsvpn0.service
		cd /tmp
		rm -rf /tmp/dsvpn
	else
                install_omr_package "omr-dsvpn" "${DSVPN_BINARY_VERSION}" "$OMR_DSVPN_DEB_FILE" "$OMR_DSVPN_DEB_URL" "-o" "Dpkg::Options::=--force-confdef" "-o" "Dpkg::Options::=--force-confold" "-o" "Dpkg::Options::=--force-overwrite"
		DSVPN_PASS=$(cat /etc/dsvpn/dsvpn0.key | tr -d "\n")
	fi
	if [ "$UPSTREAM" = "yes" ]; then
		mptcpize enable dsvpn-server@dsvpn0
	fi
fi

# Install Glorytun TCP
if systemctl -q is-active glorytun-tcp@tun0.service; then
	systemctl -q stop 'glorytun-tcp@*' > /dev/null 2>&1
fi
if [ "$SOURCES" = "yes" ]; then
        apt-get -y install libsodium-dev
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	rm -f /usr/bin/glorytun-tcp
	apt-get -y install build-essential pkg-config autoconf automake
	rm -rf /tmp/glorytun-0.0.35
	cd /tmp
	if [ "$UPSTREAM" = "yes" ]; then
		wget -O /tmp/glorytun-0.0.35.tar.gz https://github.com/Ysurac/glorytun/archive/refs/heads/tcp.tar.gz
	else
		wget -O /tmp/glorytun-0.0.35.tar.gz http://github.com/angt/glorytun/releases/download/v0.0.35/glorytun-0.0.35.tar.gz
	fi
	tar xzf glorytun-0.0.35.tar.gz
	if [ "$UPSTREAM" = "yes" ]; then
		mv /tmp/glorytun-tcp /tmp/glorytun-0.0.35
	fi
	cd glorytun-0.0.35
	./autogen.sh
	./configure
	make
	cp glorytun /usr/local/bin/glorytun-tcp
	wget -O /usr/local/bin/glorytun-tcp-run ${VPSURL}${VPSPATH}/glorytun-tcp-run
	chmod 755 /usr/local/bin/glorytun-tcp-run
	wget -O /lib/systemd/system/glorytun-tcp@.service ${VPSURL}${VPSPATH}/glorytun-tcp%40.service.in
	#wget -O /lib/systemd/network/glorytun-tcp.network ${VPSURL}${VPSPATH}/glorytun.network
	rm -f /lib/systemd/network/glorytun-tcp.network
	mkdir -p /etc/glorytun-tcp
	wget -O /etc/glorytun-tcp/post.sh ${VPSURL}${VPSPATH}/glorytun-tcp-post.sh
	chmod 755 /etc/glorytun-tcp/post.sh
	wget -O /etc/glorytun-tcp/tun0 ${VPSURL}${VPSPATH}/tun0.glorytun
	if [ "$update" = "0" ]; then
		echo "$GLORYTUN_PASS" > /etc/glorytun-tcp/tun0.key
	fi
	systemctl enable glorytun-tcp@tun0.service
	#systemctl enable systemd-networkd.service
	cd /tmp
	rm -rf /tmp/glorytun-0.0.35
else
	rm -f /usr/local/bin/glorytun-tcp
        install_omr_package "omr-glorytun-tcp" "${GLORYTUN_TCP_BINARY_VERSION}" "$OMR_GLORYTUN_TCP_DEB_FILE" "$OMR_GLORYTUN_TCP_DEB_URL" "-o" "Dpkg::Options::=--force-confdef" "-o" "Dpkg::Options::=--force-confold" "-o" "Dpkg::Options::=--force-overwrite" "--reinstall"
fi
[ "$(ip -6 a)" != "" ] && sed -i 's/0.0.0.0/::/g' /etc/glorytun-tcp/tun0


# Load tun module at boot time
if ! grep -q tun /etc/modules ; then
	echo tun >> /etc/modules
fi

# Add multipath utility
if [ "$LOCALFILES" = "no" ]; then
	wget -O /usr/local/bin/multipath ${VPSURL}${VPSPATH}/multipath
else
	cp ${DIR}/multipath /usr/local/bin/multipath
fi
chmod 755 /usr/local/bin/multipath

# Add omr-test-speed utility
if [ "$LOCALFILES" = "no" ]; then
	wget -O /usr/local/bin/omr-test-speed ${VPSURL}${VPSPATH}/omr-test-speed
else
	cp ${DIR}/omr-test-speed /usr/local/bin/omr-test-speed
fi
chmod 755 /usr/local/bin/omr-test-speed

# Add OpenMPTCProuter service
if [ "$LOCALFILES" = "no" ]; then
	wget -O /usr/local/bin/omr-service ${VPSURL}${VPSPATH}/omr-service
	wget -O /lib/systemd/system/omr.service ${VPSURL}${VPSPATH}/omr.service.in
	wget -O /usr/local/bin/omr-6in4-run ${VPSURL}${VPSPATH}/omr-6in4-run
	wget -O /lib/systemd/system/omr6in4@.service ${VPSURL}${VPSPATH}/omr6in4%40.service.in
else
	cp ${DIR}/omr-service /usr/local/bin/omr-service
	cp ${DIR}/omr.service.in /lib/systemd/system/omr.service
	cp ${DIR}/omr-6in4-run /usr/local/bin/omr-6in4-run
	cp ${DIR}/omr6in4@.service.in /lib/systemd/system/omr6in4@.service
fi
chmod 755 /usr/local/bin/omr-service
chmod 755 /usr/local/bin/omr-6in4-run
if systemctl -q is-active omr-6in4.service; then
	systemctl -q stop omr-6in4 > /dev/null 2>&1
	systemctl -q disable omr-6in4 > /dev/null 2>&1
fi
systemctl enable omr6in4@user0.service
systemctl enable omr.service

# Change SSH port to 65222
sed -i 's:#Port 22:Port 65222:g' /etc/ssh/sshd_config
sed -i 's:Port 22:Port 65222:g' /etc/ssh/sshd_config

# Remove Bind9 if available
#systemctl -q disable bind9

# Remove fail2ban if available
#systemctl -q disable fail2ban

if [ "$update" = "0" ]; then
	# Install and configure the firewall using shorewall
	apt-get -y install shorewall shorewall6
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/shorewall/openmptcprouter-shorewall.tar.gz ${VPSURL}${VPSPATH}/openmptcprouter-shorewall.tar.gz
	else
		cp ${DIR}/openmptcprouter-shorewall.tar.gz /etc/shorewall/openmptcprouter-shorewall.tar.gz
	fi
	tar xzf /etc/shorewall/openmptcprouter-shorewall.tar.gz -C /etc/shorewall
	rm /etc/shorewall/openmptcprouter-shorewall.tar.gz
	sed -i "s:eth0:$INTERFACE:g" /etc/shorewall/*
	systemctl enable shorewall
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/shorewall6/openmptcprouter-shorewall6.tar.gz ${VPSURL}${VPSPATH}/openmptcprouter-shorewall6.tar.gz
	else
		cp ${DIR}/openmptcprouter-shorewall6.tar.gz /etc/shorewall6/openmptcprouter-shorewall6.tar.gz
	fi
	tar xzf /etc/shorewall6/openmptcprouter-shorewall6.tar.gz -C /etc/shorewall6
	rm /etc/shorewall6/openmptcprouter-shorewall6.tar.gz
	sed -i "s:eth0:$INTERFACE:g" /etc/shorewall6/*
	systemctl enable shorewall6
else
	# Update only needed firewall files
	if [ "$LOCALFILES" = "no" ]; then
		mkdir -p ${DIR}
		wget -O ${DIR}/openmptcprouter-shorewall.tar.gz ${VPSURL}${VPSPATH}/openmptcprouter-shorewall.tar.gz
		wget -O ${DIR}/openmptcprouter-shorewall6.tar.gz ${VPSURL}${VPSPATH}/openmptcprouter-shorewall6.tar.gz
		mkdir -p ${DIR}/shorewall4
		tar xzvf ${DIR}/openmptcprouter-shorewall.tar.gz -C ${DIR}/shorewall4
		mkdir -p ${DIR}/shorewall6
		tar xzvf ${DIR}/openmptcprouter-shorewall6.tar.gz -C ${DIR}/shorewall6
	fi
	cp ${DIR}/shorewall4/interfaces /etc/shorewall/interfaces
	cp ${DIR}/shorewall4/snat /etc/shorewall/snat
	cp ${DIR}/shorewall4/stoppedrules /etc/shorewall/stoppedrules
	cp ${DIR}/shorewall4/tcinterfaces /etc/shorewall/tcinterfaces
	cp ${DIR}/shorewall4/shorewall.conf /etc/shorewall/shorewall.conf
	cp ${DIR}/shorewall4/policy /etc/shorewall/policy
	cp ${DIR}/shorewall4/params /etc/shorewall/params
	cp ${DIR}/shorewall4/zones /etc/shorewall/zones
	#cp ${DIR}/shorewall4/params.vpn /etc/shorewall/params.vpn
	#cp ${DIR}/shorewall4/params.net /etc/shorewall/params.net
	cp ${DIR}/shorewall6/params /etc/shorewall6/params
	#cp ${DIR}/shorewall6/params.net /etc/shorewall6/params.net
	#cp ${DIR}/shorewall6/params.vpn /etc/shorewall6/params.vpn
	cp ${DIR}/shorewall6/interfaces /etc/shorewall6/interfaces
	cp ${DIR}/shorewall6/stoppedrules /etc/shorewall6/stoppedrules
	cp ${DIR}/shorewall6/snat /etc/shorewall6/snat
	sed -i "s:eth0:$INTERFACE:g" /etc/shorewall/*
	sed -i 's/^.*#DNAT/#DNAT/g' /etc/shorewall/rules
	sed -i 's:10.0.0.2:$OMR_ADDR:g' /etc/shorewall/rules
	sed -i "s:eth0:$INTERFACE:g" /etc/shorewall6/*
	if [ "$LOCALFILES" = "no" ]; then
		rm -rf ${DIR}/shorewall4
		rm -rf ${DIR}/shorewall6
		rm -f ${DIR}/openmptcprouter-shorewall.tar.gz
		rm -f ${DIR}/openmptcprouter-shorewall6.tar.gz
	fi
fi
[ -z "$(grep nf_conntrack_sip /etc/modprobe.d/blacklist.conf)" ] && echo 'blacklist nf_conntrack_sip' >> /etc/modprobe.d/blacklist.conf
if [ "$(ip r | awk '/default/&&/src/ {print $7}')" != "" ] && [ "$(ip r | awk '/default/&&/src/ {print $7}')" != "dhcp" ]; then
	sed -i "s/MASQUERADE/SNAT($(ip r | awk '/default/&&/src/ {print $7}'))/" /etc/shorewall/snat
fi


if [ "$TLS" = "yes" ]; then
	VPS_CERT=0
	apt-get -y install socat
	if [ "$VPS_DOMAIN" != "" ] && [ "$(getent hosts $VPS_DOMAIN | awk '{ print $1; exit }')" != "" ] && [ "$(ping -c 1 -w 1 $VPS_DOMAIN)" ]; then
		if [ ! -f "/root/.acme.sh/$VPS_DOMAIN/$VPS_DOMAIN.cer" ]; then
			echo "Generate certificate for V2Ray"
			set +e
			#[ "$(shorewall  status | grep stopped)" = "" ] && shorewall open all all tcp 443
			curl https://get.acme.sh | sh
			systemctl -q restart shorewall
			~/.acme.sh/acme.sh --force --alpn --issue -d $VPS_DOMAIN --pre-hook 'shorewall open all all tcp 443 2>&1 >/dev/null' --post-hook 'shorewall close all all tcp 443 2>&1 >/dev/null' 2>&1 >/dev/null
			set -e
			if [ -f /root/.acme.sh/$VPS_DOMAIN/$VPS_DOMAIN.cer ]; then
				rm -f /etc/openmptcprouter-vps-admin/cert.pem
				ln -s /root/.acme.sh/$VPS_DOMAIN/$VPS_DOMAIN.cer /etc/openmptcprouter-vps-admin/cert.pem
				rm -f /etc/openmptcprouter-vps-admin/key.pem
				ln -s /root/.acme.sh/$VPS_DOMAIN/$VPS_DOMAIN.key /etc/openmptcprouter-vps-admin/key.pem
			fi
#			mkdir -p /etc/ssl/v2ray
#			ln -f -s /root/.acme.sh/$reverse/$reverse.key /etc/ssl/v2ray/omr.key
#			ln -f -s /root/.acme.sh/$reverse/fullchain.cer /etc/ssl/v2ray/omr.cer
			#[ "$(shorewall  status | grep stopped)" = "" ] && shorewall close all all tcp 443
		fi
		VPS_CERT=1
	else
		echo "No working domain detected..."
	fi
fi

if [ "$SPEEDTEST" = "yes" ]; then
	mkdir -p /usr/share/omr-server/speedtest
	if [ ! -f /usr/share/omr-server/speedtest/test.img ] && [ "$(df /usr/share/omr-server/speedtest | awk '/[0-9]%/{print $(NF-2)}')" -gt 2000000 ]; then
		echo "Generate speedtest image..."
		dd if=/dev/urandom of=/usr/share/omr-server/speedtest/test.img count=1024 bs=1048576
		echo "Done"
	fi
fi

# Add OpenMPTCProuter VPS script version to /etc/motd
if [ -f /etc/motd.head ]; then
	if grep --quiet 'OpenMPTCProuter VPS' /etc/motd.head; then
		sed -i "s:< OpenMPTCProuter VPS [0-9]*\.[0-9]*\(\|-test[0-9]*\) >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd.head
		sed -i "s:< OpenMPTCProuter VPS \$OMR_VERSION >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd.head
	else
		echo "< OpenMPTCProuter VPS $OMR_VERSION >" >> /etc/motd.head
	fi
elif [ -f /etc/motd ]; then
	if grep --quiet 'OpenMPTCProuter VPS' /etc/motd; then
		sed -i "s:< OpenMPTCProuter VPS [0-9]*\.[0-9]*\(\|-test[0-9]*\) >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd
		sed -i "s:< OpenMPTCProuter VPS \$OMR_VERSION >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd
	else
		echo "< OpenMPTCProuter VPS $OMR_VERSION >" >> /etc/motd
	fi
else
	echo "< OpenMPTCProuter VPS $OMR_VERSION >" > /etc/motd
fi

if [ "$SOURCES" != "yes" ]; then
        install_omr_package "omr-server" "${OMR_VERSION}" "$OMR_SERVER_DEB_FILE" "$OMR_SERVER_DEB_URL" >/dev/null 2>&1 || true
	rm -f /etc/openmtpcprouter-vps-admin/update-bin
fi

if [ "$update" = "0" ]; then
	# Display important info
	echo '===================================================================================='
	echo "OpenMPTCProuter Server $OMR_VERSION is now installed !"
	echo '\033[4m\0331mSSH port: 65222 (instead of port 22)\033[0m'
	if [ "$OMR_ADMIN" = "yes" ]; then
		echo '===================================================================================='
		echo '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
		echo 'OpenMPTCProuter Server key (you need OpenMPTCProuter >= 0.42):'
		echo $OMR_ADMIN_PASS
		echo 'OpenMPTCProuter Server username (you need OpenMPTCProuter >= 0.42):'
		echo 'openmptcprouter'
		echo '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
		echo '===================================================================================='
	fi
	echo 'Shadowsocks port: 65101'
	echo 'Shadowsocks encryption: chacha20'
	echo 'Your shadowsocks key: '
	echo $SHADOWSOCKS_PASS
	echo 'Glorytun port: 65001'
	echo 'Glorytun encryption: chacha20'
	echo 'Your glorytun key: '
	echo $GLORYTUN_PASS
	if [ "$DSVPN" = "yes" ]; then
		echo 'A Dead Simple VPN port: 65401'
		echo 'A Dead Simple VPN key: '
		echo $DSVPN_PASS
	fi
	if [ "$MLVPN" = "yes" ]; then
		echo 'MLVPN first port: 65201'
		echo 'Your MLVPN password: '
		echo $MLVPN_PASS
	fi
	if [ "$UBOND" = "yes" ]; then
		echo 'UBOND first port: 65251'
		echo 'Your UBOND password: '
		echo $UBOND_PASS
	fi
	if [ "$OMR_ADMIN" = "yes" ]; then
		echo "OpenMPTCProuter API Admin key (only for configuration via API, you don't need it): "
		echo $OMR_ADMIN_PASS_ADMIN
		echo 'OpenMPTCProuter Server key: '
		echo "\033[1m${OMR_ADMIN_PASS}\033[0m"
		echo 'OpenMPTCProuter Server username: '
		echo 'openmptcprouter'
	fi
	if [ "$VPS_CERT" = "0" ]; then
		echo 'No working domain detected, not able to generate certificate for v2ray.'
		echo 'You can set VPS_DOMAIN to a working domain if you want a certificate.'
	fi
	echo '===================================================================================='
	echo 'Keys are also saved in /root/openmptcprouter_config.txt, you are free to remove them'
	echo '===================================================================================='
	echo '\033[1m  /!\ You need to reboot to enable MPTCP, shadowsocks, glorytun and shorewall /!\ \033[0m'
	echo '------------------------------------------------------------------------------------'
	echo ' After reboot, check with uname -a that the kernel name contain mptcp.'
	echo ' Else, you may have to modify GRUB_DEFAULT in /etc/default/grub'
	echo '===================================================================================='

	# Save info in file
	cat > /root/openmptcprouter_config.txt <<-EOF
	SSH port: 65222 (instead of port 22)
	Shadowsocks port: 65101
	Shadowsocks encryption: chacha20
	Your shadowsocks key: ${SHADOWSOCKS_PASS}
	Glorytun port: 65001
	Glorytun encryption: chacha20
	Your glorytun key: ${GLORYTUN_PASS}
	EOF
	if [ "$DSVPN" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		A Dead Simple VPN port: 65401
		A Dead Simple VPN key: ${DSVPN_PASS}
		EOF
	fi
	if [ "$MLVPN" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		MLVPN first port: 65201'
		Your MLVPN password: $MLVPN_PASS
		EOF
	fi
	if [ "$UBOND" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		UBOND first port: 65251'
		Your UBOND password: $UBOND_PASS
		EOF
	fi
	if [ "$OMR_ADMIN" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		Your OpenMPTCProuter ADMIN API Server key (only for configuration via API access, you don't need it): $OMR_ADMIN_PASS_ADMIN
		Your OpenMPTCProuter Server key: $OMR_ADMIN_PASS
		Your OpenMPTCProuter Server username: openmptcprouter
		EOF
	fi
	systemctl -q restart sshd
else
	echo '===================================================================================='
	echo "OpenMPTCProuter Server is now updated to version $OMR_VERSION !"
	echo 'Keys are not changed, shorewall rules files preserved'
	echo 'You need OpenMPTCProuter >= 0.30'
	echo '===================================================================================='
	echo 'Restarting systemd daemon...'
	systemctl -q daemon-reload
	echo 'done'
	echo 'Restarting systemd network...'
	systemctl -q restart systemd-networkd
	echo 'done'
	if [ "$MLVPN" = "yes" ]; then
		echo 'Restarting mlvpn...'
		systemctl -q restart mlvpn@mlvpn0
		echo 'done'
	fi
	if [ "$UBOND" = "yes" ]; then
		echo 'Restarting ubond...'
		systemctl -q restart ubond@ubond0
		echo 'done'
	fi
	if [ "$V2RAY" = "yes" ]; then
		echo 'Restarting v2ray...'
		systemctl -q restart v2ray
		echo 'done'
	fi
	if [ "$DSVPN" = "yes" ]; then
		echo 'Restarting dsvpn...'
		systemctl -q start dsvpn-server@dsvpn0 || true
		systemctl -q restart 'dsvpn-server@*' || true
		echo 'done'
	fi
	echo 'Restarting glorytun...'
	systemctl -q start glorytun-tcp@tun0 || true
	systemctl -q restart 'glorytun-tcp@*' || true
	systemctl -q start glorytun-udp@tun0 || true
	systemctl -q restart 'glorytun-udp@*' || true
	echo 'done'
	echo 'Restarting omr6in4...'
	systemctl -q start omr6in4@user0 || true
	systemctl -q restart omr6in4@* || true
	echo 'done'
	if [ "$OPENVPN" = "yes" ]; then
		echo 'Restarting OpenVPN'
		systemctl -q restart openvpn@tun0
		systemctl -q restart openvpn@tun1
		echo 'done'
	fi
	if [ "$WIREGUARD" = "yes" ]; then
		echo 'Restarting WireGuard'
		systemctl -q restart wg-quick@wg0
		echo 'done'
	fi
	if [ "$OMR_ADMIN" = "yes" ]; then
		echo 'Restarting OpenMPTCProuter VPS admin'
		systemctl -q restart omr-admin
		echo 'done'
		if ! grep -q 'Server key' /root/openmptcprouter_config.txt ; then
			cat >> /root/openmptcprouter_config.txt <<-EOF
			Your OpenMPTCProuter Server key: $OMR_ADMIN_PASS
			Your OpenMPTCProuter Server username: openmptcprouter
			EOF
			echo '===================================================================================='
			echo '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
			echo 'OpenMPTCProuter Server key:'
			echo $OMR_ADMIN_PASS
			echo 'OpenMPTCProuter Server username:'
			echo 'openmptcprouter'
			echo '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
			echo '===================================================================================='
		else
			echo '!!! Keys are in /root/openmptcprouter_config.txt !!!'
		fi
	fi
	if [ "$VPS_CERT" = "0" ]; then
		echo 'No working domain detected, not able to generate certificate for v2ray.'
		echo 'You can set VPS_DOMAIN to a working domain if you want a certificate.'
	fi
	echo 'Apply latest sysctl...'
	sysctl -p /etc/sysctl.d/90-shadowsocks.conf > /dev/null 2>&1
	echo 'done'
	echo 'Restarting omr...'
	systemctl -q restart omr
	echo 'done'
	echo 'Restarting shadowsocks...'
	systemctl -q restart shadowsocks-libev-manager@manager
#	if [ $NBCPU -gt 1 ]; then
#		for i in $NBCPU; do
#			systemctl restart shadowsocks-libev-server@config$i
#		done
#	fi
	echo 'done'
	echo 'Restarting shorewall...'
	systemctl -q restart shorewall
	systemctl -q restart shorewall6
	echo 'done'
	echo '===================================================================================='
	echo '\033[1m  /!\ You need to reboot to use latest MPTCP kernel /!\ \033[0m'
	echo '===================================================================================='
fi
