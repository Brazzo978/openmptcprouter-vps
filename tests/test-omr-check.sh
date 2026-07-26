#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/omr-check-test.XXXXXX)"
trap 'rm -rf "$TEST_ROOT"' EXIT
mkdir -p "$TEST_ROOT/bin"

cat > "$TEST_ROOT/bin/sysctl" <<'EOF'
#!/usr/bin/env bash
case "${*: -1}" in
	net.mptcp.scheduler) printf 'default\n' ;;
	net.ipv4.tcp_congestion_control) printf 'bbr\n' ;;
esac
EOF

cat > "$TEST_ROOT/bin/systemctl" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat > "$TEST_ROOT/bin/ss" <<'EOF'
#!/usr/bin/env bash
if [[ " $* " == *" -Huanp "* ]]; then
	printf '%s\n' \
		'UNCONN 0 0 0.0.0.0:65411 0.0.0.0:* users:(("mqvpn",pid=10,fd=4))' \
		'UNCONN 0 0 [::]:65412 [::]:* users:(("mqvpn2",pid=11,fd=4))' \
		'UNCONN 0 0 0.0.0.0:65413 *:* users:(("dsvpn",pid=12,fd=4))'
	if [ "${SS_CONNECTED:-0}" = 1 ]; then
		printf '%s\n' \
			'ESTAB 0 0 10.255.249.1:65411 198.51.100.8:44444 users:(("mqvpn",pid=10,fd=4))'
	fi
fi
EOF
chmod 755 "$TEST_ROOT/bin/"*

output="$(PATH="$TEST_ROOT/bin:$PATH" "$REPO_ROOT/omr-check")"
grep -Fq 'VPN in use now: none detected' <<<"$output"
grep -Eq '^mqvpn +state=active +iface=mqvpn0 +peer_reachable=no$' <<<"$output"
grep -Eq '^mqvpn2 +state=active +iface=mqvpn2 +peer_reachable=no$' <<<"$output"
if grep -Eq '0\.0\.0\.0:\*|\[::\]:\*|\*:\*' <<<"$output"; then
	echo "wildcard UDP endpoint reported as a peer" >&2
	exit 1
fi

output="$(SS_CONNECTED=1 PATH="$TEST_ROOT/bin:$PATH" "$REPO_ROOT/omr-check")"
grep -Fq 'VPN in use now: mqvpn' <<<"$output"
grep -Fq 'peers: 198.51.100.8:44444' <<<"$output"

echo "omr-check UDP wildcard peer tests: ok"
