# Road-warrior WireGuard client manager (next 3K build)

This document describes the development candidate, not the already published
0.1163-3K archive. The manager controls the existing VPS `client-wg0` return-home
interface. It does not manage the router-facing `wg0` interface, port forwards,
or MQVPN's independent LAN-prefix registration.

After installing the candidate and starting `client-wg0`, run as root:

```sh
omr-wg-manager
```

The menu adds, lists, disables, re-enables and removes clients, changes their
LAN permission, and explicitly displays a profile or terminal QR code. The
same operations are scriptable:

```sh
omr-wg-manager status
omr-wg-manager status --json
omr-wg-manager add phone
omr-wg-manager add laptop --full
omr-wg-manager add tablet --ip 10.255.246.10 --endpoint vps.example.net:65312
omr-wg-manager lan phone allow
omr-wg-manager lan phone deny
omr-wg-manager disable phone
omr-wg-manager enable phone
omr-wg-manager remove phone
omr-wg-manager show phone
omr-wg-manager qr phone
```

The endpoint defaults to the endpoint in `/root/wireguard-client.conf`; supply
`--endpoint` if that file is unavailable or its address has changed. `qr`
requires `qrencode`. `show` and `qr` deliberately display a private key: use a
private terminal and transfer profiles over a trusted channel. Profile files
are under `/etc/wireguard/omr-remote-clients/` (directory 0700, files 0600).
The private state directory `/etc/openmptcprouter-vps-admin/wg-remote-manager/`
is 0700 and its state files are 0600. Back up the state directory, server
configuration and client profiles securely together; losing the registry does
not silently turn existing peers into trusted legacy peers.

Each new client receives a unique WireGuard address and has GUI-only access by
default: TCP 80/443 on the router's synchronized tunnel address. It cannot use
the router's SSH port, other OMR tunnels, private destinations through the VPS
WAN, or the VPS's own management ports. Local DNS port 53 is allowed if the VPS
is deliberately configured as a resolver. Split-tunnel profiles initially
route `10.255.0.0/16`; `--full` routes all IPv4 through the VPS and public
Internet traffic is NATed to its WAN IPv4 address. IPv6 is outside this
manager's scope.

LAN access requires **both** the individual client's `lan NAME allow` and the
existing global OMR GUI checkbox (or `wg-remote-lan-route --lan-access allow`).
Granting a client permission never changes that global switch. With a split
tunnel, export/import the profile again after granting LAN access so it includes
the synchronized router LAN subnet; an existing full-tunnel profile already
includes it. Disabling either gate immediately blocks established LAN traffic.
The GUI and Internet paths remain available, subject to the tunnel being up.

At first migration, the manager records all pre-existing peer public keys as
legacy. Their historic global-checkbox LAN behavior is preserved: they require
the global switch, but no new individual opt-in. Their existing profile and VPS
INPUT policy are not rewritten; in particular, the old VPS OUTPUT policy does
not promise an SSH session to the VPS over this interface. New peers do not
inherit legacy permissions, even when an address is reused. Existing peers must
each have one unique IPv4 `/32` within `10.255.246.0/24`; migration refuses
broader, overlapping, foreign or ambiguous peer routes so that they can be
resolved manually before updating.

Status reports requested permission, whether the firewall currently has an
effective LAN grant, byte counters and the age of the last handshake. A recent
handshake is activity evidence, not proof a client is presently connected or
that the router/LAN is reachable. `open (!)` warns that actual nftables state
does not match persisted policy; `unknown` means firewall state could not be
read. Peer changes use targeted `wg set` operations
and do not restart `client-wg0` or remove unrelated peers.

If a change is interrupted, `omr-wg-manager recover` disables incomplete peers
and keeps their addresses reserved. Review them with `status`, then explicitly
enable or remove them. A mismatch between live peers, `/etc/wireguard/client-wg0.conf`
and the private registry is rejected rather than overwritten; resolve external
manual edits before retrying. `SaveConfig = true` can rewrite the file when
WireGuard is stopped, so configuration management should not edit this
interface concurrently with manager operations.

## Development verification

On an isolated Linux test host with root, `python3`, `pytest`, `ip`, `nft` and
`wg` available, run:

```sh
python3 -m pytest -q tests/test_omr_wg_manager.py
python3 tests/run_omr_wg_netns.py
```

To save the sanitized checks and SHA-256 hashes of the tested source files,
append `--report PATH` to the second command.

The second command creates short-lived network namespaces and ephemeral test
keys, loads the shipped nftables rules and exercises real WireGuard traffic.
It uses a simulated router/OMR tunnel and synthetic public Internet endpoint;
it is not a production VPS, real MQVPN, mobile-device, reboot or installer
test. Output contains only sanitized assertion names.
