"""Pure nft port-rule rendering shared by the API and profile watchdog."""


def comment(text):
    return text.replace('"', "'")[:128]


def render_fw_ports(config_data):
    accept_rules, dnat_rules = [], []
    users = config_data.get('users', [{}])[0]
    for username, udata in users.items():
        for entry in udata.get('fw_ports', []):
            name = entry.get('name', '')
            port = entry.get('port', '')
            proto = entry.get('proto', 'tcp')
            fwtype = entry.get('fwtype', 'ACCEPT')
            family = entry.get('family', 4)
            source_dip = entry.get('source_dip', '')
            dest_ip = entry.get('dest_ip', '')
            vpn = entry.get('vpn', 'default')
            suffix = entry.get('comment', '')
            match = f'meta nfproto {"ipv4" if family == 4 else "ipv6"}'
            if source_dip:
                match += f' {"ip" if family == 4 else "ip6"} daddr {source_dip}'
            if dest_ip:
                match += f' {"ip" if family == 4 else "ip6"} saddr {dest_ip}'
            tag = comment(f'OMR {username} {"open" if fwtype == "ACCEPT" else "redirect"} {name} {proto}{suffix}')
            if fwtype == 'ACCEPT':
                accept_rules.append(f'{match} {proto} dport {port} accept comment "{tag}"')
            elif fwtype == 'DNAT':
                if vpn != 'default':
                    target = vpn
                elif family == 4:
                    target = udata.get('vpnremoteip', '')
                else:
                    target = 'fd00::a0{:x}:2'.format(udata.get('userid', 0) or 0)
                if not target:
                    continue
                dnat_rules.append(f'{match} {proto} dport {port} dnat {"ip" if family == 4 else "ip6"} to {target} comment "{tag}"')
    return accept_rules, dnat_rules


def render_bulk_redirect(config_data):
    lines = []
    default_user = config_data.get('users', [{}])[0].get('openmptcprouter', {})
    if config_data.get('bulk_redirect_v4'):
        target = default_user.get('vpnremoteip', '')
        if target:
            for proto in ('tcp', 'udp'):
                lines.append(f'meta nfproto ipv4 {proto} dport 1-64999 dnat ip to {target} comment "OMR bulk redirect {proto}"')
    if config_data.get('bulk_redirect_v6'):
        target6 = 'fd00::a0{:x}:2'.format(default_user.get('userid', 0) or 0)
        for proto in ('tcp', 'udp'):
            lines.append(f'meta nfproto ipv6 {proto} dport 1-64999 dnat ip6 to {target6} comment "OMR bulk redirect {proto}6"')
    return lines
