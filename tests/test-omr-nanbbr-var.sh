#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/omr-nanbbr-var-test.XXXXXX)"
trap 'rm -rf "$TEST_ROOT"' EXIT

for module in tcp_nanbbr1_var tcp_nanbbr2_var; do
	mkdir -p "$TEST_ROOT/sys/module/$module/parameters"
done
printf '41\n' > "$TEST_ROOT/sys/module/tcp_nanbbr1_var/parameters/aggressiveness"
printf '42\n' > "$TEST_ROOT/sys/module/tcp_nanbbr2_var/parameters/aggressiveness"
printf '{"version":1,"aggressiveness":88}\n' > "$TEST_ROOT/config.json"

mkdir -p "$TEST_ROOT/bin"
cat > "$TEST_ROOT/bin/cat" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "$FAIL_PARAMETER" ]; then
	count=0
	if [ -f "$CAT_STATE" ]; then
		count="$("$REAL_CAT" "$CAT_STATE")"
	fi
	count=$((count + 1))
	printf '%s\n' "$count" > "$CAT_STATE"
	if [ "$count" -eq 2 ]; then
		printf 'readback-mismatch\n'
		exit 0
	fi
fi
exec "$REAL_CAT" "$@"
EOF
chmod 755 "$TEST_ROOT/bin/cat"

export REAL_CAT
REAL_CAT="$(command -v cat)"
export FAIL_PARAMETER="$TEST_ROOT/sys/module/tcp_nanbbr2_var/parameters/aggressiveness"
export CAT_STATE="$TEST_ROOT/cat-state"

if PATH="$TEST_ROOT/bin:$PATH" \
	NANBBR_CONFIG="$TEST_ROOT/config.json" \
	NANBBR_LOCK="$TEST_ROOT/lock" \
	NANBBR_SYS_MODULE_ROOT="$TEST_ROOT/sys/module" \
	NANBBR_MODPROBE=/bin/true \
	"$REPO_ROOT/omr-nanbbr-var"; then
	echo "expected second parameter readback to fail" >&2
	exit 1
fi

test "$("$REAL_CAT" "$TEST_ROOT/sys/module/tcp_nanbbr1_var/parameters/aggressiveness")" = 41
test "$("$REAL_CAT" "$TEST_ROOT/sys/module/tcp_nanbbr2_var/parameters/aggressiveness")" = 42

NANBBR_CONFIG="$TEST_ROOT/config.json" \
	NANBBR_LOCK="$TEST_ROOT/lock" \
	NANBBR_SYS_MODULE_ROOT="$TEST_ROOT/sys/module" \
	NANBBR_MODPROBE=/bin/true \
	"$REPO_ROOT/omr-nanbbr-var"
test "$("$REAL_CAT" "$TEST_ROOT/sys/module/tcp_nanbbr1_var/parameters/aggressiveness")" = 88
test "$("$REAL_CAT" "$TEST_ROOT/sys/module/tcp_nanbbr2_var/parameters/aggressiveness")" = 88

mkdir -p "$TEST_ROOT/empty-sys/module"
if NANBBR_CONFIG="$TEST_ROOT/config.json" \
	NANBBR_LOCK="$TEST_ROOT/empty-lock" \
	NANBBR_SYS_MODULE_ROOT="$TEST_ROOT/empty-sys/module" \
	NANBBR_MODPROBE=/bin/true \
	"$REPO_ROOT/omr-nanbbr-var"; then
	echo "expected zero available parameters to fail" >&2
	exit 1
fi

echo "NanBBR var apply, rollback and capability tests: ok"
