# OMR return-to-home manager (0.1164-3K)

The VPS 0.1164-3K archive refreshed on **2026-11-09** includes `omr-rth`
and this guided menu. Earlier downloads used `omr-wg-manager`; the old command
remains a compatibility alias. The refreshed archive includes admin API
**0.18+20261030-3k10**, while the frozen kernel and VPN binaries are unchanged.

This manager targets VPS 0.1164-3K, paired with client 0.64.3-3K.
It controls the existing VPS `client-wg0` return-home
interface. It does not manage the router-facing `wg0` interface, port forwards,
or MQVPN's independent LAN-prefix registration.

After installation and starting `client-wg0`, run as root:

```sh
omr-rth
```

The command is installed in `/usr/local/sbin` by the VPS installer. The previous
`omr-wg-manager` command remains an alias for existing scripts, and the Python
module keeps its original name for the LAN-policy helper.

## Access the router after connecting

Import a client profile or QR code and activate WireGuard on the remote device.
The WireGuard endpoint is the VPS public address, normally UDP **65312**; the
router GUI is reached through its **current OMR tunnel address**, not by opening
the VPS public address in a browser. With the standard MQVPN primary router,
open **https://10.255.220.2/** or **http://10.255.220.2/**. A different active
transport or an explicitly configured router address can use a different IP.
The router still requires its normal LuCI username and password.

| Destination or action | Expected behavior |
| --- | --- |
| Router tunnel IP, TCP 80/443 | GUI rescue access works with LAN access disabled. |
| Router LAN IP, for example `10.1.1.1` | Treated as LAN access; requires all LAN permissions below. |
| Other devices on the router LAN | Blocked by default; requires all LAN permissions below. |
| Ping or SSH to the router tunnel IP | Not part of the default GUI-only permission; a failed ping does not prove the GUI is unreachable. |
| IPv4 Internet with client `AllowedIPs = 0.0.0.0/0` | Uses the VPS public egress IP; does not bypass LAN permissions. |
| No tunnel client preset | Suspends tunnel-based GUI/LAN access until an OMR VPN transport is active again. |

For LAN access, all of these must be true:

1. Enable **System -> OpenMPTCProuter -> Settings -> Server settings -> Allow
   remote WireGuard access to LAN** on the router. This is the global VPS gate.
2. Grant the individual client access in `omr-rth`, or run
   `omr-rth lan CLIENT_NAME allow` on the VPS. Imported legacy clients retain
   their migration permissions; newly created clients start with LAN denied.
3. Include the current LAN subnet in the client profile's `AllowedIPs`, or use
   `0.0.0.0/0`. Re-export/re-import a split profile after enabling LAN access so
   it includes the synchronized LAN prefix, then reactivate WireGuard.

The OMR VPN and synchronized LAN route must also be available. Disabling the
global gate or revoking the individual grant blocks LAN traffic, including
existing exchanges, while preserving HTTP/HTTPS rescue on the router tunnel IP.
Use `omr-rth status` to distinguish requested LAN permission from an actually
open firewall gate. A recent handshake alone proves neither GUI nor LAN access.

### Client v0.64.3-3K compatibility

The published v0.64.3-3K client supports this RTH manager and the unchanged
`wireguard/remote-access` API used by its global LAN checkbox. Renaming the
VPS command requires no client firmware rebuild. An older tooltip can still
refer to `omr-wg-manager`; that command remains an alias.

The client-side fix for changing LAN addresses stored in CIDR form with a
retained netmask was committed after the published v0.64.3 images and is
scheduled for v0.64.4-3K. API **3k9** provides backward compatibility now: it
normalizes the old `IPv4/prefix/retained-mask` payload after validating both
suffixes. The explicit CIDR prefix wins over the stale retained mask. This
specific scenario therefore needs no v0.64.3 rebuild when paired with 3k9.
Malformed JSON or other client-side collector issues are outside this narrow
compatibility parser. The VPS also retires obsolete LAN routes. See
[LAN subnet synchronization](LAN-SUBNET-SYNC.md).

On 2026-11-09 a temporary real WireGuard peer on an existing VPS completed a
handshake and reached LuCI over HTTP and HTTPS on the MQVPN router tunnel IP
with the global LAN gate disabled. The peer was removed and existing live peer
identities were verified unchanged. The operator also confirmed remote access
from the client afterwards. This check did not exercise the disabled LAN gate
as an allowed LAN path or assert a new clean installation.

## Manage clients

The interactive menu is:

1. Add a new user
2. List all users
3. Remove an existing user
4. Display connected clients
5. Show a client configuration
6. Show a client QR code
7. Disable a client
8. Enable a client
9. Allow LAN access for a client
10. Deny LAN access for a client
11. Recover an interrupted peer operation
12. Exit

Client operations present numbered choices. The original installation client
appears first with `(installation default)`, followed by the other existing
clients in their registry order. Its script name remains `legacy_2` on the
standard installation. Identity comes from the installer's public-key file or
a verified matching installation profile; an address alone never identifies
the default. Missing or mismatched identity evidence does not create a client,
replace a key or export another client's profile. Other imported clients may
have no private profile available; their public peer identity is still listed.

The add wizard asks for a name (up to 15 characters), suggests the next free
IPv4 address, and asks whether to route all IPv4 Internet through the VPS. It
reuses the endpoint from the existing installation profile when available.
After creation it displays the QR code when `qrencode` is installed, then the
profile path. Use a private terminal: this QR code includes the client's key.
The scriptable interface retains support for names up to 32 characters.

The same operations are scriptable:

```sh
omr-rth list
omr-rth connected
omr-rth status
omr-rth status --json
omr-rth add phone
omr-rth add laptop --full
omr-rth add tablet --ip 10.255.246.10 --endpoint vps.example.net:65312
omr-rth lan phone allow
omr-rth lan phone deny
omr-rth disable phone
omr-rth enable phone
omr-rth remove phone
omr-rth show phone
omr-rth qr phone
```

The endpoint defaults to the single `[Peer]` endpoint in
`/root/wireguard-client.conf`; comments are accepted, while duplicate endpoint
fields or multiple peer sections require an explicit `--endpoint` override.
Supply `--endpoint` if that file is unavailable or its address has changed.
An existing bracketed IPv6 outer endpoint remains supported; this does not
enable IPv6 addresses or routes inside the RTH tunnel.

New profiles reuse valid IPv4 DNS resolvers from the installation profile's
`[Interface]` section. Repeated DNS directives are merged and deduplicated;
comments, IPv6 resolvers, search domains and malformed values are omitted.
If no IPv4 resolver is present, DNS defaults to `1.1.1.1`. The source profile
and existing client keys are preserved. Like the reference add-user wizard,
the RTH wizard reuses these installation settings without asking DNS questions.

Fresh RTH installation profiles and newly generated client profiles default to
`MTU = 1320` and `PersistentKeepalive = 25`. New profiles inherit an explicit
`[Interface]` MTU or `[Peer]` keepalive from the original installation profile,
including `0` or `off` to keep keepalive disabled. Duplicate or malformed explicit
values require correction rather than being silently replaced. Existing client
profiles and their keys are preserved.

The fresh `client-wg0` server configuration also defaults to MTU 1320. During
installation, `init --defer-firewall --default-server-mtu` adds that value only
when the server configuration has no explicit MTU. This installer-only flag
changes the saved configuration, without changing a running interface or
restarting it. Ordinary menu startup does not insert server defaults. The
router-facing `wg0` configuration is unaffected; normal WireGuard `SaveConfig`
behavior still applies when an already-running interface later stops.

`qr` requires `qrencode`. `show` and `qr` deliberately display a private key: use a
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

The connected-client display follows the reference table: Client IP, Last
Handshake (UTC), Status, Endpoint and Data Transferred (RX+TX in whole MiB,
labelled MB to match the reference). `Connected` means a handshake less than
four minutes old; `Disconnected` means an older handshake, and `Never Connected`
means no handshake was reported. Disabled clients remain listed and can be
re-enabled without new keys. Public fields are parsed from targeted
`wg show client-wg0` queries, avoiding the reference's all-interface key dump.

Detailed status reports requested permission, whether the firewall currently has an
effective LAN grant, byte counters and the age of the last handshake. A recent
handshake is activity evidence, not proof a client is presently connected or
that the router/LAN is reachable. `open (!)` warns that actual nftables state
does not match persisted policy; `unknown` means firewall state could not be
read. Peer changes use targeted `wg set` operations
and do not restart `client-wg0` or remove unrelated peers.

If a change is interrupted, `omr-rth recover` disables incomplete peers
and keeps their addresses reserved. Review them with `status`, then explicitly
enable or remove them. A mismatch between live peers, `/etc/wireguard/client-wg0.conf`
and the private registry is rejected rather than overwritten; resolve external
manual edits before retrying. `SaveConfig = true` can rewrite the file when
WireGuard is stopped, so configuration management should not edit this
interface concurrently with manager operations.

## Reference and supported scope

The add wizard, numbered client selection and connected-client table adapt
[Brazzo978/wg-easy-ipv6-portfw](https://github.com/Brazzo978/wg-easy-ipv6-portfw/blob/9bc51e768e1b49d71c6093335b081cc895cee876/wg-setup.sh),
commit `9bc51e768e1b49d71c6093335b081cc895cee876` (GPL-3.0, the same license as
this repository). Reference menu entries 1/2/3/7 become entries 1/2/3/4 here.
The standalone VPN installer/uninstaller, public IPv6 controls, script updater,
PATH toggle, public port forwarding and bandwidth limiters are intentionally
omitted from this RTH menu. OMR provides the underlying WireGuard installation,
firewall, forwarding and shaping policies. This manager keeps its existing
IPv4 pool and operates only on `client-wg0`.

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
