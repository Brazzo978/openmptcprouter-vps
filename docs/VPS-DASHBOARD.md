# VPS monitoring dashboard

The API **0.18+20261030-3k11** source candidate adds a read-only dashboard for
the existing 0.64.2/0.64.3 client generation. It does not require new router
firmware and does not apply profiles or change networking. This candidate
must be tested before it replaces a published VPS installation archive.

Open **`https://VPS_ADDRESS:65500/dashboard/`**, using the configured API port
if it differs from 65500. The dashboard shares the API's existing HTTPS
listener and certificate; it does not bind public ports 80 or 443. The API
homepage remains unchanged for client reachability checks.

Sign in with the VPS API **administrator** account, normally `admin`, and its
installer-generated API administrator password. This is separate from SSH
root credentials and the `openmptcprouter` router account. Existing passwords
are preserved. Router and read-only router accounts cannot retrieve the
dashboard's fleet-wide snapshot.

## Information shown

- VPS version, kernel, uptime, load and memory; kernel MPTCP scheduler and
  congestion-control defaults, available controls and service state.
- Configured router identities, VPN and proxy selections, tunnel address,
  available ports and safe settings, LAN prefixes and RTH state.
- MQVPN session observations, live path measurements where reported, MTU
  and interface observations, FEC, reordering, congestion and scheduler data.
- Last authenticated API contact and connection/disconnection transitions
  observed by the collector, with a bounded persistent history.
- Return-to-home peers: names, addresses, enabled state, latest handshake,
  transfer counters and requested versus effective LAN permission. The global
  LAN gate is displayed separately.
- Searchable grouped parameters, a light/dark appearance and a responsive
  mobile layout. No controls change settings or restart services.

All server data passes explicit allowlists. API passwords, auth tokens,
WireGuard keys, private profiles and QR codes are not part of the dashboard
payload. Static assets are self-contained; no CDN, external font or analytics
service is needed. The browser keeps its login token in memory only, clears
it on sign-out and requires a new login after a reload.

## Evidence and unavailable values

Configured VPN/proxy choices do not prove that their sessions are active.
MQVPN session data, kernel interfaces, service state, observed TCP sockets
and authenticated API contacts are separate observations. A service being
active does not mean every configured router is connected. TCP observations
do not verify the peer's application authentication. Shared ports cannot
identify an individual user and are reported as unavailable.

MPTCP values read from VPS procfs are **VPS kernel defaults**, not the router's
current settings or proof that all existing sockets use those defaults.
The old clients do not report every requested parameter; absent telemetry
is labelled unavailable rather than replaced with a fabricated healthy zero.
Interface counters cover the interface, not a single router session.

A recent WireGuard handshake is not proof of GUI/LAN reachability. The global
LAN setting, per-peer requested permission and live firewall grants are
shown separately, including mismatches. Existing RTH routing and access
requirements still apply; this dashboard does not add permissions.

## Collection and history

`omr-dashboard-collector.service` samples independently of browser access,
normally every 15 seconds. Fixed read-only commands have per-command and
per-cycle time limits. The HTTPS data route reads a cached snapshot instead
of querying every service on each browser request.

The collector writes only its own runtime/state files:

- `/run/omr-dashboard/snapshot.json`: current snapshot, regenerated after boot.
- `/var/lib/omr-dashboard/history.json`: bounded sanitized contact/transition
  history, protected by a cross-process lock.

Directories are owner-only and files are created with private permissions.
The history begins when collection starts: it does not reconstruct earlier
connections. Times describe the collector's observations, with sampling
resolution, rather than precise packet-level connection timestamps.
Events first observed after a telemetry or collector gap are explicitly
marked; their timestamp is the observation time, not the unknown failure time.
Snapshots older than 60 seconds are visibly stale. Refresh failures retain
the previous display with a warning; an unavailable collector is not shown
as a fleet of healthy clients.

## Installation and verification

Build with `./run-vps-3k.sh prepare`; it includes the dashboard module,
HTML/CSS/JS and collector unit in the reviewed API package. Installing the
API package enables the collector and restarts the API. It does not restart
MQVPN or WireGuard, replace keys or run the full VPS installer. Take the
normal service/configuration backup and verify the candidate on a test VPS
before deploying it to customer systems.

After installation, check `systemctl status omr-dashboard-collector` and
`omr-admin`, sign in to the dashboard, compare its observations with the
server state and verify the old client API, DNS, forwarding and RTH still
work. Never publish a UI fixture as evidence of a real connected VPS.
