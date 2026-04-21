Changelog 0.62.4-3K VS vanilla 0.62 version.

## UI / Wizard / Settings

- Removed the IPv6 section from the wizard.
- IPv6 is now forcibly disabled on the controller side (`disable_ipv6=1`, `disable_6in4=1`).
- Removed IPv6 fields per interface (`ip6addr`, `ip6gw`, `reqprefix`, `reqaddress`, etc.).
- Removed the “Country settings” section from the wizard.
- Simplified the WAN wizard: removed modem-related paths (`qmi`, `ncm`, `mbim`, `modemmanager`, `dhcpv6`, `other`), now focused on `static` / `dhcp` / `pppoe`.
- In the backend, unsupported protocols are now normalized to `dhcp`.
- `modemmanager` is now forcibly disabled when saving settings.
- Reintroduced the “Master interface selection” block in Settings, with a description of its behavior (`balancing`, `change`, `dynamic`, `static`), please dont use it unless you know what to do !
- Improved default/fallback master handling: preserves the existing value when possible, otherwise falls back to `balancing`.
- Removed `xray-vless-reality` as a client-side proxy option; it is now automatically normalized to `xray` (VLESS) , probably will remove more stuff in future versione since they are useless.

## MPTCP (LuCI + defaults + runtime)

- Improved labels and descriptions on the MPTCP page for better clarity around scheduler / congestion control / path manager.
- Added the `mptcp_allow_join_initial_addr_port` option.
- Changed the default value of `mptcp_subflows` to `8`.
- Changed the default value of `mptcp_add_addr_accepted` to `8`.
- Fixed a runtime typo in MPTCP init for `allow_join_initial_addr_port`.
- Normalized BPF scheduler names in the JS UI by removing the `.o` file prefix/suffix.

# Port forwarding via proxy / XRay (really good stuff here)

- Added a new advanced firewall flag: `force_xray_pf` (“Force XRay for this port forward”).
- If a rule uses proxy-forward and `force_xray_pf=1`, the port forwarding logic will use the XRay backend forcing it up , even when the main proxy is not XRay or V2ray based.
- Improved VPS/client sync integration for port forwarding with forced XRay.
- Version `0.62.3` also includes PF-only logic to prevent transparent UDP from being left improperly enabled when only port forwarding is required.

## Tracker / failover policy

- Changed the default `omr-tracker` family to `ipv4` (proxy/default).
- Changed the default `failure_interval` to `20`.
- `omr-tracker` now uses the dynamic XRay tracker port (`xray.omrtest.port`) instead of the hardcoded `1111`, avoiding conflicts with ShadowSocks.

## VPN / SQM defaults

- Changed the default initial VPN to `glorytun_tcp` (openvpn is more developed , more stable and stuff but its more complicated and performs worse on tcp than glorytun).
- SQM on WAN interfaces (`wan1` ..) is now disabled by default (opt-in).
- V2Ray/XRay transparent UDP redirect is now enabled by default (`1`), this will break some udp tunnel and stuff since it uses udp to tcp to send udp traffic , still performs better in a lot of situation than using the tunnel to do so, disable if necessary.

## Omr-speedtest / tuning wizard

- `omr-test-speed` now reads hosts from external files:
  - `/etc/omr-test-speed-hosts.list`
  - `/etc/omr-test-speed-hosts6.list`
  - Added custom hosts for EU(`repoomr (italy)` + `Hetzner` + `Clouvider`).
  - Updated SQM/QoS formulas:
  - autorate minimum changed from `10%` to `25%`
  - non-autorate shaping changed from `95%` to `90%`
  - Fixed autorate parameter configuration.

## Build / packaging

- `ipcalc` now uses a local/versioned tarball source instead of fetching directly from git during build.
- Rust toolchain: `llvm.download-ci-llvm=false` to avoid dependency on external CI artifacts.
- `shadowsocks-rust` is now built with `cargo --locked` for deterministic lockfile-compatible builds.
Changelog VS vanilla 0.62 version.

## UI / Wizard / Settings

- Removed the IPv6 section from the wizard.
- IPv6 is now forcibly disabled on the controller side (`disable_ipv6=1`, `disable_6in4=1`).
- Removed IPv6 fields per interface (`ip6addr`, `ip6gw`, `reqprefix`, `reqaddress`, etc.).
- Removed the “Country settings” section from the wizard.
- Simplified the WAN wizard: removed modem-related paths (`qmi`, `ncm`, `mbim`, `modemmanager`, `dhcpv6`, `other`), now focused on `static` / `dhcp` / `pppoe`.
- In the backend, unsupported protocols are now normalized to `dhcp`.
- `modemmanager` is now forcibly disabled when saving settings.
- Reintroduced the “Master interface selection” block in Settings, with a description of its behavior (`balancing`, `change`, `dynamic`, `static`), please dont use it unless you know what to do !
- Improved default/fallback master handling: preserves the existing value when possible, otherwise falls back to `balancing`.
- Removed `xray-vless-reality` as a client-side proxy option; it is now automatically normalized to `xray` (VLESS) , probably will remove more stuff in future versione since they are useless.

## MPTCP (LuCI + defaults + runtime)

- Improved labels and descriptions on the MPTCP page for better clarity around scheduler / congestion control / path manager.
- Added the `mptcp_allow_join_initial_addr_port` option.
- Changed the default value of `mptcp_subflows` to `8`.
- Changed the default value of `mptcp_add_addr_accepted` to `8`.
- Fixed a runtime typo in MPTCP init for `allow_join_initial_addr_port`.
- Normalized BPF scheduler names in the JS UI by removing the `.o` file prefix/suffix.

# Port forwarding via proxy / XRay (really good stuff here)

- Added a new advanced firewall flag: `force_xray_pf` (“Force XRay for this port forward”).
- If a rule uses proxy-forward and `force_xray_pf=1`, the port forwarding logic will use the XRay backend forcing it up , even when the main proxy is not XRay or V2ray based.
- Improved VPS/client sync integration for port forwarding with forced XRay.
- Version `0.62.3` also includes PF-only logic to prevent transparent UDP from being left improperly enabled when only port forwarding is required.

## Tracker / failover policy

- Changed the default `omr-tracker` family to `ipv4` (proxy/default).
- Changed the default `failure_interval` to `20`.
- `omr-tracker` now uses the dynamic XRay tracker port (`xray.omrtest.port`) instead of the hardcoded `1111`, avoiding conflicts with ShadowSocks.

## VPN / SQM defaults

- Changed the default initial VPN to `glorytun_tcp` (openvpn is more developed , more stable and stuff but its more complicated and performs worse on tcp than glorytun).
- SQM on WAN interfaces (`wan1` ..) is now disabled by default (opt-in).
- V2Ray/XRay transparent UDP redirect is now enabled by default (`1`), this will break some udp tunnel and stuff since it uses udp to tcp to send udp traffic , still performs better in a lot of situation than using the tunnel to do so, disable if necessary.

## Omr-speedtest / tuning wizard

- `omr-test-speed` now reads hosts from external files:
  - `/etc/omr-test-speed-hosts.list`
  - `/etc/omr-test-speed-hosts6.list`
  - Added custom hosts for EU(`repoomr (italy)` + `Hetzner` + `Clouvider`).
  - Updated SQM/QoS formulas:
  - autorate minimum changed from `10%` to `25%`
  - non-autorate shaping changed from `95%` to `90%`
  - Fixed autorate parameter configuration.

## Build / packaging

- `ipcalc` now uses a local/versioned tarball source instead of fetching directly from git during build.
- Rust toolchain: `llvm.download-ci-llvm=false` to avoid dependency on external CI artifacts.
- `shadowsocks-rust` is now built with `cargo --locked` for deterministic lockfile-compatible builds.
