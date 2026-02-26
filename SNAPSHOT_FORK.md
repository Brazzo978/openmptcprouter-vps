# OMR VPS snapshot fork (no Ysurac dependency)

This snapshot installer defaults to the `Brazzo978` namespace and no longer pulls runtime artifacts from Ysurac URLs.

## Required repos/mirrors in your namespace

- `openmptcprouter-vps` (this repo)
- `openmptcprouter-vps-debian` (APT pool + `openmptcprouter.gpg.key`)
- `openmptcprouter-vps-admin`
- `mptcpize`
- `shadowsocks-libev`
- `glorytun`
- `dsvpn`
- `openmptcprouter-feeds`
- `openmptcprouter-vps-artifacts` (for `kernel/` and `debian/` files referenced by installer)

## Important defaults in installer

- `CHINA=yes` (uses git-based local repo path by default)
- `LOCALFILES=yes` (uses local templates from cloned `openmptcprouter-vps`)
- `OMR_GITHUB_ORG=Brazzo978`
- `OMR_VPS_BRANCH=omr-vps-0.1048-def`
- `REPO=repoomr.3klab.com`
- `VPSURL=https://repoomr.3klab.com/`
- Debian requirement: `Debian 12` or `Debian 13` only
- On fresh install (`update=0`), Debian 12 is upgraded to Debian 13 automatically

## Override example

```bash
OMR_GITHUB_ORG=MyOrg \
OMR_VPS_BRANCH=omr-vps-0.1048-def \
OMR_VPS_DEBIAN_BRANCH=main \
VPSURL=https://raw.githubusercontent.com/MyOrg/openmptcprouter-vps-artifacts/main/ \
./debian12-x86_64.sh
```

If your artifacts are not under `kernel/` and `debian/` in `VPSURL`, update the script or provide a matching layout.
