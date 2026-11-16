# Dashboard candidate validation — 2026-11-16

Candidate API: **0.18+20261030-3k11**. Compatible source branch for the
0.64.2/0.64.3 client generation; no router firmware was rebuilt.

## Completed checks

- Linux combined API/VPS suite: **1,281 passed, 9 skipped** (optional PyTorch
  dependency absent). One pytest collection warning, no test failures.
- Focused dashboard/authentication/package-guard suite: **42 passed**.
- JavaScript syntax checked with `node --check`.
- Actual Debian package built on a POSIX staging filesystem. Wrapper prepare
  guards passed; extracted module, static assets and collector unit hashes
  matched source. Test fixtures are excluded from the package.
- Post-install shell syntax and `systemd-analyze verify` passed. This is
  static unit verification, not a running production systemd service test.
- Browser checks with synthetic data: successful/failed login, logout,
  parameter search, light/dark theme, desktop and 390px mobile layout without
  whole-page horizontal overflow, service/peer/event views, stale HTTP 200,
  HTTP 503 with previous data retained, unavailable collector and recovery.
- Browser localStorage/sessionStorage contained no login token. The UI made
  no configuration or network/service mutation calls.
- Anonymous/router/read-only identities cannot retrieve the fleet snapshot.
  Existing API homepage remains compatible. Failed observation persistence
  cannot break router authentication.
- Historical timestamps after a telemetry gap are explicitly observations,
  with uncertainty retained in both the API and UI.

## Explicit limits

The user requested **package and preview only, with no VPS installation**.
No live VPS was changed, no installed-image behavior is claimed and the
published VPS release archive was not replaced. The UI preview contains only
synthetic identities, counters and events. It does not show a connected VPS.

Before promotion, install the candidate on an agreed test VPS and verify
the actual collector under systemd, API administrator login, client contacts,
MQVPN/other transport observations, RTH gates and peer data. Recheck DNS,
forwarding and normal client synchronization after the API restart.
