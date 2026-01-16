#!/usr/bin/env python3
#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
from __future__ import annotations

import argparse
import re
from pathlib import Path

DOC_PID_RE = re.compile(r"0x[0-9A-Fa-f]{4}")
DOC_PID_RANGE_RE = re.compile(r"0x([0-9A-Fa-f]{3})([0-9A-Fa-f])/(?:([0-9A-Fa-f]))")
YAML_PID_RE = re.compile(r"^\s*product_id(?:_wireless)?\s*:\s*(0x[0-9A-Fa-f]{4})", re.M)


def _expand_doc_ranges(text: str) -> set[str]:
    expanded: set[str] = set()
    for match in DOC_PID_RANGE_RE.finditer(text):
        prefix, first, second = match.groups()
        expanded.add(f"0x{prefix}{first}".lower())
        if second:
            expanded.add(f"0x{prefix}{second}".lower())
    return expanded


def read_doc_pids(doc_path: Path) -> set[str]:
    text = doc_path.read_text(encoding="utf-8")
    pids = {pid.lower() for pid in DOC_PID_RE.findall(text)}
    pids |= _expand_doc_ranges(text)
    pids.discard("0x1532")
    return pids


def read_yaml_pids(data_dir: Path) -> list[str]:
    pids: list[str] = []
    for yaml_path in sorted(data_dir.glob("*.yaml")):
        text = yaml_path.read_text(encoding="utf-8")
        pids.extend(pid.lower() for pid in YAML_PID_RE.findall(text))
    return pids


def format_list(title: str, values: list[str]) -> str:
    if not values:
        return f"{title}: (none)"
    joined = ", ".join(values)
    return f"{title} ({len(values)}): {joined}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit hardware DB coverage against docs.")
    parser.add_argument(
        "--doc",
        type=Path,
        default=Path("docs/razer-device-database.md"),
        help="Path to the device database doc.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("uchroma/server/data"),
        help="Directory containing hardware YAML files.",
    )
    args = parser.parse_args()

    doc_pids = read_doc_pids(args.doc)
    yaml_pids = read_yaml_pids(args.data_dir)

    yaml_pid_set = set(yaml_pids)
    duplicates = sorted({pid for pid in yaml_pids if yaml_pids.count(pid) > 1})
    doc_only = sorted(doc_pids - yaml_pid_set)
    yaml_only = sorted(yaml_pid_set - doc_pids)

    print("UChroma hardware DB audit")
    print(f"Doc PIDs: {len(doc_pids)}")
    print(f"YAML PIDs: {len(yaml_pid_set)}")
    print(format_list("Doc-only", doc_only))
    print(format_list("YAML-only", yaml_only))
    print(format_list("Duplicates in YAML", duplicates))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
