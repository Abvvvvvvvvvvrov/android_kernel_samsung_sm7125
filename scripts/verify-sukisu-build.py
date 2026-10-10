#!/usr/bin/env python3
"""Fail CI if root toggles were lost or the build changed unrelated settings."""

import argparse
from pathlib import Path
import re
import sys


def read_config(path):
    config = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(CONFIG_[A-Za-z0-9_]+)=(.*)", line)
        if match:
            config[match[1]] = match[2]
            continue
        match = re.fullmatch(r"# (CONFIG_[A-Za-z0-9_]+) is not set", line)
        if match:
            config[match[1]] = "n"
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--root", choices=("true", "false"), required=True)
    parser.add_argument("--stock-config", help="config extracted from the matching stock ROM")
    parser.add_argument("--release", help="actual make kernelrelease output")
    parser.add_argument("--expected-release", help="exact stock ROM kernel release")
    parser.add_argument("--symbols", help="complete nm --defined-only output")
    args = parser.parse_args()
    config = read_config(args.config)
    baseline = read_config(args.baseline)
    errors = []
    root = args.root == "true"
    expected = "y" if root else "n"
    if config.get("CONFIG_KSU", "n") != expected:
        errors.append(f"CONFIG_KSU must be {expected}; got {config.get('CONFIG_KSU', 'missing')}")
    for key in ("CONFIG_KSU_SUSFS", "CONFIG_KPM"):
        if config.get(key, "n") != "n":
            errors.append(f"{key} must be disabled")
    # Preserve the user's repository policy: do not enable forced module
    # signature enforcement, even though the stock ROM enables it.
    if config.get("CONFIG_MODULE_SIG_FORCE", "n") != "n":
        errors.append("CONFIG_MODULE_SIG_FORCE must remain disabled by user request")
    for key in ("CONFIG_KSU_MANUAL_HOOK", "CONFIG_KSU_KPROBES_HOOK", "CONFIG_KSU_SYSCALL_TABLE_HOOK"):
        if key in config:
            errors.append(f"obsolete KernelSU-Next symbol remains: {key}")
    for key in set(baseline) | set(config):
        if key.startswith("CONFIG_KSU") or key == "CONFIG_KPM":
            continue
        if baseline.get(key, "n") != config.get(key, "n"):
            errors.append(f"unrelated config changed: {key}: {baseline.get(key, 'n')} -> {config.get(key, 'n')}")
    if args.stock_config:
        stock = read_config(args.stock_config)
        # LOCALVERSION embeds the stock Git suffix explicitly while AUTO is off.
        # The extra trusted public certificate accepts existing signed ROM modules.
        allowed = {"CONFIG_KPM", "CONFIG_LOCALVERSION", "CONFIG_LOCALVERSION_AUTO",
                   "CONFIG_SYSTEM_TRUSTED_KEYS", "CONFIG_MODULE_SIG_FORCE"}
        for key in sorted(set(stock) | set(config)):
            if key.startswith("CONFIG_KSU") or key in allowed:
                continue
            if stock.get(key, "n") != config.get(key, "n"):
                errors.append(f"stock ROM config mismatch: {key}: {stock.get(key, 'n')} -> {config.get(key, 'n')}")
    if bool(args.release) != bool(args.expected_release):
        errors.append("--release and --expected-release must be supplied together")
    elif args.release:
        release = Path(args.release).read_text(encoding="utf-8").strip()
        if release != args.expected_release:
            errors.append(f"kernel release mismatch: {release!r}; expected {args.expected_release!r}")
    if args.symbols:
        symbols = set()
        for line in Path(args.symbols).read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) >= 3:
                symbols.add(fields[-1])
        if root:
            required = ("kernelsu_init", "ksu_handle_execveat", "ksu_handle_faccessat",
                        "ksu_handle_stat", "ksu_handle_sys_read", "ksu_handle_vfs_fstat",
                        "ksu_handle_sys_reboot", "ksu_handle_su_execveat_success")
            for name in required:
                if name not in symbols:
                    errors.append(f"built-in SukiSU symbol missing: {name}")
        else:
            root_symbols = sorted(name for name in symbols
                                  if name.startswith("ksu_") or name == "kernelsu_init")
            if root_symbols:
                errors.append(f"root-free build still has root symbols: {', '.join(root_symbols[:12])}")
        susfs_symbols = sorted(name for name in symbols if name.startswith("susfs_"))
        if susfs_symbols:
            errors.append(f"SUSFS disabled but compiled symbols remain: {', '.join(susfs_symbols[:8])}")
    if errors:
        for error in errors:
            print(f"VERIFY FAIL: {error}", file=sys.stderr)
        return 1
    print(f"VERIFY PASSED: SukiSU={expected}, SUSFS=n, KPM=n; unrelated config unchanged")
    if args.symbols:
        print("VERIFY PASSED: vmlinux root symbols match requested mode")
    if args.stock_config:
        print("VERIFY PASSED: stock ROM config preserved except root, release suffix, trusted certificate and requested MODULE_SIG_FORCE=n")
    if args.release:
        print(f"VERIFY PASSED: exact ROM kernel release {args.expected_release}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
