#!/bin/sh
#
# Copyright (C) 2018-2025 Ycarus (Yannick Chabanois) <ycarus@zugaina.org> for OpenMPTCProuter
#
# This is free software, licensed under the GNU General Public License v3 or later.
# See /LICENSE for more information.
#

KERNEL="6.12"
SHADOWSOCKS_PASS=${SHADOWSOCKS_PASS:-$(head -c 32 /dev/urandom | base64 -w0)}
GLORYTUN_PASS=${GLORYTUN_PASS:-$(od -vN "32" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
DSVPN_PASS=${DSVPN_PASS:-$(od -vN "32" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
#NBCPU=${NBCPU:-$(nproc --all | tr -d "\n")}
NBCPU=${NBCPU:-$(grep -c '^processor' /proc/cpuinfo | tr -d "\n")}
OBFS=${OBFS:-yes}
V2RAY_PLUGIN=${V2RAY_PLUGIN:-no}
V2RAY=${V2RAY:-yes}
V2RAY_UUID=${V2RAY_UUID:-$(cat /proc/sys/kernel/random/uuid | tr -d "\n")}
XRAY=${XRAY:-yes}
XRAY_UUID=${XRAY_UUID:-$V2RAY_UUID}
SHADOWSOCKS=${SHADOWSOCKS:-yes}
SHADOWSOCKS_GO=${SHADOWSOCKS_GO:-yes}
PSK=${PSK:-$(head -c 32 /dev/urandom | base64 -w0)}
UPSK=${UPSK:-$(head -c 32 /dev/urandom | base64 -w0)}
TLS=${TLS:-yes}
OMR_ADMIN=${OMR_ADMIN:-yes}
OMR_ADMIN_PASS=${OMR_ADMIN_PASS:-$(od -vN "32" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
OMR_ADMIN_PASS_ADMIN=${OMR_ADMIN_PASS_ADMIN:-$(od -vN "32" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
MQVPN=${MQVPN:-yes}
MQVPN_PASS=${MQVPN_PASS:-$(head -c 32 /dev/urandom | base64 -w0)}
MQVPN_PORT=${MQVPN_PORT:-65411}
MQVPN_SUBNET=${MQVPN_SUBNET:-10.255.249.0/24}
MQVPN_VERSION=${MQVPN_VERSION:-0.5.0-3k14-omr1}
MQVPN_COMMIT=${MQVPN_COMMIT:-efff246cb678f9cba994bd362856cc6c8b1e7cd3}
MQVPN_BINARY_URL=${MQVPN_BINARY_URL:-}
MQVPN2=${MQVPN2:-yes}
MQVPN2_PASS=${MQVPN2_PASS:-$(head -c 32 /dev/urandom | base64 -w0)}
MQVPN2_PORT=${MQVPN2_PORT:-65412}
MQVPN2_SUBNET=${MQVPN2_SUBNET:-10.255.248.0/24}
MQVPN2_VERSION=${MQVPN2_VERSION:-0.14.0}
MQVPN2_COMMIT=${MQVPN2_COMMIT:-535100137ad1931ab07d5ec4787f23744349b3e6}
MQVPN2_BUILD_FROM_SOURCE=${MQVPN2_BUILD_FROM_SOURCE:-no}
MQVPN2_BINARY_URL=${MQVPN2_BINARY_URL:-}
MQVPN2_BINARY_SHA256=${MQVPN2_BINARY_SHA256:-d94ef9db51035a10470700ab2dec55067788f74550f8bf20572f0828dc8ce351}
MQVPN2_PATCH_SHA256=4feb2d485c304c628aa2baff5c2707b1bb6e29024b2e9e317413945e14bbc124
OPENVPN=${OPENVPN:-yes}
OPENVPN_BONDING=${OPENVPN_BONDING:-no}
SOFTETHERVPN=${SOFTETHERVPN:-no}
SOFTETHERVPN_PASS_ADMIN=${SOFTETHERVPN_PASS_ADMIN:-$(od -vN "16" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
SOFTETHERVPN_PASS_USER=${SOFTETHERVPN_PASS_USER:-$(od -vN "16" -An -tx1 /dev/urandom | tr '[:lower:]' '[:upper:]' | tr -d " \n")}
DSVPN=${DSVPN:-yes}
WIREGUARD=${WIREGUARD:-yes}
FAIL2BAN=${FAIL2BAN:-yes}
BPFTUNE=${BPFTUNE:-yes}
BPFTUNE_LEARNING_RATE=${BPFTUNE_LEARNING_RATE:-3}
SOURCES=${SOURCES:-no}
NOINTERNET=${NOINTERNET:-no}
GRETUNNELS=${GRETUNNELS:-yes}
LANROUTES=${LANROUTES:-yes}
SPEEDTEST=${SPEEDTEST:-yes}
IPERF=${IPERF:-yes}
LOCALFILES=${LOCALFILES:-yes}
INTERFACE=${INTERFACE:-$(ip -o -4 route show to default | grep -m 1 -Po '(?<=dev )(\S+)' | tr -d "\n")}
INTERFACE6=${INTERFACE6:-$(ip -o -6 route show to default | grep -m 1 -Po '(?<=dev )(\S+)' | tr -d "\n")}
[ -z "$INTERFACE6" ] && INTERFACE6="$INTERFACE"
GLORYTUN_UDP=${GLORYTUN_UDP:-yes}
GLORYTUN_UDP_VERSION="23100474922259d00a8c0c4b00a0c8de89202cf9"
GLORYTUN_UDP_BINARY_VERSION="0.3.4-5"
GLORYTUN_TCP=${GLORYTUN_TCP:-yes}
# Old Glorytun TCP version if sources is not enabled...
GLORYTUN_TCP_VERSION="8aebb3efb3b108b1276aa74679e200e003f298de"
GLORYTUN_TCP_BINARY_VERSION="0.0.35-6"
OBFS_VERSION="486bebd9208539058e57e23a12f23103016e09b4"
OBFS_BINARY_VERSION="0.0.5-1"
OMR_ADMIN_VERSION="0.16+20260727-logging14"
OMR_ADMIN_BINARY_VERSION="0.16+20260113"
#OMR_ADMIN_BINARY_VERSION="0.3+20220827"
DSVPN_VERSION="3b99d2ef6c02b2ef68b5784bec8adfdd55b29b1a"
DSVPN_BINARY_VERSION="0.1.4-2"
V2RAY_VERSION="5.32.0"
V2RAY_PLUGIN_VERSION="4.43.0"
XRAY_VERSION="26.1.18"
#SHADOWSOCKS_VERSION="7407b214f335f0e2068a8622ef3674d868218e17"
#if [ "$UPSTREAM" = "yes" ] || [ "$UPSTREAM6" = "yes" ]; then
	SHADOWSOCKS_VERSION="8fc18fcba3226e31f9f2bb9e60d6be6a1837862b"
#fi
SHADOWSOCKS_BINARY_VERSION="3.3.5-4"
SHADOWSOCKS_GO_VERSION="1.14.0"
DEFAULT_USER="openmptcprouter"

# Fork snapshot defaults (independent from upstream Ysurac infrastructure)
OMR_GITHUB_ORG=${OMR_GITHUB_ORG:-Brazzo978}
OMR_VPS_BRANCH=${OMR_VPS_BRANCH:-omr-vps-0.1156-def}
OMR_VPS_GIT_URL=${OMR_VPS_GIT_URL:-https://github.com/${OMR_GITHUB_ORG}/openmptcprouter-vps.git}
OMR_VPS_DEBIAN_GIT_URL=${OMR_VPS_DEBIAN_GIT_URL:-https://github.com/${OMR_GITHUB_ORG}/openmptcprouter-vps-debian.git}
OMR_VPS_DEBIAN_BRANCH=${OMR_VPS_DEBIAN_BRANCH:-main}
OMR_VPS_DEBIAN_GPG_URL=${OMR_VPS_DEBIAN_GPG_URL:-https://repoomr.3klab.com/openmptcprouter.gpg.key}
OMR_VPS_ADMIN_GIT_URL=${OMR_VPS_ADMIN_GIT_URL:-https://github.com/${OMR_GITHUB_ORG}/openmptcprouter-vps-admin.git}
OMR_ADMIN_ARCHIVE_URL=${OMR_ADMIN_ARCHIVE_URL:-https://raw.githubusercontent.com/${OMR_GITHUB_ORG}/openmptcprouter-vps/${OMR_VPS_BRANCH}/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}.zip}
MQVPN_BINARY_URL=${MQVPN_BINARY_URL:-https://raw.githubusercontent.com/${OMR_GITHUB_ORG}/openmptcprouter-vps/${OMR_VPS_BRANCH}/mqvpn-${MQVPN_VERSION}-linux-amd64.tar.gz}
MQVPN2_BINARY_URL=${MQVPN2_BINARY_URL:-https://raw.githubusercontent.com/${OMR_GITHUB_ORG}/openmptcprouter-vps/${OMR_VPS_BRANCH}/mqvpn2-${MQVPN2_VERSION}-linux-amd64.tar.gz}
[ "$MQVPN2_BUILD_FROM_SOURCE" = "yes" ] && MQVPN2_BINARY_URL=
SHADOWSOCKS_GIT_URL=${SHADOWSOCKS_GIT_URL:-https://github.com/${OMR_GITHUB_ORG}/shadowsocks-libev.git}
GLORYTUN_GIT_URL=${GLORYTUN_GIT_URL:-https://github.com/${OMR_GITHUB_ORG}/glorytun.git}
DSVPN_GIT_URL=${DSVPN_GIT_URL:-https://github.com/${OMR_GITHUB_ORG}/dsvpn.git}
MQVPN_GIT_URL=${MQVPN_GIT_URL:-https://github.com/${OMR_GITHUB_ORG}/mqvpn.git}
MQVPN2_GIT_URL=${MQVPN2_GIT_URL:-https://github.com/mp0rta/mqvpn.git}
OMR_FEEDS_BASE_URL=${OMR_FEEDS_BASE_URL:-https://raw.githubusercontent.com/${OMR_GITHUB_ORG}/openmptcprouter-feeds/develop}
VPS_CONFIG_URL=${VPS_CONFIG_URL:-https://raw.githubusercontent.com/${OMR_GITHUB_ORG}/openmptcprouter-vps/${OMR_VPS_BRANCH}}

VPS_DOMAIN=${VPS_DOMAIN:-$(hostname -f 2>/dev/null || hostname)}
VPSPATH=${VPSPATH:-}
case "$VPSPATH" in
	""|/*) ;;
	*) VPSPATH="/$VPSPATH" ;;
esac
VPS_PUBLIC_IP=${VPS_PUBLIC_IP:-$(ip -4 route get 1.1.1.1 2>/dev/null | awk '/src/ {for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}' | tr -d "\n")}
VPSURL=${VPSURL:-https://repoomr.3klab.com/}
REPO=${REPO:-repoomr.3klab.com}
CHINA=${CHINA:-yes}

OMR_VERSION="0.1156-def"

DIR=$( pwd )
#"
set -e
umask 0022
export LC_ALL=C
export PATH=$PATH:/sbin
export DEBIAN_FRONTEND=noninteractive 

omr_fetch_file() {
	_omr_source="$1"
	_omr_destination="$2"
	if [ -f "$_omr_source" ]; then
		cp "$_omr_source" "$_omr_destination"
	else
		curl -fsSL "$_omr_source" -o "$_omr_destination"
	fi
}

echo "Check user..."
if [ "$(id -u)" -ne 0 ]; then echo 'Please run as root.' >&2; exit 1; fi

# Check Linux version
echo "Check Linux version..."
if test -f /etc/os-release ; then
	. /etc/os-release
else
	. /usr/lib/os-release
fi
if [ "$ID" != "debian" ]; then
	echo "This installer supports only Debian 12 or Debian 13."
	exit 1
fi
if [ "$VERSION_ID" != "12" ] && [ "$VERSION_ID" != "13" ]; then
	echo "This installer requires Debian 12 (Bookworm) or Debian 13 (Trixie)."
	exit 1
fi

echo "Check architecture..."
ARCH=$(dpkg --print-architecture | tr -d "\n")
if [ "$ARCH" != "amd64" ]; then
	echo "The OMR 6.12 kernel installer supports only x86_64 (amd64)."
	exit 1
fi
PSABI=$(awk 'BEGIN { while (!/flags/) if (getline < "/proc/cpuinfo" != 1) exit 1; if (/lm/&&/cmov/&&/cx8/&&/fpu/&&/fxsr/&&/mmx/&&/syscall/&&/sse2/) level = 1; if (level == 1 && /cx16/&&/lahf/&&/popcnt/&&/sse4_1/&&/sse4_2/&&/ssse3/) level = 2; if (level == 2 && /avx/&&/avx2/&&/bmi1/&&/bmi2/&&/f16c/&&/fma/&&/abm/&&/movbe/&&/xsave/) level = 3; if (level == 3 && /avx512f/&&/avx512bw/&&/avx512cd/&&/avx512dq/&&/avx512vl/) level = 4; if (level > 0) { print "x64v" level; exit level + 1 }; exit 1;}' | tr -d "\n")
if [ "$PSABI" = "x64v4" ]; then
	PSABI="x64v3"
fi
if [ "$PSABI" != "x64v3" ]; then
	echo "This release requires an x86-64-v3 CPU. Legacy x64v1/x64v2 kernels are not supported."
	exit 1
fi

echo "Check virtualized environment"
VIRT="$(systemd-detect-virt 2>/dev/null || true)"
if [ -n "$VIRT" ] && ([ "$VIRT" = "openvz" ] || [ "$VIRT" = "lxc" ] || [ "$VIRT" = "docker" ]); then
	echo "Containers are not supported: the OMR 6.12 kernel cannot be installed."
	exit 1
fi

# This release is intentionally fresh-install only. Refuse an existing OMR
# installation before package repair, repository changes or configuration edits.
echo "Check if OpenMPTCProuter VPS is already installed..."
CURRENT_OMR="$(grep -sh 'OpenMPTCProuter VPS' /etc/motd /etc/motd.head 2>/dev/null | awk '{print $4}' | tail -n 1 || true)"
if [ -n "$CURRENT_OMR" ] \
	|| [ -f /root/openmptcprouter_config.txt ] \
	|| [ -d /etc/openmptcprouter-vps-admin ] \
	|| [ -d /etc/openmtpcprouter-vps-admin ] \
	|| [ -e /etc/systemd/system/omr.service ] \
	|| [ -e /lib/systemd/system/omr.service ] \
	|| [ -e /usr/lib/systemd/system/omr.service ] \
	|| [ -e /etc/systemd/system/omr-admin.service ] \
	|| [ -e /lib/systemd/system/omr-admin.service ] \
	|| [ -e /usr/lib/systemd/system/omr-admin.service ] \
	|| [ -e /usr/bin/omr-update ] \
	|| [ -e /etc/systemd/system/omr-update.service ] \
	|| [ -e /lib/systemd/system/omr-update.service ] \
	|| [ -e /usr/lib/systemd/system/omr-update.service ] \
	|| dpkg-query -W -f='${Status}' omr-server 2>/dev/null | grep -q 'install ok installed'; then
	echo "E: OpenMPTCProuter VPS is already installed on this server."
	if [ -n "$CURRENT_OMR" ]; then
		echo "Detected version: $CURRENT_OMR"
	fi
	echo "0.1156-def is fresh-install only. Reinstall the VPS from a clean Debian image before running this installer."
	exit 1
fi

# Check if DPKG is locked and for broken packages
#dpkg -i /dev/zero 2>/dev/null
#if [ "$?" -eq 2 ]; then
#	echo "E: dpkg database is locked. Check that an update is not running in background..."
#	exit 1
#fi
echo "Check about broken packages..."
if ! eval apt-get check >/dev/null 2>&1 ; then
	if ! eval apt-get -f install -y 2>&1 ; then
		echo "E: \`apt-get check\` failed, you may have broken packages. Aborting..."
		exit 1
	fi
fi

# Fix old string...
if [ -f /etc/motd ] && grep --quiet 'OpenMPCTProuter VPS' /etc/motd ; then
	sed -i 's/OpenMPCTProuter/OpenMPTCProuter/g' /etc/motd
fi
if [ -f /etc/motd.head ] && grep --quiet 'OpenMPCTProuter VPS' /etc/motd.head ; then
	sed -i 's/OpenMPCTProuter/OpenMPTCProuter/g' /etc/motd.head
fi

# Force update key
#[ -f /etc/apt/sources.list.d/openmptcprouter.list ] && {
#	echo "Update OpenMPTCProuter repo key"
#	#wget -O - http://repo.openmptcprouter.com/openmptcprouter.gpg.key | apt-key add -
#	wget https://${REPO}/openmptcprouter.gpg.key -O /etc/apt/trusted.gpg.d/openmptcprouter.gpg
#}

# Force update key
[ -f /etc/apt/sources.list.d/openmptcprouter.list ] && {
	echo "Update ${REPO} key"
	apt-key del '2FDF 70C8 228B 7F04 42FE  59F6 608F D17B 2B24 D936' >/dev/null 2>&1 || true
	rm -f /etc/apt/trusted.gpg.d/openmptcprouter.gpg
	if [ "$CHINA" = "yes" ]; then
		if command -v gpg >/dev/null 2>&1 && [ -f /var/lib/openmptcprouter-vps-debian/openmptcprouter.gpg.key ]; then
			rm -f /usr/share/keyrings/openmptcprouter-archive-keyring.gpg
			gpg --dearmor -o /usr/share/keyrings/openmptcprouter-archive-keyring.gpg \
				/var/lib/openmptcprouter-vps-debian/openmptcprouter.gpg.key
			echo "deb [arch=amd64 signed-by=/usr/share/keyrings/openmptcprouter-archive-keyring.gpg] file:/var/lib/openmptcprouter-vps-debian ./" > /etc/apt/sources.list.d/openmptcprouter.list
		else
			echo "deb [arch=amd64 trusted=yes] file:/var/lib/openmptcprouter-vps-debian ./" > /etc/apt/sources.list.d/openmptcprouter.list
		fi
	else
		if command -v gpg >/dev/null 2>&1; then
			wget -q -O - https://${REPO}/openmptcprouter.gpg.key | gpg --dearmor -o /usr/share/keyrings/openmptcprouter-archive-keyring.gpg
		else
			wget -q https://${REPO}/openmptcprouter.gpg.key -O /etc/apt/trusted.gpg.d/openmptcprouter.gpg
		fi
	fi
}

echo "Remove lock and update packages list..."
rm -f /etc/apt/sources.list.d/xanmod*
rm -f /etc/apt/trusted.gpg.d/xanmod*

rm -f /var/lib/dpkg/lock
rm -f /var/lib/dpkg/lock-frontend
rm -f /var/cache/apt/archives/lock
rm -f /etc/apt/sources.list.d/buster-backports.list
rm -f /etc/apt/sources.list.d/stretch-backports.list
[ ! -f /etc/apt/sources.list ] && touch /etc/apt/sources.list
sed -i '/buster-backports/d' /etc/apt/sources.list
sed -i '/stretch-backports/d' /etc/apt/sources.list
apt-get update --allow-releaseinfo-change
rm -f /var/lib/dpkg/lock
rm -f /var/lib/dpkg/lock-frontend
rm -f /var/cache/apt/archives/lock
echo "Install apt-transport-https, gnupg and openssh-server..."
apt-get -y install apt-transport-https gnupg openssh-server libcrypt1 zstd

# Upgrade base install from Debian 12 to Debian 13.
if [ "$ID" = "debian" ] && [ "$VERSION_ID" = "12" ]; then
	echo "Update Debian 12 Bookworm to Debian 13 Trixie"
	apt-get -y -f --force-yes -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" --allow-downgrades upgrade
	apt-get -y -f --force-yes -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" --allow-downgrades dist-upgrade
	sed -i 's:archive:deb:g' /etc/apt/sources.list
	sed -i 's:bookworm:trixie:g' /etc/apt/sources.list
	sed -i 's|Signed-By: /usr/share/keyrings/debian-deb-keyring.gpg|Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg|g' /etc/apt/sources.list
	if [ -f  /etc/apt/sources.list.d/debian.sources ]; then
		sed -i 's:archive:deb:g' /etc/apt/sources.list.d/debian.sources
		sed -i 's:bookworm:trixie:g' /etc/apt/sources.list.d/debian.sources
		sed -i 's|Signed-By: /usr/share/keyrings/debian-deb-keyring.gpg|Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg|g' /etc/apt/sources.list.d/debian.sources
	fi
	apt-get update --allow-releaseinfo-change
	apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" --allow-downgrades upgrade
	apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confnew" --allow-downgrades dist-upgrade
	VERSION_ID="13"
fi

# Add OpenMPTCProuter repo
echo "Add OpenMPTCProuter repo..."
if [ "$CHINA" = "yes" ]; then
	echo "Install git..."
	apt-get -y install git
	rm -rf /var/lib/openmptcprouter-vps-debian 
	if [ ! -d /var/lib/openmptcprouter-vps-debian ]; then
		#git clone https://gitee.com/ysurac/openmptcprouter-vps-debian.git /var/lib/openmptcprouter-vps-debian
		git clone ${OMR_VPS_DEBIAN_GIT_URL} /var/lib/openmptcprouter-vps-debian
	fi
	cd /var/lib/openmptcprouter-vps-debian
	git pull
	if ! git checkout "${OMR_VPS_DEBIAN_BRANCH}" >/dev/null 2>&1; then
		echo "ERROR: OpenMPTCProuter Debian branch ${OMR_VPS_DEBIAN_BRANCH} is unavailable."
		exit 1
	fi
	if command -v gpg >/dev/null 2>&1; then
		rm -f /usr/share/keyrings/openmptcprouter-archive-keyring.gpg
		gpg --dearmor -o /usr/share/keyrings/openmptcprouter-archive-keyring.gpg \
			/var/lib/openmptcprouter-vps-debian/openmptcprouter.gpg.key
		echo "deb [arch=amd64 signed-by=/usr/share/keyrings/openmptcprouter-archive-keyring.gpg] file:/var/lib/openmptcprouter-vps-debian ./" > /etc/apt/sources.list.d/openmptcprouter.list
	else
		echo "deb [arch=amd64 trusted=yes] file:/var/lib/openmptcprouter-vps-debian ./" > /etc/apt/sources.list.d/openmptcprouter.list
	fi
	rm -rf /usr/share/omr-server-git
	if [ -f "${DIR}/debian9-x86_64.sh" ] && [ -f "${DIR}/omr-check" ]; then
		mkdir -p /usr/share/omr-server-git
		cp -a "${DIR}/." /usr/share/omr-server-git/
	elif [ ! -d /usr/share/omr-server-git ]; then
		#git clone https://gitee.com/ysurac/openmptcprouter-vps.git /usr/share/omr-server-git
		git clone ${OMR_VPS_GIT_URL} /usr/share/omr-server-git
	fi
	cd /usr/share/omr-server-git
	if [ -d .git ]; then
		git pull
		if ! git checkout "${OMR_VPS_BRANCH}" >/dev/null 2>&1; then
			echo "ERROR: OpenMPTCProuter VPS branch ${OMR_VPS_BRANCH} is unavailable."
			exit 1
		fi
	fi
	LOCALFILES="yes"
	TLS="no"
	DIR="/usr/share/omr-server-git"
else
	echo "deb [arch=amd64 signed-by=/usr/share/keyrings/openmptcprouter-archive-keyring.gpg] https://${REPO} buster main" > /etc/apt/sources.list.d/openmptcprouter.list
	cat <<-EOF | tee /etc/apt/preferences.d/openmptcprouter.pref
		Explanation: Prefer OpenMPTCProuter provided packages over the Debian native ones
		Package: *
		Pin: release o=${REPO}
		Pin-Priority: 999
	EOF
	if echo "$OMR_VERSION" | grep -Eiq 'test|rolling'; then
		echo "deb [arch=amd64 signed-by=/usr/share/keyrings/openmptcprouter-archive-keyring.gpg] https://${REPO} next main" > /etc/apt/sources.list.d/openmptcprouter-test.list
#		cat <<-EOF | tee -a /etc/apt/preferences.d/openmptcprouter.pref
#			Explanation: Prefer OpenMPTCProuter provided packages over the Debian native ones
#			Package: *
#			Pin: origin ${REPO}
#			Pin-Priority: 1002
#		EOF
	else
		rm -f /etc/apt/sources.list.d/openmptcprouter-test.list
	fi
	cat <<-EOF | tee -a /etc/apt/preferences.d/openmptcprouter.pref
		Explanation: Prefer libuv1 Debian native package
		Package: libuv1
		Pin: version *
		Pin-Priority: 1003
	EOF
	if command -v gpg >/dev/null 2>&1; then
		wget -q -O - https://${REPO}/openmptcprouter.gpg.key | gpg --dearmor -o /usr/share/keyrings/openmptcprouter-archive-keyring.gpg
	else
		wget -q https://${REPO}/openmptcprouter.gpg.key -O /etc/apt/trusted.gpg.d/openmptcprouter.gpg
	fi
fi

# Install mptcp kernel and shadowsocks
echo "Install mptcp kernel and shadowsocks..."
apt-get update --allow-releaseinfo-change
sleep 2
apt-get -y install dirmngr patch rename curl unzip pkg-config ipset bpftool

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

# Install the only supported kernel: the pinned OMR 6.12 x64v3 build.
KERNEL_VERSION="6.12.67"
OMR_KERNEL_PKG_VERSION="${OMR_KERNEL_PKG_VERSION:-6.12.67-10}"
OMR_KERNEL_SUFFIX="${OMR_KERNEL_SUFFIX:-net-perf-3k-xanmod1-v2}"
OMR_IMAGE_DEB="linux-image-${KERNEL_VERSION}-${PSABI}-${OMR_KERNEL_SUFFIX}_${OMR_KERNEL_PKG_VERSION}_amd64.deb"
OMR_HEADERS_DEB="linux-headers-${KERNEL_VERSION}-${PSABI}-${OMR_KERNEL_SUFFIX}_${OMR_KERNEL_PKG_VERSION}_amd64.deb"
OMR_LIBC_DEB="linux-libc-dev_${OMR_KERNEL_PKG_VERSION}_amd64.deb"
wget -O /tmp/${OMR_IMAGE_DEB} ${VPSURL}kernel/${OMR_IMAGE_DEB}
wget -O /tmp/${OMR_HEADERS_DEB} ${VPSURL}kernel/${OMR_HEADERS_DEB}
wget -O /tmp/${OMR_LIBC_DEB} ${VPSURL}kernel/${OMR_LIBC_DEB} || true
echo "Install OMR kernel linux-image-${KERNEL_VERSION}-${PSABI}-${OMR_KERNEL_SUFFIX}"
dpkg --force-all -i -B /tmp/${OMR_LIBC_DEB} >/dev/null 2>&1 || true
dpkg --force-all -i -B /tmp/${OMR_HEADERS_DEB}
dpkg --force-all -i -B /tmp/${OMR_IMAGE_DEB}
# Some VPS providers ignore guest GRUB defaults and boot the highest distro kernel.
# Keep OMR as preferred boot target by purging newer stock Debian kernels.
for pkg in $(dpkg-query -W -f='${Package}\n' 'linux-image-[0-9]*' 2>/dev/null | grep -E 'linux-image-[0-9]+\.[0-9]+\.[0-9]+\+deb' || true); do
	PKGREL=$(echo "$pkg" | sed -e 's/^linux-image-//' -e 's/+.*$//')
	if dpkg --compare-versions "$PKGREL" gt "$KERNEL_VERSION"; then
		apt-get -y purge "$pkg" >/dev/null 2>&1 || true
	fi
done
apt-get -y purge linux-image-amd64 linux-headers-amd64 linux-image-cloud-amd64 linux-headers-cloud-amd64 >/dev/null 2>&1 || true

[ -f /etc/default/grub ] && {
	if [ -f /boot/grub/grub.cfg ]; then
		KREL="${KERNEL_VERSION}-${PSABI}-${OMR_KERNEL_SUFFIX}"
		BOOTID=$(awk -F"'" -v k="$KREL" '$0 ~ "menuentry " && $0 ~ k && $0 !~ /recovery/ {for(i=1;i<=NF;i++) if($i ~ /^gnulinux-/) {print $i; exit}}' /boot/grub/grub.cfg)
		if [ -n "$BOOTID" ]; then
			sed -i "s@^\(GRUB_DEFAULT=\).*@\1\"${BOOTID}\"@" /etc/default/grub >/dev/null 2>&1
			sed -i '/^GRUB_SAVEDEFAULT=/d' /etc/default/grub >/dev/null 2>&1 || true
		fi
		grub-mkconfig -o /boot/grub/grub.cfg >/dev/null 2>&1
	fi
}

if [ "$ARCH" = "amd64" ]; then
	echo "Install tracebox OpenMPTCProuter edition"
	apt-get -y -o Dpkg::Options::="--force-overwrite" install tracebox
fi
if [ "$IPERF" = "yes" ] && [ "$CHINA" != "yes" ]; then
	#echo "Install iperf3 OpenMPTCProuter edition"
	#apt-get -y -o Dpkg::Options::="--force-overwrite" install omr-iperf3
	#chmod 644 /lib/systemd/system/iperf3.service
	echo "Install iperf3"
	[ "$ARCH" = "amd64" ] && apt-get -y remove omr-iperf3 omr-libiperf0 >/dev/null 2>&1
	if [ "$SOURCES" = "yes" ]; then
		apt-get -y remove iperf3 libiperf0
		apt-get -y install xz-utils devscripts equivs
		cd /tmp
		rm -rf iperf-3.18
		wget https://github.com/esnet/iperf/releases/download/3.18/iperf-3.18.tar.gz
		tar xzf iperf-3.18.tar.gz
		cd iperf-3.18
		wget --waitretry=1 --read-timeout=20 --timeout=15 -t 5 --continue --no-dns-cache ${VPSURL}debian/iperf3_3.18-2.debian.tar.xz
		tar xJf iperf3_3.18-2.debian.tar.xz
		sleep 1
		echo "Install iperf3 dependencies..."
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		mk-build-deps --install --tool "apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends -y"
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		echo "Build iperf3 package...."
		dpkg-buildpackage -b -us -uc >/dev/null 2>&1
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		cd /tmp
		echo "Install iperf3 package..."
		dpkg -i iperf3_*.deb libiperf0_*.deb >/dev/null 2>&1
		rm -rf iperf-3.18
		rm -f iperf* libiperf*
	else
		apt-get -y install iperf3 libiperf0
	fi
	if [ ! -f "/etc/iperf3/private.pem" ]; then
		mkdir -p /etc/iperf3
		openssl genrsa -out /etc/iperf3/private.pem 2048
		openssl rsa -in /etc/iperf3/private.pem -outform PEM -pubout -out /etc/iperf3/public.pem
		IPERFPASS=$(echo -n "{openmptcprouter}openmptcprouter" | sha256sum | awk '{ print $1 }')
		echo "openmptcprouter,$IPERFPASS" > /etc/iperf3/users.csv
	fi
	chown -Rf iperf3 /etc/iperf3 || true
	systemctl enable iperf3.service || true
	mkdir -p /etc/systemd/system/iperf3.service.d
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/systemd/system/iperf3.service.d/override.conf ${VPS_CONFIG_URL}${VPSPATH}/iperf3.override.conf
	else
		cp ${DIR}/iperf3.override.conf /etc/systemd/system/iperf3.service.d/override.conf
	fi
	echo "iperf3 installed"
fi

rm -f /var/lib/dpkg/lock
rm -f /var/lib/dpkg/lock-frontend

apt-get -y install mptcpize iproute2
echo "MPTCPize iperf3..."
mptcpize enable iperf3 >/dev/null 2>&1 || true

echo "Remove Shadowsocks-libev..."
apt-get -y remove shadowsocks-libev >/dev/null 2>&1 || true
if [ "$SHADOWSOCKS" = "yes" ]; then
	echo "Install Shadowsocks-libev..."
	if [ "$SOURCES" = "yes" ] || [ "$ARCH" != "amd64" ]; then
		apt-get -y install git
		## Compile Shadowsocks
		#rm -rf /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}
		#wget -O /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}.tar.gz http://github.com/shadowsocks/shadowsocks-libev/releases/download/v${SHADOWSOCKS_VERSION}/shadowsocks-libev-${SHADOWSOCKS_VERSION}.tar.gz
		cd /tmp
		rm -rf shadowsocks-libev
		git clone ${SHADOWSOCKS_GIT_URL}
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
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		apt-get -y install --no-install-recommends devscripts equivs apg libcap2-bin libpam-cap libc-ares2 libc-ares-dev libev4 haveged libpcre3-dev || true
		apt-get -y install --no-install-recommends asciidoc-base asciidoc-common docbook-xml docbook-xsl libev-dev libmbedcrypto3 libmbedtls-dev libmbedtls12 libmbedx509-0 libxml2-utils libxslt1.1 pkg-config sgml-base sgml-data xml-core xmlto xsltproc || true
		sleep 1
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		systemctl enable haveged >/dev/null 2>&1 || true
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		apt-get -y install libsodium-dev || true
		#cd /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		mk-build-deps --install --tool "apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends -y" >/dev/null 2>&1 || true
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		dpkg-buildpackage -b -us -uc >/dev/null 2>&1 || true
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		cd /tmp
		#dpkg -i shadowsocks-libev_*.deb
		dpkg -i omr-shadowsocks-libev_*.deb >/dev/null 2>&1 || true
		#mkdir -p /usr/lib/shadowsocks-libev
		#cp -f /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}/src/*.ebpf /usr/lib/shadowsocks-libev
		#rm -rf /tmp/shadowsocks-libev-${SHADOWSOCKS_VERSION}
		rm -rf /tmp/shadowsocks-libev
	else
		apt-get -y install haveged >/dev/null 2>&1 || true
		apt-get -y -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-overwrite" install omr-shadowsocks-libev=${SHADOWSOCKS_BINARY_VERSION}
	fi
fi

echo "Add modules on server start..."
# Load BBR Congestion module at boot time
if ! grep -q bbr /etc/modules ; then
	echo tcp_bbr >> /etc/modules
fi

echo "Stop OpenMPTCProuter VPS admin"
if systemctl -q is-active omr-admin.service 2>/dev/null; then
	systemctl -q stop omr-admin > /dev/null 2>&1 || true
fi
if systemctl -q is-active omr-admin-ipv6.service 2>/dev/null; then
	systemctl -q stop omr-admin-ipv6 > /dev/null 2>&1 || true
	systemctl -q disable omr-admin-ipv6 > /dev/null 2>&1 || true
fi

if [ "$OMR_ADMIN" = "yes" ]; then
	echo 'Install OpenMPTCProuter VPS Admin'
	apt-get -y install python3-openssl python3-pip python3-setuptools python3-wheel python3-dev
	#apt-get -y install unzip gunicorn python3-flask-restful python3-openssl python3-pip python3-setuptools python3-wheel
	#apt-get -y install unzip python3-openssl python3-pip python3-setuptools python3-wheel
	apt-get -y --allow-downgrades install python3-passlib python3-jwt python3-netaddr libuv1t64 python3-uvloop
	apt-get -y --allow-downgrades install python3-uvicorn jq ipcalc python3-netifaces python3-aiofiles python3-psutil python3-requests pwgen
	echo '-- pip3 install needed python modules'
	echo "If you see any error here, I really don't care: it's about a module not used for home users"
	#pip3 install pyjwt passlib uvicorn fastapi netjsonconfig python-multipart netaddr
	#pip3 -q install fastapi netjsonconfig python-multipart uvicorn -U
	apt-get -y install python3-jsonschema python3-fastapi python3-multipart python3-starlette
	mkdir -p /etc/openmptcprouter-vps-admin/omr-6in4
	mkdir -p /etc/openmptcprouter-vps-admin/intf
	#[ ! -f "/etc/openmptcprouter-vps-admin/current-vpn" ] && echo "glorytun_tcp" > /etc/openmptcprouter-vps-admin/current-vpn
	[ ! -f "/etc/openmptcprouter-vps-admin/current-vpn" ] && echo "openvpn" > /etc/openmptcprouter-vps-admin/current-vpn
	mkdir -p /var/opt/openmptcprouter
	if [ "$SOURCES" = "yes" ]; then
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /lib/systemd/system/omr-admin.service ${VPS_CONFIG_URL}${VPSPATH}/omr-admin.service.in
			#wget -O /lib/systemd/system/omr-admin-ipv6.service ${VPS_CONFIG_URL}${VPSPATH}/omr-admin-ipv6.service.in
		else
			cp ${DIR}/omr-admin.service.in /lib/systemd/system/omr-admin.service
		fi
		OMR_ADMIN_ARCHIVE_SOURCE="${OMR_ADMIN_ARCHIVE_URL}"
		if [ "$LOCALFILES" = "yes" ] && [ -f "${DIR}/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}.zip" ]; then
			OMR_ADMIN_ARCHIVE_SOURCE="${DIR}/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}.zip"
		fi
		omr_fetch_file "${OMR_ADMIN_ARCHIVE_SOURCE}" /tmp/openmptcprouter-vps-admin.zip
		cd /tmp
		unzip -q -o openmptcprouter-vps-admin.zip
		OMR_ADMIN_SRC_DIR=""
		for admin_dir in "/tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}" "/tmp/openmptcprouter-vps-admin"; do
			[ -f "${admin_dir}/omr-admin.py" ] && OMR_ADMIN_SRC_DIR="${admin_dir}" && break
		done
		if [ -z "${OMR_ADMIN_SRC_DIR}" ]; then
			OMR_ADMIN_SRC_DIR=$(find /tmp -maxdepth 1 -type d -name 'openmptcprouter-vps-admin*' -exec test -f '{}/omr-admin.py' \; -print | head -n 1)
		fi
		[ -z "${OMR_ADMIN_SRC_DIR}" ] && {
			echo "Unable to find omr-admin.py in ${OMR_ADMIN_ARCHIVE_URL}" >&2
			exit 8
		}
		install -m 755 "${OMR_ADMIN_SRC_DIR}/omr-admin.py" /usr/local/bin/omr-admin.py
		install -m 755 "${OMR_ADMIN_SRC_DIR}/omr-admin.py" /usr/bin/omr-admin.py
		if [ -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ]; then
			OMR_ADMIN_PASS2=$(grep -Po '"'"pass"'"\s*:\s*"\K([^"]*)' /etc/openmptcprouter-vps-admin/omr-admin-config.json | tr -d  "\n")
			[ -z "$OMR_ADMIN_PASS2" ] && OMR_ADMIN_PASS2=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].openmptcprouter.user_password | tr -d "\n")
			[ -n "$OMR_ADMIN_PASS2" ] && OMR_ADMIN_PASS=$OMR_ADMIN_PASS2
			OMR_ADMIN_PASS_ADMIN2=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].admin.user_password | tr -d "\n")
			[ -n "$OMR_ADMIN_PASS_ADMIN2" ] && OMR_ADMIN_PASS_ADMIN=$OMR_ADMIN_PASS_ADMIN2
		else
			cp "${OMR_ADMIN_SRC_DIR}/omr-admin-config.json" /etc/openmptcprouter-vps-admin/
			install -m 755 "${OMR_ADMIN_SRC_DIR}/omr-admin.py" /usr/local/bin/omr-admin.py
			install -m 755 "${OMR_ADMIN_SRC_DIR}/omr-admin.py" /usr/bin/omr-admin.py
			cd /etc/openmptcprouter-vps-admin
		fi
		if [ -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ] && [ "$(grep user_password /etc/openmptcprouter-vps-admin/omr-admin-config.json)" = "" ]; then
			cp "${OMR_ADMIN_SRC_DIR}/omr-admin-config.json" /etc/openmptcprouter-vps-admin/
			install -m 755 "${OMR_ADMIN_SRC_DIR}/omr-admin.py" /usr/local/bin/omr-admin.py
			install -m 755 "${OMR_ADMIN_SRC_DIR}/omr-admin.py" /usr/bin/omr-admin.py
			cd /etc/openmptcprouter-vps-admin
		fi
		rm -rf /tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION} /tmp/openmptcprouter-vps-admin
		chmod u+x /usr/local/bin/omr-admin.py
	else
		if [ -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ]; then
			OMR_ADMIN_PASS2=$(grep -Po '"'"pass"'"\s*:\s*"\K([^"]*)' /etc/openmptcprouter-vps-admin/omr-admin-config.json | tr -d  "\n")
			[ -z "$OMR_ADMIN_PASS2" ] && OMR_ADMIN_PASS2=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].openmptcprouter.user_password | tr -d "\n")
			[ -n "$OMR_ADMIN_PASS2" ] && [ "$OMR_ADMIN_PASS2" != "MySecretKey" ] && OMR_ADMIN_PASS=$OMR_ADMIN_PASS2
			OMR_ADMIN_PASS_ADMIN2=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].admin.user_password | tr -d "\n")
			[ -n "$OMR_ADMIN_PASS_ADMIN2" ] && [ "$OMR_ADMIN_PASS_ADMIN2" != "AdminMySecretKey" ] && OMR_ADMIN_PASS_ADMIN=$OMR_ADMIN_PASS_ADMIN2
		fi
		apt-get -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-overwrite" -y --allow-downgrades install omr-vps-admin=${OMR_ADMIN_BINARY_VERSION}
		if [ ! -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ]; then
			cp /usr/share/omr-admin/omr-admin-config.json /etc/openmptcprouter-vps-admin/
		fi
		#OMR_ADMIN_PASS=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].openmptcprouter.user_password | tr -d "\n")
		#OMR_ADMIN_PASS_ADMIN=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].admin.user_password | tr -d "\n")
	fi
	if [ -n "$OMR_ADMIN_ARCHIVE_URL" ]; then
		rm -rf /tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION} /tmp/openmptcprouter-vps-admin /tmp/openmptcprouter-vps-admin.zip
		OMR_ADMIN_ARCHIVE_SOURCE="${OMR_ADMIN_ARCHIVE_URL}"
		if [ "$LOCALFILES" = "yes" ] && [ -f "${DIR}/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}.zip" ]; then
			OMR_ADMIN_ARCHIVE_SOURCE="${DIR}/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}.zip"
		fi
		omr_fetch_file "${OMR_ADMIN_ARCHIVE_SOURCE}" /tmp/openmptcprouter-vps-admin.zip
		cd /tmp
		unzip -q -o openmptcprouter-vps-admin.zip
		OMR_ADMIN_SRC_DIR=""
		for admin_dir in "/tmp/openmptcprouter-vps-admin-${OMR_ADMIN_VERSION}" "/tmp/openmptcprouter-vps-admin"; do
			[ -f "${admin_dir}/omr-admin.py" ] && OMR_ADMIN_SRC_DIR="${admin_dir}" && break
		done
		if [ -z "${OMR_ADMIN_SRC_DIR}" ]; then
			OMR_ADMIN_SRC_DIR=$(find /tmp -maxdepth 1 -type d -name 'openmptcprouter-vps-admin*' -exec test -f '{}/omr-admin.py' \; -print | head -n 1)
		fi
		[ -z "${OMR_ADMIN_SRC_DIR}" ] && {
			echo "Unable to find omr-admin.py in ${OMR_ADMIN_ARCHIVE_URL}" >&2
			exit 8
		}
		if [ -f "${OMR_ADMIN_SRC_DIR}/omr-admin.py" ]; then
			install -m 755 "${OMR_ADMIN_SRC_DIR}/omr-admin.py" /usr/local/bin/omr-admin.py
			install -m 755 "${OMR_ADMIN_SRC_DIR}/omr-admin.py" /usr/bin/omr-admin.py
			chmod u+x /usr/local/bin/omr-admin.py
		fi
		if [ ! -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ] && [ -f "${OMR_ADMIN_SRC_DIR}/omr-admin-config.json" ]; then
			cp "${OMR_ADMIN_SRC_DIR}/omr-admin-config.json" /etc/openmptcprouter-vps-admin/
		fi
	fi
	if [ ! -f /etc/openmptcprouter-vps-admin/key.pem ]; then
		cd /etc/openmptcprouter-vps-admin
		openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -keyout key.pem -out cert.pem -subj "/C=US/ST=Oregon/L=Portland/O=OpenMPTCProuterVPS/OU=Org/CN=www.openmptcprouter.vps"
	fi
	sed -i "s:openmptcptouter:${DEFAULT_USER}:g" /etc/openmptcprouter-vps-admin/omr-admin-config.json
	sed -i "s:AdminMySecretKey:$OMR_ADMIN_PASS_ADMIN:g" /etc/openmptcprouter-vps-admin/omr-admin-config.json
	sed -i "s:MySecretKey:$OMR_ADMIN_PASS:g" /etc/openmptcprouter-vps-admin/omr-admin-config.json
	[ "$NOINTERNET" = "yes" ] && {
		jq '. + {internet: false}' /etc/openmptcprouter-vps-admin/omr-admin-config.json > /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp
		mv /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp /etc/openmptcprouter-vps-admin/omr-admin-config.json
		#sed -i 's/"port": 65500,/"port": 65500,\n    "internet": false,/' /etc/openmptcprouter-vps-admin/omr-admin-config.json
	}
	[ "$GRETUNNELS" = "no" ] && {
		jq '. + {gre_tunnels: false}' /etc/openmptcprouter-vps-admin/omr-admin-config.json > /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp
		mv /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp /etc/openmptcprouter-vps-admin/omr-admin-config.json
		#sed -i 's/"port": 65500,/"port": 65500,\n    "gre_tunnels": false,/' /etc/openmptcprouter-vps-admin/omr-admin-config.json
	}
	[ "$LANROUTES" = "no" ] && {
		jq '. + {lan_routes: false}' /etc/openmptcprouter-vps-admin/omr-admin-config.json > /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp
		mv /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp /etc/openmptcprouter-vps-admin/omr-admin-config.json
	}

	# IPv6 give an error on uvicorn
	jq '. + {host: "0.0.0.0"}' /etc/openmptcprouter-vps-admin/omr-admin-config.json > /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp
	mv /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp /etc/openmptcprouter-vps-admin/omr-admin-config.json

	python3 - <<'PY'
from pathlib import Path

config_old = """    elif path.exists('/proc/sys/net/mptcp/enabled'):
        mptcp_enabled = os.popen('sysctl -n net.mptcp.enabled').read().rstrip()
        mptcp_checksum = os.popen('sysctl -n net.mptcp.checksum_enabled').read().rstrip()
        mptcp_version = '1'
"""
config_new = """    elif path.exists('/proc/sys/net/mptcp/enabled'):
        mptcp_enabled = os.popen('sysctl -n net.mptcp.enabled').read().rstrip()
        mptcp_checksum = os.popen('sysctl -n net.mptcp.checksum_enabled').read().rstrip()
        mptcp_pm_type = os.popen('sysctl -n net.mptcp.pm_type').read().rstrip()
        mptcp_path_manager = 'userspace' if mptcp_pm_type == '1' else 'fullmesh'
        mptcp_scheduler = os.popen('sysctl -n net.mptcp.scheduler').read().rstrip()
        if mptcp_scheduler.startswith('bpf_'):
            mptcp_scheduler = 'mptcp_' + mptcp_scheduler + '.o'
        mptcp_syn_retries = os.popen('sysctl -n net.ipv4.tcp_syn_retries').read().rstrip()
        mptcp_version = '1'
"""
mptcp_old = """    else:
        os.system('sysctl -qw net.mptcp.checksum_enabled=' + checksum)
"""
mptcp_new = """    else:
        os.system('sysctl -qw net.mptcp.checksum_enabled=' + checksum)
        if path_manager in ('userspace', 'user', 'netlink'):
            os.system('sysctl -qw net.mptcp.pm_type=1')
        else:
            os.system('sysctl -qw net.mptcp.pm_type=0')
        scheduler_runtime = scheduler
        if scheduler_runtime.endswith('.o'):
            scheduler_runtime = scheduler_runtime[:-2]
        if scheduler_runtime.startswith('mptcp_bpf_'):
            scheduler_runtime = 'bpf_' + scheduler_runtime[10:]
        elif scheduler_runtime.startswith('mptcp_'):
            scheduler_runtime = scheduler_runtime[6:]
        os.system('sysctl -qw net.mptcp.scheduler=' + scheduler_runtime)
        os.system('sysctl -qw net.ipv4.tcp_syn_retries=' + str(syn_retries))
"""
xray_old = """            routing = {'type': 'field','inboundTag': [tag], 'outboundTag': 'OMRLan'}
"""
xray_new = """            routing = {'type': 'field','inboundTag': [tag], 'outboundTag': 'direct'}
"""
xray_marker = "def xray_add_port(user, port, proto, name, destip, destport):"

for target in (Path('/usr/local/bin/omr-admin.py'), Path('/usr/bin/omr-admin.py')):
    if not target.exists():
        continue
    data = target.read_text()
    updated = data
    if config_old in updated:
        updated = updated.replace(config_old, config_new, 1)
    if mptcp_old in updated:
        updated = updated.replace(mptcp_old, mptcp_new, 1)
    marker_pos = updated.find(xray_marker)
    if marker_pos != -1:
        before = updated[:marker_pos]
        after = updated[marker_pos:]
        after = after.replace(xray_old, xray_new, 1)
        updated = before + after
    if updated != data:
        target.write_text(updated)
PY


	chmod 644 /lib/systemd/system/omr-admin.service
	#chmod 644 /lib/systemd/system/omr-admin-ipv6.service
	#[ "$(ip -6 a)" != "" ] && sed -i 's/0.0.0.0/::/g' /usr/local/bin/omr-admin.py
	#[ "$(ip -6 a)" != "" ] && {
	#	systemctl enable omr-admin-ipv6.service
	#}
	systemctl enable omr-admin.service
	mptcpize enable omr-admin.service >/dev/null 2>&1
	if systemctl -q is-active omr-admin-ipv6.service 2>/dev/null; then
		systemctl -q stop omr-admin-ipv6 >/dev/null 2>&1
		systemctl -q disable omr-admin-ipv6 >/dev/null 2>&1
	fi
fi

# OMR 6.x compatibility bridge for scheduler/CC sync on modern kernels
mkdir -p /usr/share/bpf/scheduler
if ! ls /usr/share/bpf/scheduler/mptcp_bpf_*.o >/dev/null 2>&1; then
	MPTCP_BPF_SCHED_URL="${MPTCP_BPF_SCHED_URL:-${VPSURL%/}/kernel/mptcp-bpf-schedulers.tar.gz}"
	wget -q -O /tmp/mptcp-bpf-schedulers.tar.gz "${MPTCP_BPF_SCHED_URL}" || true
	if [ -s /tmp/mptcp-bpf-schedulers.tar.gz ]; then
		tar xzf /tmp/mptcp-bpf-schedulers.tar.gz -C /usr/share/bpf/scheduler >/dev/null 2>&1 || true
	fi
fi
rm -f /tmp/mptcp-bpf-schedulers.tar.gz >/dev/null 2>&1 || true

cat > /usr/local/sbin/load-mptcp-bpf-schedulers.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
DIR=/usr/share/bpf/scheduler
PIN=/sys/fs/bpf/mptcp_sched
command -v bpftool >/dev/null 2>&1 || exit 0
mkdir -p "$PIN"

register_one() {
	local obj="$1"
	local map_name="$2"
	[ -f "$obj" ] || return 0
	if bpftool struct_ops list 2>/dev/null | awk '{print $2}' | grep -qx "$map_name"; then
		return 0
	fi
	bpftool struct_ops register "$obj" "$PIN" >/dev/null 2>&1 || true
}

register_one "$DIR/mptcp_bpf_bkup.o" bkup
register_one "$DIR/mptcp_bpf_burst.o" burst
register_one "$DIR/mptcp_bpf_first.o" first
register_one "$DIR/mptcp_bpf_red.o" red
register_one "$DIR/mptcp_bpf_rr.o" rr
register_one "$DIR/mptcp_bpf_minrtt.o" minrtt
EOF
chmod 0755 /usr/local/sbin/load-mptcp-bpf-schedulers.sh

cat > /etc/systemd/system/mptcp-bpf-schedulers.service <<'EOF'
[Unit]
Description=Load MPTCP BPF schedulers
After=network-pre.target
DefaultDependencies=no
Before=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/load-mptcp-bpf-schedulers.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

cat > /usr/local/sbin/omr-mptcp-compat.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

CONF="/etc/sysctl.d/90-shadowsocks.conf"
[ -e /proc/sys/net/mptcp/enabled ] || exit 0
[ -f "$CONF" ] || exit 0

read_key_from_conf() {
	local key="$1"
	awk -F= -v k="$key" '
		$1 ~ "^[[:space:]]*"k"[[:space:]]*$" {
			val=$2
			gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
			print val
		}
	' "$CONF" | tail -n1
}

normalize_scheduler() {
	local s="${1:-}"
	s="$(echo "$s" | tr -d '[:space:]')"
	s="${s%.o}"
	s="${s#mptcp_bpf_}"
	s="${s#mptcp_}"
	case "$s" in
		bkup|burst|first|red|rr|minrtt) echo "bpf_${s}" ;;
		bpf_*) echo "$s" ;;
		*) echo "$s" ;;
	esac
}

map_pm_type() {
	case "${1:-0}" in
		1|userspace|user|netlink) echo "1" ;;
		*) echo "0" ;;
	esac
}

checksum="$(read_key_from_conf net.mptcp.mptcp_checksum)"
[ -z "$checksum" ] && checksum="$(read_key_from_conf net.mptcp.checksum_enabled)"
[ -z "$checksum" ] && checksum="$(sysctl -n net.mptcp.checksum_enabled 2>/dev/null || echo 0)"

scheduler="$(read_key_from_conf net.mptcp.mptcp_scheduler)"
[ -z "$scheduler" ] && scheduler="$(read_key_from_conf net.mptcp.scheduler)"
[ -z "$scheduler" ] && scheduler="$(sysctl -n net.mptcp.scheduler 2>/dev/null || echo default)"
scheduler="$(normalize_scheduler "$scheduler")"

pm_type_raw="$(read_key_from_conf net.mptcp.mptcp_path_manager)"
[ -z "$pm_type_raw" ] && pm_type_raw="$(read_key_from_conf net.mptcp.pm_type)"
[ -z "$pm_type_raw" ] && pm_type_raw="0"
pm_type="$(map_pm_type "$pm_type_raw")"

syn_retries="$(read_key_from_conf net.mptcp.mptcp_syn_retries)"
[ -z "$syn_retries" ] && syn_retries="$(read_key_from_conf net.ipv4.tcp_syn_retries)"
[ -z "$syn_retries" ] && syn_retries="$(sysctl -n net.ipv4.tcp_syn_retries 2>/dev/null || echo 6)"

cc="$(read_key_from_conf net.ipv4.tcp_congestion_control)"
[ -z "$cc" ] && cc="$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || true)"

available="$(sysctl -n net.mptcp.available_schedulers 2>/dev/null || true)"
if [ -n "$available" ] && ! grep -qw -- "$scheduler" <<<"$available"; then
	if grep -qw -- "bpf_${scheduler}" <<<"$available"; then
		scheduler="bpf_${scheduler}"
	else
		scheduler="default"
	fi
fi

sysctl -qw net.mptcp.enabled=1 || true
sysctl -qw net.mptcp.checksum_enabled="$checksum" || true
sysctl -qw net.mptcp.pm_type="$pm_type" || true
sysctl -qw net.mptcp.scheduler="$scheduler" || true

if [[ "$syn_retries" =~ ^[0-9]+$ ]]; then
	sysctl -qw net.ipv4.tcp_syn_retries="$syn_retries" || true
fi
if [ -n "$cc" ]; then
	sysctl -qw net.ipv4.tcp_congestion_control="$cc" || true
fi

logger -t omr-mptcp-compat "applied scheduler=$scheduler pm_type=$pm_type checksum=$checksum cc=$cc"
EOF
chmod 0755 /usr/local/sbin/omr-mptcp-compat.sh

cat > /etc/systemd/system/omr-mptcp-compat.service <<'EOF'
[Unit]
Description=OMR MPTCP compatibility bridge for modern kernels
After=network-online.target mptcp-bpf-schedulers.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/omr-mptcp-compat.sh
EOF

cat > /etc/systemd/system/omr-mptcp-compat.path <<'EOF'
[Unit]
Description=Watch OMR sysctl config and apply MPTCP compatibility mapping

[Path]
PathChanged=/etc/sysctl.d/90-shadowsocks.conf
PathModified=/etc/sysctl.d/90-shadowsocks.conf
Unit=omr-mptcp-compat.service

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/omr-mptcp-compat.timer <<'EOF'
[Unit]
Description=Periodic OMR MPTCP compatibility apply

[Timer]
OnBootSec=20s
OnUnitActiveSec=30s
AccuracySec=5s
Unit=omr-mptcp-compat.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable mptcp-bpf-schedulers.service >/dev/null 2>&1 || true
systemctl enable omr-mptcp-compat.path omr-mptcp-compat.timer >/dev/null 2>&1 || true
systemctl restart mptcp-bpf-schedulers.service >/dev/null 2>&1 || true
systemctl restart omr-mptcp-compat.path omr-mptcp-compat.timer >/dev/null 2>&1 || true
systemctl start omr-mptcp-compat.service >/dev/null 2>&1 || true

# Get shadowsocks optimization
if [ "$LOCALFILES" = "no" ]; then
	wget -O /etc/sysctl.d/90-shadowsocks.conf ${VPS_CONFIG_URL}${VPSPATH}/shadowsocks.6.1.conf
else
	cp ${DIR}/shadowsocks.6.1.conf /etc/sysctl.d/90-shadowsocks.conf
fi

if [ "$SHADOWSOCKS" = "yes" ]; then
	# Install shadowsocks config and add a shadowsocks by CPU
	mkdir -p /etc/shadowsocks-libev
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/shadowsocks-libev/manager.json ${VPS_CONFIG_URL}${VPSPATH}/manager.json
	else
		cp ${DIR}/manager.json /etc/shadowsocks-libev/manager.json
	fi
	SHADOWSOCKS_PASS_JSON=$(echo $SHADOWSOCKS_PASS | sed 's/+/-/g; s/\//_/g;')
	if [ "$NBCPU" -gt "1" ]; then
		for i in $(seq 2 $NBCPU); do
			sed -i '0,/65101/ s/        "65101.*/&\n&/' /etc/shadowsocks-libev/manager.json
		done
	fi
	sed -i "s:MySecretKey:$SHADOWSOCKS_PASS_JSON:g" /etc/shadowsocks-libev/manager.json
	[ "$(ip -6 a 2>/dev/null)" = "" ] && sed -i '/"\[::0\]"/d' /etc/shadowsocks-libev/manager.json
	[ ! -f /etc/shadowsocks-libev/local.acl ] && touch /etc/shadowsocks-libev/local.acl
	#sed -i 's:aes-256-cfb:chacha20:g' /etc/shadowsocks-libev/config.json
	#sed -i 's:json:json --no-delay:g' /lib/systemd/system/shadowsocks-libev-server@.service
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /lib/systemd/system/shadowsocks-libev-manager@.service ${VPS_CONFIG_URL}${VPSPATH}/shadowsocks-libev-manager@.service.in
	else
		cp ${DIR}/shadowsocks-libev-manager@.service.in /lib/systemd/system/shadowsocks-libev-manager@.service
	fi
	if systemctl -q is-enabled shadowsocks-libev 2>/dev/null; then
		systemctl -q disable shadowsocks-libev
	fi
	[ -f /etc/shadowsocks-libev/config.json ] && systemctl disable shadowsocks-libev-server@config.service
	systemctl enable shadowsocks-libev-manager@manager.service
	if [ $NBCPU -gt 1 ]; then
		for i in $(seq 1 $NBCPU); do
			[ -f /etc/shadowsocks-libev/config$i.json ] && systemctl is-enabled shadowsocks-libev && systemctl disable shadowsocks-libev-server@config$i.service
		done
	fi
	if systemctl -q is-active shadowsocks-libev-manager@manager 2>/dev/null; then
		systemctl -q stop shadowsocks-libev-manager@manager > /dev/null 2>&1
	fi
fi
if ! grep -q 'DefaultLimitNOFILE=65536' /etc/systemd/system.conf ; then
	echo 'DefaultLimitNOFILE=65536' >> /etc/systemd/system.conf
fi

if [ "$LOCALFILES" = "no" ]; then
	wget -O /usr/bin/omr-check ${VPS_CONFIG_URL}${VPSPATH}/omr-check
	chmod 755 /usr/bin/omr-check
else
	cp ${DIR}/omr-check /usr/bin/omr-check
	chmod 755 /usr/bin/omr-check
fi

mkdir -p /etc/modules-load.d
cat > /etc/modules-load.d/omr-tcp-cc.conf <<-EOF
tcp_bic
tcp_cdg
tcp_cubic
tcp_dctcp
tcp_highspeed
tcp_hstcp
tcp_htcp
tcp_hybla
tcp_illinois
tcp_lp
tcp_nv
tcp_scalable
tcp_vegas
tcp_veno
tcp_westwood
tcp_yeah
EOF
for module in $(cat /etc/modules-load.d/omr-tcp-cc.conf); do
	modprobe ${module} >/dev/null 2>&1 || true
done

# Install simple-obfs
if [ "$OBFS" = "yes" ]; then
	echo "Install OBFS"
	if [ "$SOURCES" = "yes" ] || [ "$ARCH" != "amd64" ]; then
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
		apt-get -y -o Dpkg::Options::="--force-overwrite" install omr-simple-obfs=${OBFS_BINARY_VERSION}
	fi
	#sed -i 's%"mptcp": true%"mptcp": true,\n"plugin": "/usr/local/bin/obfs-server",\n"plugin_opts": "obfs=http;mptcp;fast-open;t=400"%' /etc/shadowsocks-libev/config.json
fi

# Install v2ray-plugin
if [ "$V2RAY_PLUGIN" = "yes" ]; then
	echo "Install v2ray plugin"
	if [ "$SOURCES" = "yes" ] && [ "$ARCH" != "amd64" ]; then
		rm -rf /tmp/v2ray-plugin-linux-amd64-${V2RAY_PLUGIN_VERSION}.tar.gz
		#wget -O /tmp/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz https://github.com/shadowsocks/v2ray-plugin/releases/download/${V2RAY_PLUGIN_VERSION}/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz
		#wget -O /tmp/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz ${VPS_CONFIG_URL}${VPSPATH}/bin/v2ray-plugin-linux-amd64-v${V2RAY_PLUGIN_VERSION}.tar.gz
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
		apt-get -y install v2ray-plugin=${V2RAY_PLUGIN_VERSION}
	fi
fi

if [ "$OBFS" = "no" ] && [ "$V2RAY_PLUGIN" = "no" ] && [ -f /etc/shadowsocks-libev/config.json ]; then
	sed -i -e '/plugin/d' -e 's/,,//' /etc/shadowsocks-libev/config.json
fi

if systemctl -q is-active shadowsocks-go.service 2>/dev/null; then
	systemctl -q stop shadowsocks-go > /dev/null 2>&1
	systemctl -q disable shadowsocks-go > /dev/null 2>&1
fi

if [ "$SHADOWSOCKS_GO" = "yes" ]; then
	#if [ "$SOURCES" = "yes" ] || [ "$ARCH" = "arm64" ]; then
	if [ "$ARCH" = "arm64" ]; then
		if [ "$ARCH" = "amd64" ]; then
			wget -O /tmp/shadowsocks-go-${SHADOWSOCKS_GO_VERSION}-amd64.deb ${VPSURL}/debian/shadowsocks-go-${SHADOWSOCKS_GO_VERSION}-amd64.deb
			rm -f /var/lib/dpkg/lock
			rm -f /var/lib/dpkg/lock-frontend
			dpkg --force-all -i -B /tmp/shadowsocks-go-${SHADOWSOCKS_GO_VERSION}-amd64.deb
			rm -f /tmp/shadowsocks-go-${SHADOWSOCKS_GO_VERSION}-amd64.deb
		elif [ "$ARCH" = "arm64" ]; then
			wget -O /tmp/shadowsocks-go-${SHADOWSOCKS_GO_VERSION}-arm64.deb ${VPSURL}/debian/shadowsocks-go-${SHADOWSOCKS_GO_VERSION}-arm64.deb
			rm -f /var/lib/dpkg/lock
			rm -f /var/lib/dpkg/lock-frontend
			dpkg --force-all -i -B /tmp/shadowsocks-go-${SHADOWSOCKS_GO_VERSION}-arm64.deb
			rm -f /tmp/shadowsocks-go-${SHADOWSOCKS_GO_VERSION}-arm64.deb
		fi
	else
		apt-get -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-overwrite" -y install shadowsocks-go=${SHADOWSOCKS_GO_VERSION}
	fi
	if [ -f /etc/shadowsocks-go/server.json ]; then
		PSK2=$(grep -Po '"'"psk"'"\s*:\s*"\K([^"]*)' /etc/shadowsocks-go/server.json | head -n 1 | tr -d "\n")
		[ -n "$PSK2" ] && [ "$PSK2" != "PSK" ] && [ "$PSK2" != "null" ] && PSK="$PSK2"
		UPSK2=$(grep -Po '"'"openmptcprouter"'"\s*:\s*"\K([^"]*)' /etc/shadowsocks-go/upsks.json | head -n 1 | tr -d "\n")
		[ -n "$UPSK2" ] && [ "$UPSK2" != "UPSK" ] && [ "$UPSK2" != "null" ] && UPSK="$UPSK2"
	fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/shadowsocks-go/server.json ${VPS_CONFIG_URL}${VPSPATH}/shadowsocks-go.server.json
	else
		cp ${DIR}/shadowsocks-go.server.json /etc/shadowsocks-go/server.json
	fi
	sed -i "s:\"PSK\":\"$PSK\":g" /etc/shadowsocks-go/server.json
	sed -i "s:UPSK:$UPSK:g" /etc/shadowsocks-go/upsks.json
	jq -M 'del(.users[0].openmptcprouter."shadowsocks-go")' /etc/openmptcprouter-vps-admin/omr-admin-config.json > /etc/openmptcprouter-vps-admin/omr-admin-config.json.new
	mv -f /etc/openmptcprouter-vps-admin/omr-admin-config.json /etc/openmptcprouter-vps-admin/omr-admin-config.json.bak
	mv -f /etc/openmptcprouter-vps-admin/omr-admin-config.json.new /etc/openmptcprouter-vps-admin/omr-admin-config.json

	chmod 644 /lib/systemd/system/shadowsocks-go.service
	systemctl daemon-reload
	systemctl enable shadowsocks-go.service
fi


if systemctl -q is-active v2ray.service 2>/dev/null; then
	systemctl -q stop v2ray > /dev/null 2>&1
	systemctl -q disable v2ray > /dev/null 2>&1
fi

if [ "$V2RAY" = "yes" ]; then
	#apt-get -y -o Dpkg::Options::="--force-overwrite" install v2ray
	#if [ "$SOURCES" = "yes" ] || [ "$ARCH" = "arm64" ]; then
	if [ "$ARCH" = "arm64" ]; then
		if [ "$ARCH" = "amd64" ]; then
			wget -O /tmp/v2ray-${V2RAY_VERSION}-amd64.deb ${VPSURL}/debian/v2ray-${V2RAY_VERSION}-amd64.deb
			rm -f /var/lib/dpkg/lock
			rm -f /var/lib/dpkg/lock-frontend
			dpkg --force-all -i -B /tmp/v2ray-${V2RAY_VERSION}-amd64.deb
			rm -f /tmp/v2ray-${V2RAY_VERSION}-amd64.deb
		elif [ "$ARCH" = "arm64" ]; then
			wget -O /tmp/v2ray-${V2RAY_VERSION}-arm64.deb ${VPSURL}/debian/v2ray-${V2RAY_VERSION}-arm64.deb
			rm -f /var/lib/dpkg/lock
			rm -f /var/lib/dpkg/lock-frontend
			dpkg --force-all -i -B /tmp/v2ray-${V2RAY_VERSION}-arm64.deb
			rm -f /tmp/v2ray-${V2RAY_VERSION}-arm64.deb
		fi
#		else
#			[ "$ARCH" = "i386" ] && V2RAY_FILENAME="v2ray-linux-32.zip"
#			[ "$ARCH" = "amd64" ] && V2RAY_FILENAME="v2ray-linux-64.zip"
#			[ "$ARCH" = "armel" ] && V2RAY_FILENAME="v2ray-linux-arm32-v7a.zip"
#			[ "$ARCH" = "armhf" ] && V2RAY_FILENAME="v2ray-linux-arm32-v7a.zip"
#			[ "$ARCH" = "arm64" ] && V2RAY_FILENAME="v2ray-linux-arm64-v8a.zip"
#			[ "$ARCH" = "mips64el" ] && V2RAY_FILENAME="v2ray-linux-mips64le.zip"
#			[ "$ARCH" = "mipsel" ] && V2RAY_FILENAME="v2ray-linux-mips32le.zip"
#			[ "$ARCH" = "riscv64" ] && V2RAY_FILENAME="v2ray-linux-riscv64.zip"
#			wget -O /tmp/v2ray-${V2RAY_VERSION}.zip https://github.com/v2fly/v2ray-core/releases/download/v${V2RAY_VERSION}/${V2RAY_FILENAME}
#			cd /tmp
#			rm -rf v2ray
#			mkdir -p v2ray
#			cd v2ray
#			unzip /tmp/v2ray-${V2RAY_VERSION}.zip
#			cp v2ray /usr/bin/
#			cp geoip.dat /usr/bin/
#			cp geosite.dat /usr/bin/
#			wget -O /lib/systemd/system/v2ray.service ${VPS_CONFIG_URL}${VPSPATH}/v2ray.service
#		fi
	else
		apt-get -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-overwrite" -y install v2ray=${V2RAY_VERSION}
	fi
	if [ -f /etc/v2ray/v2ray-server.json ]; then
		V2RAY_UUID2=$(grep -Po '"'"id"'"\s*:\s*"\K([^"]*)' /etc/v2ray/v2ray-server.json | head -n 1 | tr -d "\n")
		[ -n "$V2RAY_UUID2" ] && V2RAY_UUID="$V2RAY_UUID2"
	fi
	#if [ ! -f /etc/v2ray/v2ray-server.json ]; then
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /etc/v2ray/v2ray-server.json ${VPS_CONFIG_URL}${VPSPATH}/v2ray-server.json
		else
			cp ${DIR}/v2ray-server.json /etc/v2ray/v2ray-server.json
		fi
		sed -i "s:V2RAY_UUID:$V2RAY_UUID:g" /etc/v2ray/v2ray-server.json
	#fi
	if [ -z "$(grep mptcp /etc/v2ray/v2ray-server.json | grep true)" ]; then
		sed -i 's/"sockopt": {/&\n                    "mptcp": true,/' /etc/v2ray/v2ray-server.json
	fi
	rm -f /etc/v2ray/config.json
	ln -s /etc/v2ray/v2ray-server.json /etc/v2ray/config.json
	#if [ -f /etc/systemd/system/v2ray.service.dpkg-dist ]; then
	#	mv -f /etc/systemd/system/v2ray.service.dpkg-dist /etc/systemd/system/v2ray.service
	#fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /lib/systemd/system/v2ray.service ${VPS_CONFIG_URL}${VPSPATH}/v2ray.service
	else
		cp ${DIR}/v2ray.service /lib/systemd/system/v2ray.service
	fi
	chmod 644 /lib/systemd/system/v2ray.service
	systemctl daemon-reload
	systemctl enable v2ray.service
	#if [ "$UPSTREAM" = "yes" ] || [ "$UPSTREAM6" = "yes" ]; then
	#	mptcpize enable v2ray
	#fi
fi

if systemctl -q is-active xray.service 2>/dev/null; then
	systemctl -q stop xray > /dev/null 2>&1
	systemctl -q disable xray > /dev/null 2>&1
fi

if [ "$XRAY" = "yes" ]; then
	#apt-get -y -o Dpkg::Options::="--force-overwrite" install xray
	#if [ "$SOURCES" = "yes" ] || [ "$ARCH" = "arm64" ]; then
	if [ "$ARCH" = "arm64" ]; then
		if [ "$ARCH" = "amd64" ]; then
			wget -O /tmp/xray-${XRAY_VERSION}-amd64.deb ${VPSURL}/debian/xray-${XRAY_VERSION}-amd64.deb
			rm -f /var/lib/dpkg/lock
			rm -f /var/lib/dpkg/lock-frontend
			dpkg --force-all -i -B /tmp/xray-${XRAY_VERSION}-amd64.deb
			rm -f /tmp/xray-${XRAY_VERSION}-amd64.deb
		elif [ "$ARCH" = "arm64" ]; then
			wget -O /tmp/xray-${XRAY_VERSION}-arm64.deb ${VPSURL}/debian/xray-${XRAY_VERSION}-arm64.deb
			rm -f /var/lib/dpkg/lock
			rm -f /var/lib/dpkg/lock-frontend
			dpkg --force-all -i -B /tmp/xray-${XRAY_VERSION}-arm64.deb
			rm -f /tmp/xray-${XRAY_VERSION}-arm64.deb
		fi
	else
		apt-get -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-overwrite" -y install xray=${XRAY_VERSION}
	fi
	if [ -f /etc/xray/xray-server.json ]; then
		XRAY_UUID2=$(grep -Po '"'"id"'"\s*:\s*"\K([^"]*)' /etc/xray/xray-server.json | head -n 1 | tr -d "\n")
		[ -n "$XRAY_UUID2" ] && [ "$XRAY_UUID2" != "XRAY_UUID" ] && [ "$XRAY_UUID2" != "V2RAY_UUID" ] && XRAY_UUID="$XRAY_UUID2"
		PSK2=$(jq -r '.inbounds[] | select(.tag=="omrin-shadowsocks-tunnel") | .settings.password' /etc/xray/xray-server.json | tr -d "\n")
		[ "$PSK2" != "null" ] && [ -n "$PSK2" ] && [ "$PSK2" != "XRAY_PSK" ] && PSK="$PSK2"
		UPSK2=$(jq -r '.inbounds[] | select(.tag=="omrin-shadowsocks-tunnel") | .settings.clients[] | select(.email=="openmptcprouter") | .password' /etc/xray/xray-server.json | tr -d "\n")
		[ "$UPSK2" != "null" ] && [ -n "$UPSK2" ] && [ "$UPSK2" != "XRAY_UPSK" ] && UPSK="$UPSK2"
		XRAY_X25519_PRIVATE_KEY2=$(grep -Po '"'"privateKey"'"\s*:\s*"\K([^"]*)' /etc/xray/xray-vless_reality.json | head -n 1 | tr -d "\n")
		[ -n "$XRAY_X25519_PRIVATE_KEY2" ] && [ "$XRAY_X25519_PRIVATE_KEY2" != "XRAY_X25519_PRIVATE_KEY" ] && XRAY_X25519_PRIVATE_KEY="$XRAY_X25519_PRIVATE_KEY2"
		XRAY_X25519_PUBLIC_KEY2=$(grep -Po '"'"publicKey"'"\s*:\s*"\K([^"]*)' /etc/xray/xray-vless_reality.json | head -n 1 | tr -d "\n")
		[ -n "$XRAY_X25519_PUBLIC_KEY2" ] && [ "$XRAY_X25519_PUBLIC_KEY2" != "XRAY_X25519_PUBLIC_KEY" ] && XRAY_X25519_PUBLIC_KEY="$XRAY_X25519_PUBLIC_KEY2"
		#jq -M 'del(.transport)' /etc/xray/xray-server.json > /etc/xray/xray-server.json.tmp
		#mv -f /etc/xray/xray-server.json.tmp /etc/xray/xray-server.json

	fi
	if [ -f /etc/openmptcprouter-vps-admin/omr-admin-config.json ]; then
		jq -M 'del(.users[0].openmptcprouter.xray)' /etc/openmptcprouter-vps-admin/omr-admin-config.json > /etc/openmptcprouter-vps-admin/omr-admin-config.json.new
		mv -f /etc/openmptcprouter-vps-admin/omr-admin-config.json /etc/openmptcprouter-vps-admin/omr-admin-config.json.bak
		mv -f /etc/openmptcprouter-vps-admin/omr-admin-config.json.new /etc/openmptcprouter-vps-admin/omr-admin-config.json
	fi
	if [ -f /etc/xray/xray-server.json ]; then
		jq -M 'del(.api.listen)' /etc/xray/xray-server.json > /etc/xray/xray-server.json.new
		mv -f /etc/xray/xray-server.json /etc/xray/xray-server.json.bak
		mv -f /etc/xray/xray-server.json.new /etc/xray/xray-server.json
	fi
	if [ ! -f /etc/xray/xray-server.json ] || [ -z "$(grep -i mptcp /etc/xray/xray-server.json | grep true)" ] || [ -z "$(grep -i transport /etc/xray/xray-server.json)" ]; then
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /etc/xray/xray-server.json ${VPS_CONFIG_URL}${VPSPATH}/xray-server.json
		else
			cp ${DIR}/xray-server.json /etc/xray/xray-server.json
		fi
		sed -i "s:XRAY_UUID:$XRAY_UUID:g" /etc/xray/xray-server.json
		sed -i "s:V2RAY_UUID:$XRAY_UUID:g" /etc/xray/xray-server.json
		sed -i "s:XRAY_PSK:$PSK:g" /etc/xray/xray-server.json
		sed -i "s:XRAY_UPSK:$UPSK:g" /etc/xray/xray-server.json
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /etc/xray/xray-vless-reality.json ${VPS_CONFIG_URL}${VPSPATH}/xray-vless-reality.json
		else
			cp ${DIR}/xray-vless-reality.json /etc/xray/xray-vless-reality.json
		fi
		if [ -z "$XRAY_X25519_PRIVATE_KEY" ]; then
			XRAY_X25519_KEYS=$(/usr/bin/xray x25519)
			XRAY_X25519_PRIVATE_KEY=$(echo "${XRAY_X25519_KEYS}" | grep Private | awk '{ print $3 }' | tr -d "\n")
			XRAY_X25519_PUBLIC_KEY=$(echo "${XRAY_X25519_KEYS}" | grep Public | awk '{ print $3 }' | tr -d "\n")
		fi
		sed -i "s:XRAY_UUID:$XRAY_UUID:g" /etc/xray/xray-vless-reality.json
		sed -i "s:XRAY_X25519_PRIVATE_KEY:$XRAY_X25519_PRIVATE_KEY:g" /etc/xray/xray-vless-reality.json
		sed -i "s:XRAY_X25519_PUBLIC_KEY:$XRAY_X25519_PUBLIC_KEY:g" /etc/xray/xray-vless-reality.json
		for xrayuser in $(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r '.users[0][].username'); do
			if [ "$xrayuser" != "admin" ] && [ "$xrayuser" != "openmptcprouter" ]; then
				xrayid="$(/usr/bin/xray uuid)"
				jq --arg xrayuser "$xrayuser" --arg xrayid "$xrayid" '(.inbounds[] | select(.tag=="omrin-tunnel") | .settings.clients) += [{"level": 0, "alterId": 0, "email": $xrayuser,"id": $xrayid}]' /etc/xray/xray-server.json > /etc/xray/xray-server.json.tmp
				mv /etc/xray/xray-server.json.tmp /etc/xray/xray-server.json
				jq --arg xrayuser "$xrayuser" --arg xrayid "$xrayid" '(.inbounds[] | select(.tag=="omrin-vmess-tunnel") | .settings.clients) += [{"level": 0, "alterId": 0, "email": $xrayuser,"id": $xrayid}]' /etc/xray/xray-server.json > /etc/xray/xray-server.json.tmp
				mv /etc/xray/xray-server.json.tmp /etc/xray/xray-server.json
				jq --arg xrayuser "$xrayuser" --arg xrayid "$xrayid" '(.inbounds[] | select(.tag=="omrin-socks-tunnel") | .settings.accounts) += [{"user": $xrayuser,"pass": $xrayid}]' /etc/xray/xray-server.json > /etc/xray/xray-server.json.tmp
				mv /etc/xray/xray-server.json.tmp /etc/xray/xray-server.json
				jq --arg xrayuser "$xrayuser" --arg xrayid "$xrayid" '(.inbounds[] | select(.tag=="omrin-trojan-tunnel") | .settings.clients) += [{"level": 0, "alterId": 0, "email": $xrayuser,"id": $xrayid}]' /etc/xray/xray-server.json > /etc/xray/xray-server.json.tmp
				mv /etc/xray/xray-server.json.tmp /etc/xray/xray-server.json
				[ -e /etc/shadowsocks-go/upsks.json ] && shadowsockspass="$(jq --arg xrayuser $xrayuser -r '.[$xrayuser]' /etc/shadowsocks-go/upsks.json)"
				[ -z "$shadowsockspass" ] && shadowsockspass=$(head -c 32 /dev/urandom | base64 -w0)
				jq --arg xrayuser "$xrayuser" --arg shadowsockspass "$shadowsockspass" '(.inbounds[] | select(.tag=="omrin-shadowsocks-tunnel") | .settings.clients) += [{"email": $xrayuser,"password": $shadowsockspass}]' /etc/xray/xray-server.json > /etc/xray/xray-server.json.tmp
				mv /etc/xray/xray-server.json.tmp /etc/xray/xray-server.json
			fi
		done
	fi
	#if ([ "$UPSTREAM" = "yes" ] || [ "$UPSTREAM6" = "yes" ]) && [ -z "$(grep mptcp /etc/xray/xray-server.json | grep true)" ]; then
	#	sed -i 's/"sockopt": {/&\n                    "mptcp": true,/' /etc/xray/xray-server.json
	#fi
	rm -f /etc/xray/config.json
	ln -s /etc/xray/xray-server.json /etc/xray/config.json
	#if [ -f /etc/systemd/system/xray.service.dpkg-dist ]; then
	#	mv -f /etc/systemd/system/xray.service.dpkg-dist /etc/systemd/system/xray.service
	#fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /lib/systemd/system/xray.service ${VPS_CONFIG_URL}${VPSPATH}/xray.service
	else
		cp ${DIR}/xray.service /lib/systemd/system/xray.service
	fi
	chmod 644 /lib/systemd/system/xray.service
	systemctl daemon-reload
	systemctl enable xray.service
fi

if systemctl -q is-active wg-quick@wg0.service 2>/dev/null; then
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

if systemctl -q is-active fail2ban.service 2>/dev/null; then
	systemctl -q stop fail2ban > /dev/null 2>&1
	systemctl -q disable fail2ban > /dev/null 2>&1
fi
if [ "$FAIL2BAN" = "yes" ]; then
	echo "Install Fail2ban"
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	apt-get -y install fail2ban python3-systemd
	systemctl enable fail2ban
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/fail2ban/jail.d/openmptcprouter.conf ${VPS_CONFIG_URL}${VPSPATH}/fail2ban-jail-openmptcprouter.conf
		wget -O /etc/fail2ban/filter.d/openvpn.conf ${VPS_CONFIG_URL}${VPSPATH}/fail2ban-filter-openvpn.conf
	else
		cp ${DIR}/fail2ban-jail-openmptcprouter.conf /etc/fail2ban/jail.d/openmptcprouter.conf
		cp ${DIR}/fail2ban-filter-openvpn.conf /etc/fail2ban/filter.d/openvpn.conf
	fi
	echo "Install Fail2ban done"
fi

if systemctl -q is-active openvpn-server@tun0.service 2>/dev/null; then
	systemctl -q stop openvpn-server@tun0 > /dev/null 2>&1
	systemctl -q disable openvpn-server@tun0 > /dev/null 2>&1
fi
if [ "$OPENVPN" = "yes" ]; then
	echo "Install OpenVPN"
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	apt-get -y --allow-downgrades install openvpn easy-rsa
	#wget -O /lib/systemd/network/openvpn.network ${VPS_CONFIG_URL}${VPSPATH}/openvpn.network
	rm -f /lib/systemd/network/openvpn.network
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
		./easyrsa --batch init-pki >/dev/null 2>&1
		./easyrsa --batch build-ca nopass
		EASYRSA_CERT_EXPIRE=3650 ./easyrsa --batch build-server-full server nopass
		EASYRSA_CERT_EXPIRE=3650 ./easyrsa --batch build-client-full "openmptcprouter" nopass
		EASYRSA_CRL_DAYS=3650 ./easyrsa --batch gen-crl
	fi
	chmod 644 /etc/openvpn/ca/pki/crl.pem >/dev/null 2>&1 || true
	if [ ! -f "/etc/openvpn/ca/pki/issued/openmptcprouter.crt" ]; then
		mv /etc/openvpn/ca/pki/issued/client.crt /etc/openvpn/ca/pki/issued/openmptcprouter.crt
		mv /etc/openvpn/ca/pki/private/client.key /etc/openvpn/ca/pki/private/openmptcprouter.key
	fi
	if [ ! -f "/etc/openvpn/server/dh2048.pem" ]; then
		openssl dhparam -out /etc/openvpn/server/dh2048.pem 2048
	fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/openvpn/tun0.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-tun0.6.1.conf
		wget -O /etc/openvpn/tun1.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-tun1.6.1.conf
		if [ "$OPENVPN_BONDING" = "yes" ]; then
			wget -O /etc/openvpn/bonding1.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-bonding1.conf
			wget -O /etc/openvpn/bonding2.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-bonding2.conf
			wget -O /etc/openvpn/bonding3.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-bonding3.conf
			wget -O /etc/openvpn/bonding4.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-bonding4.conf
			wget -O /etc/openvpn/bonding5.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-bonding5.conf
			wget -O /etc/openvpn/bonding6.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-bonding6.conf
			wget -O /etc/openvpn/bonding7.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-bonding7.conf
			wget -O /etc/openvpn/bonding8.conf ${VPS_CONFIG_URL}${VPSPATH}/openvpn-bonding8.conf
		fi
	else
		cp ${DIR}/openvpn-tun0.6.1.conf /etc/openvpn/tun0.conf
		cp ${DIR}/openvpn-tun1.6.1.conf /etc/openvpn/tun1.conf
		if [ "$OPENVPN_BONDING" = "yes" ]; then
			cp ${DIR}/openvpn-bonding1.conf /etc/openvpn/bonding1.conf
			cp ${DIR}/openvpn-bonding2.conf /etc/openvpn/bonding2.conf
			cp ${DIR}/openvpn-bonding3.conf /etc/openvpn/bonding3.conf
			cp ${DIR}/openvpn-bonding4.conf /etc/openvpn/bonding4.conf
			cp ${DIR}/openvpn-bonding5.conf /etc/openvpn/bonding5.conf
			cp ${DIR}/openvpn-bonding6.conf /etc/openvpn/bonding6.conf
			cp ${DIR}/openvpn-bonding7.conf /etc/openvpn/bonding7.conf
			cp ${DIR}/openvpn-bonding8.conf /etc/openvpn/bonding8.conf
		fi
	fi
	if [ "$(ip -6 a 2>/dev/null)" = "" ]; then
		sed -i 's/proto tcp6-server//' /etc/openvpn/tun0.conf
		sed -i 's/proto udp6//' /etc/openvpn/tun1.conf
		if [ "$OPENVPN_BONDING" = "yes" ]; then
			sed -i 's/proto udp6//' /etc/openvpn/bonding1.conf
			sed -i 's/proto udp6//' /etc/openvpn/bonding2.conf
			sed -i 's/proto udp6//' /etc/openvpn/bonding3.conf
			sed -i 's/proto udp6//' /etc/openvpn/bonding4.conf
			sed -i 's/proto udp6//' /etc/openvpn/bonding5.conf
			sed -i 's/proto udp6//' /etc/openvpn/bonding6.conf
			sed -i 's/proto udp6//' /etc/openvpn/bonding7.conf
			sed -i 's/proto udp6//' /etc/openvpn/bonding8.conf
		fi
	fi
	mkdir -p /etc/openvpn/ccd
	if [ ! -f /etc/openvpn/ccd/ipp_tcp.txt ]; then
		echo 'openmptcprouter,10.255.250.2,' > /etc/openvpn/ccd/ipp_tcp.txt
	fi
	if [ ! -f /etc/openvpn/ccd/ipp_udp.txt ]; then
		echo 'openmptcprouter,10.255.252.2,' > /etc/openvpn/ccd/ipp_udp.txt
	fi
	chmod 755 /etc/openvpn/ccd/
	chmod 644 /etc/openvpn/ccd/*
	chmod 644 /lib/systemd/system/openvpn*.service
	systemctl enable openvpn@tun0.service
	systemctl enable openvpn@tun1.service
	if [ "$OPENVPN_BONDING" = "yes" ]; then
		systemctl enable openvpn@bonding1.service
		systemctl enable openvpn@bonding2.service
		systemctl enable openvpn@bonding3.service
		systemctl enable openvpn@bonding4.service
		systemctl enable openvpn@bonding5.service
		systemctl enable openvpn@bonding6.service
		systemctl enable openvpn@bonding7.service
		systemctl enable openvpn@bonding8.service
	fi
fi

echo 'Glorytun UDP'
# Avoid package postinst hangs when TUN is unavailable on the VPS.
_check_tun_ready() {
	mkdir -p /dev/net >/dev/null 2>&1 || true
	[ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200 >/dev/null 2>&1 || true
	chmod 666 /dev/net/tun >/dev/null 2>&1 || true
	modprobe tun >/dev/null 2>&1 || true
	i=0
	while [ "$i" -lt 10 ]; do
		if ip tuntap add dev omr-tun-test mode tun >/dev/null 2>&1; then
			ip link del omr-tun-test >/dev/null 2>&1 || true
			return 0
		fi
		i=$((i + 1))
		sleep 1
	done
	return 1
}
GLORYTUN_TUN_READY="yes"
if [ "$GLORYTUN_UDP" = "yes" ] || [ "$GLORYTUN_TCP" = "yes" ]; then
	if ! _check_tun_ready; then
		echo "No working /dev/net/tun after retries: install Glorytun now, defer service start."
		GLORYTUN_TUN_READY="no"
	fi
fi
GLORYTUN_FORCE_SOURCE="yes"
echo "Debian 13 detected: build Glorytun from source (repo packages need libsodium.so.23)."
# Install Glorytun UDP
if systemctl -q is-active glorytun-udp@tun0.service 2>/dev/null; then
	systemctl -q stop 'glorytun-udp@*' > /dev/null 2>&1
fi
if [ "$GLORYTUN_UDP" = "yes" ]; then
	if [ "$SOURCES" = "yes" ] || [ "$ARCH" != "amd64" ] || [ "$GLORYTUN_FORCE_SOURCE" = "yes" ]; then
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		rm -f /usr/bin/glorytun
		apt-get -y install libsodium-dev || true
		apt-get install -y --no-install-recommends build-essential git ca-certificates meson pkg-config
		rm -rf /tmp/glorytun-udp
		cd /tmp
		git clone ${GLORYTUN_GIT_URL} /tmp/glorytun-udp
		cd /tmp/glorytun-udp
		git checkout ${GLORYTUN_UDP_VERSION}
		git submodule update --init --recursive
		meson build
		ninja -C build install
		sed -i 's:EmitDNS=yes:EmitDNS=no:g' /lib/systemd/network/glorytun.network || true
		rm -f /lib/systemd/system/glorytun*
		rm -f /lib/systemd/network/glorytun*
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /usr/local/bin/glorytun-udp-run ${VPS_CONFIG_URL}${VPSPATH}/glorytun-udp-run
		else
			cp ${DIR}/glorytun-udp-run /usr/local/bin/glorytun-udp-run
		fi
		chmod 755 /usr/local/bin/glorytun-udp-run
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /lib/systemd/system/glorytun-udp@.service ${VPS_CONFIG_URL}${VPSPATH}/glorytun-udp%40.service.in
		else
			cp ${DIR}/glorytun-udp@.service.in /lib/systemd/system/glorytun-udp@.service
		fi
		chmod 644 /lib/systemd/system/glorytun-udp@.service
		#wget -O /lib/systemd/network/glorytun-udp.network ${VPS_CONFIG_URL}${VPSPATH}/glorytun-udp.network
		rm -f /lib/systemd/network/glorytun-udp.network
		mkdir -p /etc/glorytun-udp
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /etc/glorytun-udp/post.sh ${VPS_CONFIG_URL}${VPSPATH}/glorytun-udp-post.sh
			wget -O /etc/glorytun-udp/tun0 ${VPS_CONFIG_URL}${VPSPATH}/tun0.glorytun-udp
		else
			cp ${DIR}/glorytun-udp-post.sh /etc/glorytun-udp/post.sh
			cp ${DIR}/tun0.glorytun-udp /etc/glorytun-udp/tun0
		fi
		chmod 755 /etc/glorytun-udp/post.sh
		echo "$GLORYTUN_PASS" > /etc/glorytun-udp/tun0.key
		systemctl enable glorytun-udp@tun0.service
		systemctl enable systemd-networkd.service
		cd /tmp
		rm -rf /tmp/glorytun-udp
	else
		rm -f /usr/local/bin/glorytun
		apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-overwrite" install --reinstall omr-glorytun=${GLORYTUN_UDP_BINARY_VERSION}
		chmod 644 /lib/systemd/system/glorytun-udp@.service
		GLORYTUN_PASS="$(cat /etc/glorytun-udp/tun0.key | tr -d '\n')"
	fi
	[ "$(ip -6 a 2>/dev/null)" != "" ] && sed -i 's/0.0.0.0/::/g' /etc/glorytun-udp/tun0
fi


# Add chrony for time sync
apt-get install -y chrony
systemctl enable chrony

if [ "$DSVPN" = "yes" ]; then
	echo 'A Dead Simple VPN'
	# Install A Dead Simple VPN
	if systemctl -q is-active dsvpn-server.service 2>/dev/null; then
		systemctl -q disable dsvpn-server > /dev/null 2>&1
		systemctl -q stop dsvpn-server > /dev/null 2>&1
	fi
	if [ "$SOURCES" = "yes" ] || [ "$ARCH" != "amd64" ]; then
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		apt-get install -y --no-install-recommends build-essential git ca-certificates
		rm -rf /tmp/dsvpn
		cd /tmp
		git clone ${DSVPN_GIT_URL} /tmp/dsvpn
		cd /tmp/dsvpn
		git checkout ${DSVPN_VERSION}
		make CFLAGS='-DNO_DEFAULT_ROUTES -DNO_DEFAULT_FIREWALL'
		make install
		rm -f /lib/systemd/system/dsvpn/*
		mkdir -p /etc/dsvpn
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /usr/local/bin/dsvpn-run ${VPS_CONFIG_URL}${VPSPATH}/dsvpn-run
			wget -O /lib/systemd/system/dsvpn-server@.service ${VPS_CONFIG_URL}${VPSPATH}/dsvpn-server%40.service.in
			wget -O /etc/dsvpn/dsvpn0 ${VPS_CONFIG_URL}${VPSPATH}/dsvpn0-config
		else
			cp ${DIR}/dsvpn-run /usr/local/bin/dsvpn-run
			cp ${DIR}/dsvpn-server@.service.in /lib/systemd/system/dsvpn-server@.service
			cp ${DIR}/dsvpn0-config /etc/dsvpn/dsvpn0
		fi
		chmod 755 /usr/local/bin/dsvpn-run
		chmod 644 /lib/systemd/system/dsvpn-server@.service
		if [ -f /etc/dsvpn/dsvpn.key ]; then
			mv /etc/dsvpn/dsvpn.key /etc/dsvpn/dsvpn0.key
		fi
		echo "$DSVPN_PASS" > /etc/dsvpn/dsvpn0.key
		systemctl enable dsvpn-server@dsvpn0.service
		cd /tmp
		rm -rf /tmp/dsvpn
	else
		apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-overwrite" install omr-dsvpn=${DSVPN_BINARY_VERSION}
		chmod 644 /lib/systemd/system/dsvpn-server@.service
		DSVPN_PASS=$(cat /etc/dsvpn/dsvpn0.key | tr -d "\n")
	fi
	if [ -n "$(ip addr | grep -m 1 inet6 2>/dev/null)" ]; then
		sed -i 's/0.0.0.0/::/' /etc/dsvpn/dsvpn0
	fi
	mptcpize enable dsvpn-server@dsvpn0 >/dev/null 2>&1
fi

if [ "$MQVPN" = "yes" ]; then
	echo 'MQVPN'
	if systemctl -q is-active mqvpn-server.service 2>/dev/null; then
		systemctl -q disable mqvpn-server > /dev/null 2>&1
		systemctl -q stop mqvpn-server > /dev/null 2>&1
	fi
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	apt-get install -y --no-install-recommends bash curl ca-certificates openssl iproute2 iptables iputils-ping libevent-dev
	MQVPN_ARTIFACT_SOURCE="$MQVPN_BINARY_URL"
	if [ "$LOCALFILES" = "yes" ] && [ -f "${DIR}/mqvpn-${MQVPN_VERSION}-linux-amd64.tar.gz" ]; then
		MQVPN_ARTIFACT_SOURCE="${DIR}/mqvpn-${MQVPN_VERSION}-linux-amd64.tar.gz"
	fi
	if [ -n "$MQVPN_ARTIFACT_SOURCE" ]; then
		rm -rf /tmp/mqvpn-artifact
		mkdir -p /tmp/mqvpn-artifact
		case "$MQVPN_ARTIFACT_SOURCE" in
			*.deb)
				omr_fetch_file "$MQVPN_ARTIFACT_SOURCE" /tmp/mqvpn-artifact/mqvpn.deb
				dpkg -i /tmp/mqvpn-artifact/mqvpn.deb
				[ -x /usr/bin/mqvpn ] && install -m 755 /usr/bin/mqvpn /usr/local/bin/mqvpn
				;;
			*)
				omr_fetch_file "$MQVPN_ARTIFACT_SOURCE" /tmp/mqvpn-artifact/mqvpn.tar.gz
				tar xzf /tmp/mqvpn-artifact/mqvpn.tar.gz -C /tmp/mqvpn-artifact
				if [ -x /tmp/mqvpn-artifact/bin/mqvpn ]; then
					install -m 755 /tmp/mqvpn-artifact/bin/mqvpn /usr/local/bin/mqvpn
					[ -d /tmp/mqvpn-artifact/lib ] && cp -a /tmp/mqvpn-artifact/lib/. /usr/local/lib/
				elif [ -x /tmp/mqvpn-artifact/mqvpn ]; then
					install -m 755 /tmp/mqvpn-artifact/mqvpn /usr/local/bin/mqvpn
				else
					echo 'ERROR: MQVPN artifact does not contain an mqvpn binary'
					exit 1
				fi
				;;
		esac
		rm -rf /tmp/mqvpn-artifact
	else
		apt-get install -y --no-install-recommends build-essential cmake pkg-config git libevent-dev
		rm -rf /tmp/mqvpn
		git clone --recursive "$MQVPN_GIT_URL" /tmp/mqvpn
		cd /tmp/mqvpn
		git checkout "$MQVPN_COMMIT"
		git submodule update --init --recursive
		./build.sh
		install -m 755 /tmp/mqvpn/build/mqvpn /usr/local/bin/mqvpn
		for lib in /tmp/mqvpn/build/libmqvpn.so* /tmp/mqvpn/third_party/xquic/build/libxquic.so*; do
			[ -e "$lib" ] && install -m 644 "$lib" /usr/local/lib/
		done
		rm -rf /tmp/mqvpn
	fi
	ldconfig >/dev/null 2>&1 || true
	if [ ! -x /usr/local/bin/mqvpn ]; then
		echo 'ERROR: MQVPN install failed: /usr/local/bin/mqvpn not found'
		exit 1
	fi
	mkdir -p /etc/mqvpn
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/mqvpn/server.conf ${VPS_CONFIG_URL}${VPSPATH}/mqvpn-server.conf
	else
		cp ${DIR}/mqvpn-server.conf /etc/mqvpn/server.conf
	fi
	sed -i "s:MQVPN_PASS:$MQVPN_PASS:g" /etc/mqvpn/server.conf
	sed -i "s:MQVPN_PORT:$MQVPN_PORT:g" /etc/mqvpn/server.conf
	omr_mqvpn_conf_set() {
		_omr_mqvpn_section="$1"
		_omr_mqvpn_key="$2"
		_omr_mqvpn_value="$3"
		_omr_mqvpn_file="/etc/mqvpn/server.conf"
		_omr_mqvpn_tmp="$(mktemp)"
		awk -v section="$_omr_mqvpn_section" -v key="$_omr_mqvpn_key" -v value="$_omr_mqvpn_value" '
			BEGIN {
				target = "[" section "]";
				in_section = 0;
				found_section = 0;
				wrote_key = 0;
			}
			/^\[[^]]+\][[:space:]]*$/ {
				if (in_section && !wrote_key) {
					print key " = " value;
					wrote_key = 1;
				}
				in_section = ($0 == target);
				if (in_section) found_section = 1;
				print;
				next;
			}
			{
				if (in_section && $0 ~ "^[[:space:]]*" key "[[:space:]]*=") {
					if (!wrote_key) {
						print key " = " value;
						wrote_key = 1;
					}
					next;
				}
				print;
			}
			END {
				if (!found_section) {
					print "";
					print target;
					print key " = " value;
				} else if (in_section && !wrote_key) {
					print key " = " value;
				}
			}
		' "$_omr_mqvpn_file" > "$_omr_mqvpn_tmp" && cat "$_omr_mqvpn_tmp" > "$_omr_mqvpn_file"
		rm -f "$_omr_mqvpn_tmp"
	}
	omr_mqvpn_conf_set Interface MTU 0
	omr_mqvpn_conf_set Multipath Scheduler wlb
	omr_mqvpn_conf_set Multipath CC cubic
	omr_mqvpn_conf_set Multipath OuterPacketSize 1400
	omr_mqvpn_conf_set Multipath PMTUD false
	omr_mqvpn_conf_set Multipath PMTUDProbeSize 1420
	chmod 0600 /etc/mqvpn/server.conf
	if [ ! -f /etc/mqvpn/server.key ] || [ ! -f /etc/mqvpn/server.crt ]; then
		openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
			-keyout /etc/mqvpn/server.key \
			-out /etc/mqvpn/server.crt \
			-subj "/C=US/ST=Oregon/L=Portland/O=OpenMPTCProuterVPS/OU=MQVPN/CN=mqvpn.openmptcprouter.vps"
		chmod 0600 /etc/mqvpn/server.key
		chmod 0644 /etc/mqvpn/server.crt
	fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /lib/systemd/system/mqvpn-server.service ${VPS_CONFIG_URL}${VPSPATH}/mqvpn-server.service.in
	else
		cp ${DIR}/mqvpn-server.service.in /lib/systemd/system/mqvpn-server.service
	fi
	chmod 644 /lib/systemd/system/mqvpn-server.service
	systemctl daemon-reload
	systemctl enable mqvpn-server.service
fi

if [ "$MQVPN2" = "yes" ]; then
	echo 'MQVPN2 (experimental)'
	if systemctl -q is-active mqvpn2-server.service 2>/dev/null; then
		systemctl -q disable mqvpn2-server.service > /dev/null 2>&1
		systemctl -q stop mqvpn2-server.service > /dev/null 2>&1
	fi
	rm -f /var/lib/dpkg/lock
	rm -f /var/lib/dpkg/lock-frontend
	apt-get install -y --no-install-recommends bash curl ca-certificates openssl iproute2 iptables iputils-ping libevent-dev
	MQVPN2_ARTIFACT_SOURCE="$MQVPN2_BINARY_URL"
	if [ "$LOCALFILES" = "yes" ] && [ -f "${DIR}/mqvpn2-${MQVPN2_VERSION}-linux-amd64.tar.gz" ]; then
		MQVPN2_ARTIFACT_SOURCE="${DIR}/mqvpn2-${MQVPN2_VERSION}-linux-amd64.tar.gz"
	fi
	if [ -n "$MQVPN2_ARTIFACT_SOURCE" ]; then
		rm -rf /tmp/mqvpn2-artifact
		mkdir -p /tmp/mqvpn2-artifact
		omr_fetch_file "$MQVPN2_ARTIFACT_SOURCE" /tmp/mqvpn2-artifact/mqvpn2.tar.gz
		if ! printf '%s  %s\n' "$MQVPN2_BINARY_SHA256" /tmp/mqvpn2-artifact/mqvpn2.tar.gz | sha256sum -c -; then
			echo 'ERROR: MQVPN2 artifact checksum mismatch'
			exit 1
		fi
		tar xzf /tmp/mqvpn2-artifact/mqvpn2.tar.gz -C /tmp/mqvpn2-artifact
		if [ -x /tmp/mqvpn2-artifact/bin/mqvpn2 ]; then
			install -m 755 /tmp/mqvpn2-artifact/bin/mqvpn2 /usr/local/bin/mqvpn2
		elif [ -x /tmp/mqvpn2-artifact/bin/mqvpn ]; then
			install -m 755 /tmp/mqvpn2-artifact/bin/mqvpn /usr/local/bin/mqvpn2
		elif [ -x /tmp/mqvpn2-artifact/mqvpn2 ]; then
			install -m 755 /tmp/mqvpn2-artifact/mqvpn2 /usr/local/bin/mqvpn2
		elif [ -x /tmp/mqvpn2-artifact/mqvpn ]; then
			install -m 755 /tmp/mqvpn2-artifact/mqvpn /usr/local/bin/mqvpn2
		else
			echo 'ERROR: MQVPN2 artifact does not contain an mqvpn or mqvpn2 binary'
			exit 1
		fi
		rm -rf /tmp/mqvpn2-artifact
	else
		apt-get install -y --no-install-recommends build-essential cmake pkg-config git libevent-dev patch
		MQVPN2_SOURCE_DIR=/var/tmp/mqvpn2
		rm -rf "$MQVPN2_SOURCE_DIR"
		git clone --recursive "$MQVPN2_GIT_URL" "$MQVPN2_SOURCE_DIR"
		cd "$MQVPN2_SOURCE_DIR"
		git checkout --detach "$MQVPN2_COMMIT"
		git submodule update --init --recursive
		if [ "$(git rev-parse HEAD)" != "$MQVPN2_COMMIT" ]; then
			echo "ERROR: MQVPN2 source is not the pinned commit $MQVPN2_COMMIT"
			exit 1
		fi
		MQVPN2_PATCH_SOURCE="${VPS_CONFIG_URL}${VPSPATH}/mqvpn2-datagram-stability.patch"
		if [ "$LOCALFILES" = "yes" ] && [ -f "${DIR}/mqvpn2-datagram-stability.patch" ]; then
			MQVPN2_PATCH_SOURCE="${DIR}/mqvpn2-datagram-stability.patch"
		fi
		omr_fetch_file "$MQVPN2_PATCH_SOURCE" /tmp/mqvpn2-datagram-stability.patch
		if ! printf '%s  %s\n' "$MQVPN2_PATCH_SHA256" /tmp/mqvpn2-datagram-stability.patch | sha256sum -c -; then
			echo 'ERROR: MQVPN2 stability patch checksum mismatch'
			exit 1
		fi
		if ! patch --batch --forward --fuzz=0 -p1 < /tmp/mqvpn2-datagram-stability.patch; then
			echo "ERROR: MQVPN2 stability patch does not apply to $MQVPN2_COMMIT"
			exit 1
		fi
		rm -f /tmp/mqvpn2-datagram-stability.patch
		MQVPN2_JOBS=$(nproc 2>/dev/null || echo 4)
		MQVPN2_BSSL_DIR="$MQVPN2_SOURCE_DIR/third_party/xquic/third_party/boringssl"
		MQVPN2_XQUIC_DIR="$MQVPN2_SOURCE_DIR/third_party/xquic"
		cmake -S "$MQVPN2_BSSL_DIR" -B "$MQVPN2_BSSL_DIR/build" \
			-DBUILD_SHARED_LIBS=0 \
			-DCMAKE_BUILD_TYPE=Release \
			-DCMAKE_C_FLAGS=-fPIC \
			-DCMAKE_CXX_FLAGS=-fPIC
		cmake --build "$MQVPN2_BSSL_DIR/build" --parallel "$MQVPN2_JOBS" --target ssl crypto
		cmake -S "$MQVPN2_XQUIC_DIR" -B "$MQVPN2_XQUIC_DIR/build" \
			-DCMAKE_BUILD_TYPE=Release \
			-DSSL_TYPE=boringssl \
			-DSSL_PATH="$MQVPN2_BSSL_DIR" \
			-DXQC_ENABLE_BBR2=ON \
			-DXQC_ENABLE_UNLIMITED=OFF \
			-DXQC_ENABLE_FEC=ON \
			-DXQC_ENABLE_XOR=ON
		cmake --build "$MQVPN2_XQUIC_DIR/build" --parallel "$MQVPN2_JOBS"
		cmake -S "$MQVPN2_SOURCE_DIR" -B "$MQVPN2_SOURCE_DIR/build" \
			-DCMAKE_BUILD_TYPE=Release \
			-DBUILD_TESTING=OFF \
			-DMQVPN_ENABLE_HYBRID_TCP_LANE=OFF \
			-DMQVPN_ENABLE_HYBRID_TCP_EGRESS=OFF \
			-DXQUIC_BUILD_DIR="$MQVPN2_XQUIC_DIR/build"
		cmake --build "$MQVPN2_SOURCE_DIR/build" --parallel "$MQVPN2_JOBS" --target mqvpn
		install -m 755 "$MQVPN2_SOURCE_DIR/build/mqvpn" /usr/local/bin/mqvpn2
		cd "$DIR"
		rm -rf "$MQVPN2_SOURCE_DIR"
	fi
	if [ ! -x /usr/local/bin/mqvpn2 ]; then
		echo 'ERROR: MQVPN2 install failed: /usr/local/bin/mqvpn2 not found'
		exit 1
	fi
	mkdir -p /etc/mqvpn2
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/mqvpn2/server.conf ${VPS_CONFIG_URL}${VPSPATH}/mqvpn2-server.conf
	else
		cp ${DIR}/mqvpn2-server.conf /etc/mqvpn2/server.conf
	fi
	sed -i "s:MQVPN2_PASS:$MQVPN2_PASS:g" /etc/mqvpn2/server.conf
	sed -i "s:MQVPN2_PORT:$MQVPN2_PORT:g" /etc/mqvpn2/server.conf
	sed -i "s:MQVPN2_SUBNET:$MQVPN2_SUBNET:g" /etc/mqvpn2/server.conf
	chmod 0600 /etc/mqvpn2/server.conf
	if [ ! -f /etc/mqvpn2/server.key ] || [ ! -f /etc/mqvpn2/server.crt ]; then
		openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
			-keyout /etc/mqvpn2/server.key \
			-out /etc/mqvpn2/server.crt \
			-subj "/C=US/ST=Oregon/L=Portland/O=OpenMPTCProuterVPS/OU=MQVPN2/CN=mqvpn2.openmptcprouter.vps"
		chmod 0600 /etc/mqvpn2/server.key
		chmod 0644 /etc/mqvpn2/server.crt
	fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /lib/systemd/system/mqvpn2-server.service ${VPS_CONFIG_URL}${VPSPATH}/mqvpn2-server.service.in
	else
		cp ${DIR}/mqvpn2-server.service.in /lib/systemd/system/mqvpn2-server.service
	fi
	chmod 644 /lib/systemd/system/mqvpn2-server.service
	systemctl daemon-reload
	systemctl enable mqvpn2-server.service
fi

# Install Glorytun TCP
if systemctl -q is-active glorytun-tcp@tun0.service 2>/dev/null; then
	systemctl -q stop 'glorytun-tcp@*' > /dev/null 2>&1
fi
if [ "$GLORYTUN_TCP" = "yes" ]; then
	echo "Install Glorytun-TCP..."
	if [ "$SOURCES" = "yes" ] || [ "$ARCH" != "amd64" ] || [ "$GLORYTUN_FORCE_SOURCE" = "yes" ]; then
		echo "install libsodium..."
		apt-get -y install libsodium-dev || true
		rm -f /var/lib/dpkg/lock
		rm -f /var/lib/dpkg/lock-frontend
		rm -f /usr/bin/glorytun-tcp
		echo "Install needed build tools..."
		apt-get -y install build-essential pkg-config autoconf automake || true
		rm -rf /tmp/glorytun-0.0.35
		cd /tmp
		echo "Clone glorytun"
		git clone ${GLORYTUN_GIT_URL} glorytun-0.0.35
		cd glorytun-0.0.35
		echo "checkout ${GLORYTUN_TCP_VERSION}"
		git checkout ${GLORYTUN_TCP_VERSION}
		echo "Patch Glorytun TCP"
		wget ${OMR_FEEDS_BASE_URL}/glorytun/patches/001-fix-compilation-errors-gcc14.patch
		wget ${OMR_FEEDS_BASE_URL}/glorytun/patches/002-fix-crypto-aead-pointer-types.patch
		patch -p1 < 001-fix-compilation-errors-gcc14.patch
		patch -p1 < 002-fix-crypto-aead-pointer-types.patch
		./autogen.sh
		./configure
		make
		cp glorytun /usr/local/bin/glorytun-tcp
		mkdir -p /etc/glorytun-tcp
		if [ "$LOCALFILES" = "no" ]; then
			wget -O /usr/local/bin/glorytun-tcp-run ${VPS_CONFIG_URL}${VPSPATH}/glorytun-tcp-run
			wget -O /lib/systemd/system/glorytun-tcp@.service ${VPS_CONFIG_URL}${VPSPATH}/glorytun-tcp%40.service.in
			wget -O /etc/glorytun-tcp/post.sh ${VPS_CONFIG_URL}${VPSPATH}/glorytun-tcp-post.sh
			wget -O /etc/glorytun-tcp/tun0 ${VPS_CONFIG_URL}${VPSPATH}/tun0.glorytun
		else
			cp ${DIR}/glorytun-tcp-run /usr/local/bin/glorytun-tcp-run
			cp ${DIR}/glorytun-tcp@.service.in /lib/systemd/system/glorytun-tcp@.service
			cp ${DIR}/glorytun-tcp-post.sh /etc/glorytun-tcp/post.sh
			cp ${DIR}/tun0.glorytun /etc/glorytun-tcp/tun0
		fi
		chmod 755 /usr/local/bin/glorytun-tcp-run
		chmod 644 /lib/systemd/system/glorytun-tcp@.service
		rm -f /lib/systemd/network/glorytun-tcp.network
		chmod 755 /etc/glorytun-tcp/post.sh
		echo "$GLORYTUN_PASS" > /etc/glorytun-tcp/tun0.key
		systemctl enable glorytun-tcp@tun0.service
		#systemctl enable systemd-networkd.service
		cd /tmp
		rm -rf /tmp/glorytun-0.0.35
	else
		rm -f /usr/local/bin/glorytun-tcp
		apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-overwrite" install --reinstall omr-glorytun-tcp=${GLORYTUN_TCP_BINARY_VERSION}
	fi
	[ "$(ip -6 a)" != "" ] && sed -i 's/0.0.0.0/::/g' /etc/glorytun-tcp/tun0
fi

if [ "$SOFTETHERVPN" = "yes" ]; then
	apt-get -y install softether-vpnserver
	mptcpize enable softether-vpnserver >/dev/null 2>&1
	set +e
	softether_test() {
		# Check if SoftEther VPN is available...
		result=1
		while ! $($@ About >/dev/null 2>&1); do
			sleep 1
			echo -n '.'
		done
		echo "Server ready for configuration..."
	}
	softether_password=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .softethervpn_admin_password | tr -d "\n")
	#echo "softether : $softether_password"
	if [ "$softether_password" = "null" ]; then
		#echo "Generate pass..."
		softether_password=$SOFTETHERVPN_PASS_ADMIN
		softetherrun="vpncmd 127.0.0.1:443 /SERVER /CSV /CMD"
		softether_test "$softetherrun"
		$softetherrun ServerPasswordSet $softether_password
		softetherdefault="vpncmd 127.0.0.1:443 /SERVER /CSV /PASSWORD:$softether_password"
		jq --arg softether_password $softether_password '. + {softethervpn_admin_password: $softether_password}' /etc/openmptcprouter-vps-admin/omr-admin-config.json > /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp
		mv -f /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp /etc/openmptcprouter-vps-admin/omr-admin-config.json
	else
		softetherdefault="vpncmd 127.0.0.1:65390 /SERVER /CSV /PASSWORD:$softether_password"
	fi

	softherether_user_name=$DEFAULT_USER
	softether_user_password=$(cat /etc/openmptcprouter-vps-admin/omr-admin-config.json | jq -r .users[0].openmptcprouter.softethervpn | tr -d "\n")
	#echo "softether user : $softether_user_password"
	if [ "$softether_user_password" = "null" ]; then
		#echo "Generate user password"
		softether_user_password=$SOFTETHERVPN_PASS_USER
		jq --arg softether_user_password $softether_user_password '(.users[0].openmptcprouter) += {softethervpn: $softether_user_password}' /etc/openmptcprouter-vps-admin/omr-admin-config.json > /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp
		mv -f /etc/openmptcprouter-vps-admin/omr-admin-config.json.tmp /etc/openmptcprouter-vps-admin/omr-admin-config.json
	fi

	softetherrun="$softetherdefault /CMD"
	softetherhubrun="$softetherdefault /HUB:OMRVPN /CMD"
	softether_test "$softetherrun"

	#echo "$softetherrun ServerPasswordSet $softether_password"
	$softetherrun ServerPasswordSet "$softether_password"
	#echo "$softetherrun HubCreate OMRVPN"
	$softetherrun HubCreate OMRVPN /PASSWORD:"$softether_password"
	#echo "$softetherrun HubDelete DEFAULT"
	$softetherrun HubDelete DEFAULT
	#echo "$softetherrun BridgeCreate OMRVPN /DEVICE:softether /TAP:yes"
	$softetherrun BridgeCreate OMRVPN /DEVICE:softether /TAP:yes
	#echo "$softetherhubrun DHCPSet OMRVPN /START:10.255.210.2 /END:10.255.210.254 /MASK:255.255.255.0 /EXPIRE:7200 /GW:10.255.210.1 /DNS:none /DNS2:none /DOMAIN:none /LOG:yes"
	$softetherhubrun DHCPSet /START:10.255.210.2 /END:10.255.210.254 /MASK:255.255.255.0 /EXPIRE:7200 /GW:10.255.210.1 /DNS:none /DNS2:none /DOMAIN:none /LOG:yes
	#echo "$softetherhubrun DHCPSet OMRVPN DhcpEnable"
	$softetherhubrun DhcpEnable
	#echo "$softetherhubrun SecureNatEnable OMRVPN"
	$softetherhubrun SecureNatEnable
	#echo "$softetherhubrun SecureNatHostSet /IP:10.255.210.1 /MAC:none /MASK:none"
	$softetherhubrun SecureNatHostSet /IP:10.255.210.1 /MAC:none /MASK:none
	#echo "$softetherhubrun NatEnable OMRVPN"
	$softetherhubrun NatEnable
	#echo "$softetherhubrun UserCreate ${softherether_user_name} /GROUP:none /REALNAME:none /NOTE:none"
	$softetherhubrun UserCreate ${softherether_user_name} /GROUP:none /REALNAME:none /NOTE:none
	#echo "$softetherhubrun UserPasswordSet ${softherether_user_name} /PASSWORD:${softether_user_password}"
	$softetherhubrun UserPasswordSet ${softherether_user_name} /PASSWORD:${softether_user_password}
	#echo "$softetherhubrun ListenerCreate OMRVPN 65390"
	$softetherhubrun ListenerCreate 65390
	$softetherhubrun ListenerEnable 65390
	softetherdefault="vpncmd 127.0.0.1:65390 /SERVER /CSV /PASSWORD:$softether_password"
	softetherhubrun="$softetherdefault /HUB:OMRVPN /CMD"
	$softetherhubrun ListenerDisable 443
	$softetherhubrun ListenerDisable 992
	$softetherhubrun ListenerDisable 1194
	$softetherhubrun ListenerDisable 5555
	$softetherhubrun PortsUDPSet 0
	set -e
fi

# Load tun module at boot time
if ! grep -q tun /etc/modules ; then
	echo tun >> /etc/modules
fi

# Add multipath utility
if [ "$LOCALFILES" = "no" ]; then
	wget -O /usr/local/bin/multipath ${VPS_CONFIG_URL}${VPSPATH}/multipath
else
	cp ${DIR}/multipath /usr/local/bin/multipath
fi
chmod 755 /usr/local/bin/multipath

# Add omr-test-speed utility
if [ "$LOCALFILES" = "no" ]; then
	wget -O /usr/local/bin/omr-test-speed ${VPS_CONFIG_URL}${VPSPATH}/omr-test-speed
else
	cp ${DIR}/omr-test-speed /usr/local/bin/omr-test-speed
fi
chmod 755 /usr/local/bin/omr-test-speed

# Add OpenMPTCProuter service
if [ "$LOCALFILES" = "no" ]; then
	wget -O /usr/local/bin/omr-service ${VPS_CONFIG_URL}${VPSPATH}/omr-service
	wget -O /lib/systemd/system/omr.service ${VPS_CONFIG_URL}${VPSPATH}/omr.service.in
	wget -O /usr/local/sbin/omr-nanbbr-var ${VPS_CONFIG_URL}${VPSPATH}/omr-nanbbr-var
	wget -O /lib/systemd/system/omr-nanbbr-var.service ${VPS_CONFIG_URL}${VPSPATH}/omr-nanbbr-var.service.in
	wget -O /usr/local/bin/omr-6in4-run ${VPS_CONFIG_URL}${VPSPATH}/omr-6in4-run
	wget -O /lib/systemd/system/omr6in4@.service ${VPS_CONFIG_URL}${VPSPATH}/omr6in4%40.service.in
	wget -O /usr/local/bin/omr-bypass ${VPS_CONFIG_URL}${VPSPATH}/omr-bypass
	wget -O /lib/systemd/system/omr-bypass.service ${VPS_CONFIG_URL}${VPSPATH}/omr-bypass.service.in
	wget -O /lib/systemd/system/omr-bypass.timer ${VPS_CONFIG_URL}${VPSPATH}/omr-bypass.timer.in
else
	cp ${DIR}/omr-service /usr/local/bin/omr-service
	cp ${DIR}/omr.service.in /lib/systemd/system/omr.service
	cp ${DIR}/omr-nanbbr-var /usr/local/sbin/omr-nanbbr-var
	cp ${DIR}/omr-nanbbr-var.service.in /lib/systemd/system/omr-nanbbr-var.service
	cp ${DIR}/omr-6in4-run /usr/local/bin/omr-6in4-run
	cp ${DIR}/omr6in4@.service.in /lib/systemd/system/omr6in4@.service
	cp ${DIR}/omr-bypass /usr/local/bin/omr-bypass
	cp ${DIR}/omr-bypass.service.in /lib/systemd/system/omr-bypass.service
	cp ${DIR}/omr-bypass.timer.in /lib/systemd/system/omr-bypass.timer

fi
chmod 644 /lib/systemd/system/omr.service
chmod 644 /lib/systemd/system/omr-nanbbr-var.service
chmod 644 /lib/systemd/system/omr6in4@.service
chmod 755 /usr/local/bin/omr-service
chmod 755 /usr/local/sbin/omr-nanbbr-var
chmod 755 /usr/local/bin/omr-bypass
chmod 755 /usr/local/bin/omr-6in4-run
chmod 644 /lib/systemd/system/omr-bypass.service
chmod 644 /lib/systemd/system/omr-bypass.timer
mkdir -p /etc/openmptcprouter-vps-admin
if [ ! -e /etc/openmptcprouter-vps-admin/nanbbr-var.json ]; then
	printf '{\n  "aggressiveness": 50,\n  "version": 1\n}\n' \
		> /etc/openmptcprouter-vps-admin/nanbbr-var.json
	chmod 644 /etc/openmptcprouter-vps-admin/nanbbr-var.json
fi
systemctl daemon-reload
if systemctl -q is-active omr-6in4.service 2>/dev/null; then
	systemctl -q stop omr-6in4 > /dev/null 2>&1
	systemctl -q disable omr-6in4 > /dev/null 2>&1
fi
systemctl enable omr6in4@user0.service
systemctl enable omr-nanbbr-var.service
systemctl enable omr.service
systemctl enable omr-bypass.timer
systemctl enable omr-bypass.service

# Change SSH port to 65222
sed -i 's:#Port 22:Port 65222:g' /etc/ssh/sshd_config
sed -i 's:Port 22:Port 65222:g' /etc/ssh/sshd_config

# Remove Bind9 if available
#systemctl -q disable bind9

# Remove fail2ban if available
#systemctl -q disable fail2ban

# Install and configure the firewall using shorewall.
	apt-get -y install shorewall shorewall6
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/shorewall/openmptcprouter-shorewall.tar.gz ${VPS_CONFIG_URL}${VPSPATH}/openmptcprouter-shorewall.tar.gz
	else
		cp ${DIR}/openmptcprouter-shorewall.tar.gz /etc/shorewall/openmptcprouter-shorewall.tar.gz
	fi
	tar xzf /etc/shorewall/openmptcprouter-shorewall.tar.gz -C /etc/shorewall
	rm /etc/shorewall/openmptcprouter-shorewall.tar.gz
	if [ -n "$INTERFACE" ]; then
		sed -i "s:eth0:$INTERFACE:g" /etc/shorewall/*
		systemctl enable shorewall
	fi
	if [ "$LOCALFILES" = "no" ]; then
		wget -O /etc/shorewall6/openmptcprouter-shorewall6.tar.gz ${VPS_CONFIG_URL}${VPSPATH}/openmptcprouter-shorewall6.tar.gz
	else
		cp ${DIR}/openmptcprouter-shorewall6.tar.gz /etc/shorewall6/openmptcprouter-shorewall6.tar.gz
	fi
	tar xzf /etc/shorewall6/openmptcprouter-shorewall6.tar.gz -C /etc/shorewall6
	rm /etc/shorewall6/openmptcprouter-shorewall6.tar.gz
	if [ -n "$INTERFACE6" ]; then
		sed -i "s:eth0:$INTERFACE6:g" /etc/shorewall6/*
		systemctl enable shorewall6
	fi
[ -z "$(grep nf_conntrack_sip /etc/modprobe.d/blacklist.conf)" ] && echo 'blacklist nf_conntrack_sip' >> /etc/modprobe.d/blacklist.conf
if [ "$(ip r | awk '/default/&&/src/ {print $7}')" != "" ] && [ "$(ip r | awk '/default/&&/src/ {print $7}')" != "dhcp" ]; then
	sed -i "s/MASQUERADE/SNAT($(ip r | awk '/default/&&/src/ {print $7}'))/" /etc/shorewall/snat
fi

# Bound persistent and volatile logs on small VPS disks.
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/openmptcprouter-storage.conf <<-'EOF'
	[Journal]
	Compress=yes
	SystemMaxUse=64M
	SystemKeepFree=512M
	SystemMaxFileSize=8M
	RuntimeMaxUse=16M
	RuntimeKeepFree=64M
	RuntimeMaxFileSize=4M
	MaxRetentionSec=14day
	MaxFileSec=1day
EOF
systemctl restart systemd-journald
journalctl --vacuum-size=64M >/dev/null 2>&1 || true

if [ "$BPFTUNE" = "yes" ]; then
	case "$BPFTUNE_LEARNING_RATE" in
		0|1|2|3|4) ;;
		*)
			echo "E: BPFTUNE_LEARNING_RATE must be between 0 and 4." >&2
			exit 1
			;;
	esac
	apt-get -y install bpftune
	mkdir -p /etc/systemd/system/bpftune.service.d
	cat > /etc/systemd/system/bpftune.service.d/10-openmptcprouter.conf <<-EOF
		[Service]
		ExecStart=
		ExecStart=/usr/sbin/bpftune --rollback --learning_rate ${BPFTUNE_LEARNING_RATE} --allow tcp_buffer_tuner.so --allow net_buffer_tuner.so --allow sysctl_tuner.so
	EOF
	systemctl daemon-reload
	systemctl enable bpftune
	systemctl restart bpftune
fi

if [ "$TLS" = "yes" ]; then
	VPS_CERT=0
	apt-get -y install socat cron
	if [ "$VPS_DOMAIN" != "" ] && [ "$(getent hosts $VPS_DOMAIN | awk '{ print $1; exit }')" != "" ] && [ "$(ping -c 1 -w 1 $VPS_DOMAIN)" ]; then
		if [ ! -f "/root/.acme.sh/$VPS_DOMAIN/$VPS_DOMAIN.cer" ]; then
			echo "Generate certificate for V2Ray"
			set +e
			#[ "$(shorewall  status | grep stopped)" = "" ] && shorewall open all all tcp 443
			curl https://get.acme.sh | sh
			systemctl -q restart shorewall
			~/.acme.sh/acme.sh --force --alpn --issue -d $VPS_DOMAIN --pre-hook 'shorewall open all all tcp 443 >/dev/null 2>&1' --post-hook 'shorewall close all all tcp 443 >/dev/null 2>&1' >/dev/null 2>&1
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

# Final kernel pin after all package installs/upgrades. Debian 13 can pull a
# newer stock kernel late in the installer, making it the first GRUB entry.
KREL="${KERNEL_VERSION}-${PSABI}-${OMR_KERNEL_SUFFIX}"
if [ -f "/boot/vmlinuz-${KREL}" ]; then
	linux-update-symlinks install "$KREL" "/boot/vmlinuz-${KREL}" >/dev/null 2>&1 || true
	if grep -q '^GRUB_TOP_LEVEL=' /etc/default/grub; then
		sed -i "s@^GRUB_TOP_LEVEL=.*@GRUB_TOP_LEVEL=\"/boot/vmlinuz-${KREL}\"@" /etc/default/grub
	else
		echo "GRUB_TOP_LEVEL=\"/boot/vmlinuz-${KREL}\"" >> /etc/default/grub
	fi
	sed -i "s@^\(GRUB_DEFAULT=\).*@\1\"0\"@" /etc/default/grub >/dev/null 2>&1
	sed -i '/^GRUB_SAVEDEFAULT=/d' /etc/default/grub >/dev/null 2>&1 || true
	for pkg in $(dpkg-query -W -f='${Package}\n' 'linux-image-[0-9]*' 2>/dev/null | grep -E 'linux-image-[0-9]+\.[0-9]+\.[0-9]+\+deb' || true); do
		PKGREL=$(echo "$pkg" | sed -e 's/^linux-image-//' -e 's/+.*$//')
		if dpkg --compare-versions "$PKGREL" gt "$KERNEL_VERSION" && [ "$pkg" != "linux-image-$(uname -r)" ]; then
			apt-get -y purge "$pkg" >/dev/null 2>&1 || true
		fi
	done
	apt-get -y purge linux-image-amd64 linux-headers-amd64 linux-image-cloud-amd64 linux-headers-cloud-amd64 >/dev/null 2>&1 || true
	[ -f /boot/grub/grub.cfg ] && grub-mkconfig -o /boot/grub/grub.cfg >/dev/null 2>&1
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
		sed -i "s:< OpenMPTCProuter VPS [^>]* >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd.head
		sed -i "s:< OpenMPTCProuter VPS [0-9]*\.[0-9]*\(\|-test[0-9]*\) >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd.head
		sed -i "s:< OpenMPTCProuter VPS [0-9]*\.[0-9]*\(\|-rolling[0-9]*\) >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd.head
		sed -i "s:< OpenMPTCProuter VPS [0-9]*\.[0-9]*\(\|-rolling-test[0-9]*\) >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd.head
		sed -i "s:< OpenMPTCProuter VPS \$OMR_VERSION >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd.head
	else
		echo "< OpenMPTCProuter VPS $OMR_VERSION >" >> /etc/motd.head
	fi
elif [ -f /etc/motd ]; then
	if grep --quiet 'OpenMPTCProuter VPS' /etc/motd; then
		sed -i "s:< OpenMPTCProuter VPS [^>]* >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd
		sed -i "s:< OpenMPTCProuter VPS [0-9]*\.[0-9]*\(\|-test[0-9]*\) >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd
		sed -i "s:< OpenMPTCProuter VPS [0-9]*\.[0-9]*\(\|-rolling[0-9]*\) >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd
		sed -i "s:< OpenMPTCProuter VPS [0-9]*\.[0-9]*\(\|-rolling-test[0-9]*\) >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd
		sed -i "s:< OpenMPTCProuter VPS \$OMR_VERSION >:< OpenMPTCProuter VPS $OMR_VERSION >:g" /etc/motd
	else
		echo "< OpenMPTCProuter VPS $OMR_VERSION >" >> /etc/motd
	fi
else
	echo "< OpenMPTCProuter VPS $OMR_VERSION >" > /etc/motd
fi

# Debian cloud images can enable networkd wait-online while the primary
# interface is managed by ifupdown. With no local networkd configuration the
# unit waits for two minutes and marks an otherwise healthy boot as degraded.
if systemctl -q is-active networking.service 2>/dev/null \
	&& ! find /etc/systemd/network /run/systemd/network -maxdepth 1 \
		-type f -name '*.network' -print -quit 2>/dev/null | grep -q .; then
	systemctl disable systemd-networkd-wait-online.service >/dev/null 2>&1 || true
	systemctl reset-failed systemd-networkd-wait-online.service >/dev/null 2>&1 || true
fi

# Install the inert profile marker only after every required component and
# configuration step has succeeded. It has no hooks or legacy dependencies;
# the fresh-only guard uses its installed state on subsequent runs.
apt-get -y install omr-server="${OMR_VERSION}"
rm -f /etc/openmtpcprouter-vps-admin/update-bin

if [ "$MQVPN" = "yes" ]; then
	# Keep MQVPN firewall integration explicit in the fresh install.
	if ! grep -Eq '^vpn[[:space:]]+mqvpn\+' /etc/shorewall/interfaces; then
		echo "vpn	mqvpn+		nosmurfs,tcpflags" >> /etc/shorewall/interfaces
	fi
	if ! grep -Eq '^ACCEPT[[:space:]]+mqvpn\+' /etc/shorewall/stoppedrules; then
		echo "ACCEPT          mqvpn+		-" >> /etc/shorewall/stoppedrules
	fi
	if ! grep -Eq '^ACCEPT[[:space:]]+-[[:space:]]+mqvpn\+' /etc/shorewall/stoppedrules; then
		echo "ACCEPT          -               mqvpn+" >> /etc/shorewall/stoppedrules
	fi
	if ! grep -q '10.255.249.0/24' /etc/shorewall/snat; then
		echo "MASQUERADE		10.255.249.0/24		\$NET_IFACE" >> /etc/shorewall/snat
	fi
fi

if [ "$MQVPN2" = "yes" ]; then
	# omr-server can refresh /etc/shorewall from package defaults; re-apply
	# the isolated MQVPN2 interface and SNAT rules after package install.
	if ! grep -Eq '^vpn[[:space:]]+mqvpn2([[:space:]]|$)' /etc/shorewall/interfaces; then
		echo "vpn	mqvpn2		nosmurfs,tcpflags" >> /etc/shorewall/interfaces
	fi
	if ! grep -Eq '^ACCEPT[[:space:]]+mqvpn2([[:space:]]|$)' /etc/shorewall/stoppedrules; then
		echo "ACCEPT          mqvpn2		-" >> /etc/shorewall/stoppedrules
	fi
	if ! grep -Eq '^ACCEPT[[:space:]]+-[[:space:]]+mqvpn2([[:space:]]|$)' /etc/shorewall/stoppedrules; then
		echo "ACCEPT          -               mqvpn2" >> /etc/shorewall/stoppedrules
	fi
	if ! grep -Fq "$MQVPN2_SUBNET" /etc/shorewall/snat; then
		echo "MASQUERADE		$MQVPN2_SUBNET		\$NET_IFACE" >> /etc/shorewall/snat
	fi
fi

# Display important info for the completed fresh installation.
	echo '===================================================================================='
	echo "OpenMPTCProuter Server $OMR_VERSION is now installed !"
	echo '\033[1m SSH port: 65222 (instead of port 22)\033[0m'
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
	if [ "$SHADOWSOCKS" = "yes" ]; then
		echo 'Shadowsocks port: 65101'
		echo 'Shadowsocks encryption: chacha20'
		echo 'Your shadowsocks key: '
		echo $SHADOWSOCKS_PASS
	fi
	if [ "$SHADOWSOCKS_GO" = "yes" ]; then
		echo 'Your shadowsocks 2022 key: '
		echo "${PSK}:${UPSK}"
	fi
	echo 'Glorytun port: 65001'
	echo 'Glorytun encryption: chacha20'
	echo 'Your glorytun key: '
	echo $GLORYTUN_PASS
	if [ "$DSVPN" = "yes" ]; then
		echo 'A Dead Simple VPN port: 65401'
		echo 'A Dead Simple VPN key: '
		echo $DSVPN_PASS
	fi
	if [ "$MQVPN" = "yes" ]; then
		echo "MQVPN port: $MQVPN_PORT"
		echo 'Your MQVPN key: '
		echo $MQVPN_PASS
	fi
	if [ "$MQVPN2" = "yes" ]; then
		echo "MQVPN2 experimental port: $MQVPN2_PORT"
		echo 'Your MQVPN2 key: '
		echo $MQVPN2_PASS
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
	if [ "$OMR_ADMIN" = "yes" ]; then
		systemctl reset-failed omr-admin.service >/dev/null 2>&1 || true
		systemctl restart omr-admin.service >/dev/null 2>&1 || true
	fi
	echo '===================================================================================='
	echo 'Keys are also saved in /root/openmptcprouter_config.txt, you are free to remove them'
	echo '===================================================================================='
	echo '\033[1m  /!\ You need to reboot to enable MPTCP, shadowsocks, glorytun and shorewall /!\ \033[0m'
	echo '------------------------------------------------------------------------------------'
		echo ' After reboot, verify that the OMR 6.12 kernel is running with uname -r.'
	echo '===================================================================================='

	# Save info in file
	cat > /root/openmptcprouter_config.txt <<-EOF
	SSH port: 65222 (instead of port 22)
	EOF
	if [ "$SHADOWSOCKS" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		Shadowsocks port: 65101
		Shadowsocks encryption: chacha20
		Your shadowsocks key: ${SHADOWSOCKS_PASS}
		EOF
	fi
	if [ "$SHADOWSOCKS_GO" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		Your shadowsocks 2022 key: ${PSK}:${UPSK}
		EOF
	fi
	if ([ "$GLORYTUN_TCP" = "yes" ] || [ "$GLORYTUN_UDP" = "yes" ]); then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		Glorytun port: 65001
		Glorytun encryption: chacha20
		Your glorytun key: ${GLORYTUN_PASS}
		EOF
	fi
	if [ "$DSVPN" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		A Dead Simple VPN port: 65401
		A Dead Simple VPN key: ${DSVPN_PASS}
		EOF
	fi
	if [ "$MQVPN" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		MQVPN port: $MQVPN_PORT
		MQVPN version: $MQVPN_VERSION
		Your MQVPN key: $MQVPN_PASS
		EOF
	fi
	if [ "$MQVPN2" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		MQVPN2 experimental port: $MQVPN2_PORT
		MQVPN2 version: $MQVPN2_VERSION
		MQVPN2 commit: $MQVPN2_COMMIT
		Your MQVPN2 key: $MQVPN2_PASS
		EOF
	fi
	if [ "$OMR_ADMIN" = "yes" ]; then
		cat >> /root/openmptcprouter_config.txt <<-EOF
		Your OpenMPTCProuter ADMIN API Server key (only for configuration via API access, you don't need it): $OMR_ADMIN_PASS_ADMIN
		Your OpenMPTCProuter Server key: $OMR_ADMIN_PASS
		Your OpenMPTCProuter Server username: openmptcprouter
		EOF
		fi
systemctl -q restart ssh >/dev/null 2>&1 || systemctl -q restart sshd >/dev/null 2>&1 || true
exit 0
