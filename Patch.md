# Manual Client Patch (0.59.x)

Use this only if the client is already installed and you cannot reinstall with a pre-patched image.

## What This Patch Fixes

- Prevents concurrent `post-tracking` executions (lock in `omr-tracker`).
- Ignores backup files in `/usr/share/omr/post-tracking.d/` to avoid duplicate execution.
- Fixes IPv6 tracker variable usage (`OMR_TRACKER_IPV6`).
- Avoids false `ip issues` errors when IPv6 is disabled.
- Fixes IPv6 error message source IP usage.
- Fixes shell test typo in `post-tracking`.

## Files Used

- `CLIENT/patches/omr-tracker`
- `CLIENT/patches/post-tracking`

## Apply On Client

1. Copy patched files to the client:

```bash
scp CLIENT/patches/omr-tracker root@<CLIENT_IP>:/tmp/omr-tracker
scp CLIENT/patches/post-tracking root@<CLIENT_IP>:/tmp/post-tracking
```

2. Install with backups and restart tracker:

```bash
ssh root@<CLIENT_IP> <<'EOF'
set -e
cp -a /bin/omr-tracker /root/omr-tracker.bak-$(date +%Y%m%d-%H%M%S)
cp -a /usr/share/omr/post-tracking.d/post-tracking /root/post-tracking.bak-$(date +%Y%m%d-%H%M%S)

install -m 0755 /tmp/omr-tracker /bin/omr-tracker
install -m 0755 /tmp/post-tracking /usr/share/omr/post-tracking.d/post-tracking

sh -n /bin/omr-tracker
sh -n /usr/share/omr/post-tracking.d/post-tracking

/etc/init.d/omr-tracker restart
EOF
```

## Recommended Tracker Settings

```bash
ssh root@<CLIENT_IP> <<'EOF'
uci set omr-tracker.omrvpn.restart_down='1'
uci set omr-tracker.omrvpn.wait_test='5'
uci commit omr-tracker
/etc/init.d/omr-tracker restart
EOF
```
