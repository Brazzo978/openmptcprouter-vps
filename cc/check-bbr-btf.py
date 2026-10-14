#!/usr/bin/env python3
"""Reject a kernel whose stock BBRv3 kfunc BTF IDs cannot resolve."""
import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path

KFUNCS = (
    "bbr_init", "bbr_main", "bbr_sndbuf_expand", "bbr_skb_marked_lost",
    "bbr_undo_cwnd", "bbr_cwnd_event", "bbr_ssthresh", "bbr_tso_segs",
    "bbr_set_state",
)
CUSTOM = ("bbr1", "bbr2", "nanqinlang") + tuple(
    f"nanbbr{family}_{profile}"
    for family in (1, 2, 3)
    for profile in ("light", "def", "aggr", "var")
)


def output(*command):
    return subprocess.check_output(command, text=True)


def verify(vmlinux: Path):
    section_lines = re.findall(
        r"^\s*\[\s*\d+\]\s+\.BTF_ids\s+\S+\s+"
        r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)",
        output("readelf", "-SW", str(vmlinux)), re.MULTILINE)
    if len(section_lines) != 1:
        raise ValueError("missing or ambiguous vmlinux .BTF_ids section")
    section_addr, section_off, section_size = (
        int(n, 16) for n in section_lines[0])
    symbols = re.findall(
        r"^([0-9a-fA-F]+)\s+\w\s+tcp_bbr_check_kfunc_ids$",
        output("nm", "-an", str(vmlinux)), re.MULTILINE)
    if len(symbols) != 1:
        raise ValueError("missing or ambiguous stock BBR kfunc ID set")
    offset = int(symbols[0], 16) - section_addr
    if offset < 0 or offset + 8 + 8 * len(KFUNCS) > section_size:
        raise ValueError("stock BBR kfunc ID set outside .BTF_ids")
    with vmlinux.open("rb") as stream:
        stream.seek(section_off + offset)
        values = struct.unpack("<" + "I" * (2 + 2 * len(KFUNCS)),
                               stream.read(8 + 8 * len(KFUNCS)))
    count, flags = values[:2]
    if count != len(KFUNCS) or flags != 1:
        raise ValueError(f"unexpected BBR kfunc set layout: {count=} {flags=}")
    ids = values[2::2]
    if any(identifier == 0 for identifier in ids):
        raise ValueError(f"unresolved stock BBR kfunc BTF IDs: {ids}")
    btf = output("bpftool", "btf", "dump", "file", str(vmlinux),
                 "format", "raw")
    missing = [name for name in KFUNCS
               if not re.search(r"\bFUNC '" + re.escape(name) + r"'", btf)]
    if missing:
        raise ValueError("stock BBR functions missing from BTF: " +
                         ", ".join(missing))
    module_dir = vmlinux.parent / "net" / "ipv4"
    for name in CUSTOM:
        module = module_dir / f"tcp_{name}.ko"
        if not module.is_file():
            raise ValueError(f"missing custom congestion module: {module}")
        sections = output("readelf", "-SW", str(module))
        if not re.search(r"\]\s+\.BTF\s+", sections):
            raise ValueError(f"missing module BTF: {module}")
    bbr1 = module_dir / "tcp_bbr1.ko"
    bbr1_section = re.findall(
        r"^\s*\[\s*\d+\]\s+\.BTF_ids\s+\S+\s+"
        r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)",
        output("readelf", "-SW", str(bbr1)), re.MULTILINE)
    if len(bbr1_section) != 1:
        raise ValueError("missing or ambiguous BBR1 module .BTF_ids section")
    bbr1_addr, bbr1_off, bbr1_size = (
        int(value, 16) for value in bbr1_section[0])
    bbr1_symbols = re.findall(
        r"^([0-9a-fA-F]+)\s+\w\s+tcp_bbr1_check_kfunc_ids$",
        output("nm", "-an", str(bbr1)), re.MULTILINE)
    if len(bbr1_symbols) != 1:
        raise ValueError("missing or ambiguous BBR1 kfunc ID set")
    bbr1_offset = int(bbr1_symbols[0], 16) - bbr1_addr
    bbr1_count = 8
    if bbr1_offset < 0 or bbr1_offset + 8 + 8 * bbr1_count > bbr1_size:
        raise ValueError("BBR1 kfunc ID set outside module .BTF_ids")
    with bbr1.open("rb") as stream:
        stream.seek(bbr1_off + bbr1_offset)
        bbr1_values = struct.unpack("<" + "I" * (2 + 2 * bbr1_count),
                                    stream.read(8 + 8 * bbr1_count))
    if bbr1_values[:2] != (bbr1_count, 1):
        raise ValueError("unexpected BBR1 kfunc set layout")
    bbr1_ids = bbr1_values[2::2]
    if any(identifier == 0 for identifier in bbr1_ids):
        raise ValueError(f"unresolved BBR1 kfunc BTF IDs: {bbr1_ids}")
    bbr1_btf = output("bpftool", "-B", str(vmlinux), "btf", "dump",
                      "file", str(bbr1), "format", "raw")
    bbr1_names = (
        "bbr1_bbr_init", "bbr1_bbr_main", "bbr1_bbr_sndbuf_expand",
        "bbr1_bbr_undo_cwnd", "bbr1_bbr_cwnd_event",
        "bbr1_bbr_ssthresh", "bbr1_bbr_tso_segs", "bbr1_bbr_set_state",
    )
    absent = [name for name in bbr1_names
              if not re.search(r"\bFUNC '" + re.escape(name) + r"'", bbr1_btf)]
    if absent:
        raise ValueError("BBR1 kfuncs absent from BTF: " + ", ".join(absent))
    print(f"Verified {count} stock BBR and {bbr1_count} BBR1 kfunc BTF IDs, "
          f"plus {len(CUSTOM)} custom module BTF sections")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("vmlinux", type=Path)
    args = parser.parse_args()
    try:
        verify(args.vmlinux)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Invalid BBR BTF: {error}", file=sys.stderr)
        sys.exit(1)
