# OpenMPTCProuter VPS Fork (`omr-vps-0.1028-def`)

This branch is a maintained fork of the historical `0.1028` VPS installer, made to support older OMR clients (for example `0.59.x`) with predictable behavior.

## Scope

- Target OS is **Debian 11 (Bullseye) only**.
- The installer is intentionally strict and does not support Debian 9/10/12/13.
- Goal is a stable legacy-compatible VPS deployment, not feature parity with newer upstream releases.

## What Is Changed In This Fork

- Removed dependency on unstable upstream endpoints and switched to fork-controlled sources.
- Kept the `0.1028` stack and package behavior expected by legacy clients.
- Upgraded Glorytun TCP package from `0.0.35-3` to `0.0.35-6`.
- OpenVPN bonding services are disabled by default(they usually dont work and when they do is terrible).
- Added hardening for `omr-admin` runtime on modern Debian 11 images:
  - Force compatible Python stack: `pydantic<2`, `fastapi<0.100`, `starlette<0.28`, `uvloop<0.20`.
  - Create `/etc/shorewall/params.net` and `/etc/shorewall6/params.net` early to avoid startup race/crash.
  - Reset/restart `omr-admin` services at install end for clean first boot.
- Installer still moves SSH to port `65222` at the end (expected behavior).

## Clean Install

If `curl` is missing on a fresh Debian 11 VM:

```bash
apt-get update && apt-get install -y curl
```

Run installer:

```bash
curl -sL https://raw.githubusercontent.com/Brazzo978/openmptcprouter-vps/omr-vps-0.1028-def/debian9-x86_64.sh | bash
```

## Expected Result

- Installer completes without manual patching.
- SSH moves from `22` to `65222`.
- OMR API listens on `65500`.
- `omr-admin` and `omr-admin-ipv6` are active after install.
- Reboot is required to boot into the installed MPTCP kernel (`5.4.207-mptcp`).
