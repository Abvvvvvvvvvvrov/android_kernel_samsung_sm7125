#!/usr/bin/env bash
# Standalone build using the vendored root implementation in this repository.
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
ROOT_ENABLED=${ROOT_ENABLED:-true}
case "$ROOT_ENABLED" in
    true|false) ;;
    *) printf 'ROOT_ENABLED must be true or false\n' >&2; exit 2 ;;
esac
export PATH="$repo_dir/toolchain/clang/bin:$PATH"
export ARCH=arm64
export SUBARCH=arm64
mkdir -p out diagnostics

test -f drivers/kernelsu/ksu.c
test -f drivers/kernelsu/Kconfig
test -x toolchain/clang/bin/clang
test -s scripts/a52q-lineage-20260817.config
test -s scripts/a52q-lineage-20260817.json
test -s certs/a52q-lineage-20260817.pem
cp scripts/a52q-lineage-20260817.json diagnostics/stock-reference.json
sha256sum scripts/a52q-lineage-20260817.config scripts/a52q-lineage-20260817.json \
    certs/a52q-lineage-20260817.pem > diagnostics/reference-sha256.txt
openssl x509 -in certs/a52q-lineage-20260817.pem -noout -subject -serial \
    -fingerprint -sha256 > diagnostics/trusted-stock-certificate.txt
# Match the actual installed ROM's clang/LLD 21 toolchain and LLVM tools.
# An explicit empty LOCALVERSION prevents a Git suffix for the patched tree;
# the source defconfig already carries the exact ROM release suffix.
make_args=(O=out ARCH=arm64 CC=clang PYTHON=python3 LLVM=1 LLVM_IAS=1 LOCALVERSION=
    CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu-
    CROSS_COMPILE_ARM32=arm-linux-gnueabi-
    LD=ld.lld AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump
    READELF=llvm-readelf STRIP=llvm-strip HOSTCC=clang HOSTCXX=clang++)

# Do not edit the source defconfig or apply patches/sed during compilation.
make "${make_args[@]}" vendor/lineage-a52q_defconfig 2>&1 | tee diagnostics/configure.log
cp out/.config diagnostics/base.config
make -s "${make_args[@]}" kernelrelease > diagnostics/base-kernelrelease.txt
if [ "$ROOT_ENABLED" = true ]; then
    bash scripts/config --file out/.config --enable KSU
else
    bash scripts/config --file out/.config --disable KSU
fi
# SUSFS kernel patches are not part of this migration. KPM remains disabled.
bash scripts/config --file out/.config --disable KSU_SUSFS --disable KPM
make "${make_args[@]}" olddefconfig 2>&1 | tee -a diagnostics/configure.log
cp out/.config diagnostics/final.config
make -s "${make_args[@]}" kernelrelease > diagnostics/kernelrelease.txt
cmp diagnostics/base-kernelrelease.txt diagnostics/kernelrelease.txt
python3 scripts/verify-sukisu-build.py --config out/.config \
    --baseline diagnostics/base.config --root "$ROOT_ENABLED" \
    --stock-config scripts/a52q-lineage-20260817.config \
    --release diagnostics/kernelrelease.txt \
    --expected-release 4.14.356-openela-rc1-perf-g98de87f1b888 \
    2>&1 | tee diagnostics/config-validation.log

{
    printf 'source_commit=%s\n' "$(git rev-parse HEAD)"
    printf 'root_enabled=%s\n' "$ROOT_ENABLED"
    printf 'susfs_enabled=false\nkpm_enabled=false\n'
    printf 'clang_commit=%s\n' "${CLANG_COMMIT:-531a564ba5426707dee226eccb19f104a7af5a5f}"
    printf 'kernelrelease='
    cat diagnostics/kernelrelease.txt
    git status --short
} > diagnostics/build.txt

make -j"$(nproc --all)" "${make_args[@]}" Image.gz dtbs 2>&1 | tee diagnostics/build.log
test -s out/arch/arm64/boot/Image.gz
gzip -t out/arch/arm64/boot/Image.gz
# Write the entire symbol table before parsing. A grep -q pipe under pipefail
# can report nm's SIGPIPE as a failed build even if the symbol was present.
llvm-nm --defined-only out/vmlinux > diagnostics/vmlinux.nm
python3 scripts/verify-sukisu-build.py --config out/.config \
    --baseline diagnostics/base.config --root "$ROOT_ENABLED" \
    --stock-config scripts/a52q-lineage-20260817.config \
    --release diagnostics/kernelrelease.txt \
    --expected-release 4.14.356-openela-rc1-perf-g98de87f1b888 \
    --symbols diagnostics/vmlinux.nm \
    2>&1 | tee diagnostics/symbol-validation.log
