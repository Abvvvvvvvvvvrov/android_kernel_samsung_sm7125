#!/usr/bin/env python3
"""Verify an AnyKernel3 flashable zip for Galaxy A52 4G (a52q).

Usage:
    python3 verify-ak3.py <AnyKernel3-*.zip>

Checks (fail loudly, exit 1):
  * zip contains Image.gz (preferred) or Image, and NOT Image.gz-dtb /
    Image-dtb / dtb / dtbo.img (a52q boot.img hdr v2 keeps stock dtb section
    + stock dtbo overlays per board revision; appended-dtb images and foreign
    dtbo files are a classic boot-hang source).
  * Image.gz has valid gzip magic, decompresses fully, sane size.
  * Decompressed Image embeds a "Linux version 4.14..." string; warn on -dirty.
  * anykernel.sh targets boot partition, non-slot device, a52q device names.

Stdlib only, runs on CI (ubuntu) and locally (Windows).
"""
import gzip
import re
import sys
import zipfile

REQUIRED_DEVICES = ("a52q", "SM-A525")
FORBIDDEN = ("Image.gz-dtb", "Image-dtb", "dtb", "dtbo.img")
MIN_IMG = 5 * 1024 * 1024        # compressed Image.gz below this = truncated
MAX_IMG = 40 * 1024 * 1024       # above this = something wrong (e.g. debug blob)


def fail(msg):
    print(f"VERIFY FAIL: {msg}")
    return False


def main(path):
    ok = True
    try:
        zf = zipfile.ZipFile(path)
    except (FileNotFoundError, zipfile.BadZipFile) as e:
        print(f"VERIFY FAIL: cannot open zip: {e}")
        return 1
    names = set(zf.namelist())
    print(f"zip: {path} ({len(names)} entries)")

    for bad in FORBIDDEN:
        if bad in names:
            ok = fail(f"zip ships forbidden '{bad}' (stock dtb/dtbo must stay)") and ok

    img_name = "Image.gz" if "Image.gz" in names else ("Image" if "Image" in names else None)
    if img_name is None:
        ok = fail("no kernel image (Image.gz or Image) in zip") and ok
        print("VERIFY: FAILED")
        return 1
    print(f"kernel image: {img_name}")

    raw = zf.read(img_name)
    print(f"compressed size: {len(raw)} bytes")
    if img_name.endswith(".gz"):
        if raw[:2] != b"\x1f\x8b":
            ok = fail("Image.gz has bad gzip magic") and ok
        else:
            try:
                img = gzip.decompress(raw)
            except (OSError, EOFError) as e:
                img = b""
                ok = fail(f"Image.gz does not decompress fully: {e}") and ok
            print(f"decompressed size: {len(img)} bytes")
            if not MIN_IMG <= len(raw) <= MAX_IMG:
                ok = fail(f"compressed size {len(raw)} outside sane range "
                           f"[{MIN_IMG}, {MAX_IMG}]") and ok
            m = re.search(rb"Linux version (\S+)", img)
            if m:
                ver = m.group(1).decode("ascii", "replace")
                print(f"embedded version: Linux version {ver}")
                if not ver.startswith("4.14."):
                    ok = fail(f"unexpected kernel version: {ver}") and ok
                if "dirty" in ver:
                    print("VERIFY WARN: version string contains -dirty "
                          "(tree was modified during build)")
            else:
                ok = fail("no 'Linux version' string inside Image") and ok
    else:
        if len(raw) < MIN_IMG:
            ok = fail(f"Image too small ({len(raw)} bytes), truncated?") and ok

    try:
        ak = zf.read("anykernel.sh").decode("utf-8", "replace")
    except KeyError:
        ok = fail("anykernel.sh missing from zip") and ok
        ak = ""
    for needle, why in (("BLOCK=boot;", "must flash boot partition (a52q is A-only)"),
                        ("IS_SLOT_DEVICE=0;", "a52q has no slots"),
                        ("do.devicecheck=1;", "device check must stay on")):
        if needle in ak:
            print(f"anykernel.sh: {needle} OK")
        else:
            ok = fail(f"anykernel.sh missing '{needle}' ({why})") and ok
    for dev in REQUIRED_DEVICES:
        if dev not in ak:
            ok = fail(f"anykernel.sh missing device id '{dev}'") and ok

    print("VERIFY: PASSED" if ok else "VERIFY: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
