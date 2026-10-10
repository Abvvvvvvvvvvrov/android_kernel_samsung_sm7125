# SukiSU Ultra builtin snapshot

Repository: https://github.com/SukiSU-Ultra/SukiSU-Ultra

Branch: `builtin`

Commit: `6c284e957feaa9a388a9f1c37dc4ec80d95e434b`

Imported directory: `kernel/`. This is an ordinary vendored directory, with
no submodule, nested Git repository, or symlink. The previous KernelSU-Next
implementation and its obsolete Kbuild/hook files are removed.

Target: Samsung SM7125/A52q arm64 kernel 4.14.356. The integration requires
`CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=n`, and `CONFIG_KPM=n`.

The upstream GPL-2.0 license is preserved byte for byte. Its Git blob is
`d159169d1050894d3ea3b98e1c965c4058208fe1`.

## Local changes to the imported source

- `Makefile`: pin metadata instead of running Git, curl, or a network fetch
  during compilation. The fully fetched pinned builtin commit has 815 reachable
  commits, giving numeric version 38000 using the upstream formula
  `40000 + 815 - 2815`. Version string `v4.2.0-6c284e95@builtin` identifies the
  4.2.0 release family and this exact builtin snapshot, not the release tag.
  The no-SUSFS build reports manual builtin hooks. Detect the kernel's
  `enforcing_enabled()` accessor in addition to its SELinux state structure.
- `Kconfig`: default SUSFS to disabled. A future SUSFS integration must use
  a matching filesystem implementation and matching hook ABI; this patch
  does not supply those hooks.
- `runtime/ksud.c`: guard SELinux policy-hiding lifecycle calls with the same
  `>= 5.10` condition used to compile their implementation. The 4.14 target
  does not provide these functions.
- `selinux/selinux.c`: use the kernel's enforcing accessors when available.
  Samsung's SELinux backport keeps the effective enforcing value in
  `selinux_enforcing`, rather than `selinux_state.enforcing`.
- `feature/sucompat.c` and `.h`: return 1 only after an authorized `su` exec
  has successfully changed credentials and redirected to an existing `ksud`.
  The manual exec hook installs a restricted su-session descriptor only after
  exec succeeds and closes the old CLOEXEC descriptors. Failed execs, ordinary
  executables, direct ksud launches, and the shell fallback do not receive it.
  Failure to allocate the descriptor is logged. This preserves the upstream
  per-descriptor permissions needed by profiles with a nonzero target UID.
- `manager/pkg_observer.c`: supply the existing mark destructor through
  `fsnotify_ops.free_mark` on kernels >= 4.12. This target's `fsnotify_put_mark()`
  calls that function unconditionally, so leaving it NULL can panic the kernel.
- `policy/allowlist.c`: replace the modern `fallthrough` macro, absent in the
  target compiler headers, with the equivalent fallthrough comment.
- `policy/app_profile.c`: OR the capability bit `1ULL << CAP_DAC_READ_SEARCH`
  into the temporary effective capabilities, rather than the capability number.
- Text files use LF line endings. Trailing whitespace and one Kconfig
  indentation issue are normalized without changing source behavior.

## Manual-hook contract

The kernel-side header is `include/linux/sukisu.h`. Hook declarations must
match this snapshot; declarations from KernelSU-Next are incompatible.

- Exec: call `ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags)` after
  rejecting error filenames and only for a non-NULL filename. Save whether its
  result is 1; call `ksu_handle_su_execveat_success()` on that condition only
  after `exec_binprm()` succeeds. Keep `fs/exec.c:get_user_arg_ptr()` static:
  SukiSU's runtime implements its own helper.
- Init rc read: call the three-argument
  `ksu_handle_sys_read(fd, &buf, &count)` while `ksu_vfs_read_hook` is enabled.
  Its filesystem proxy appends ksud lifecycle actions to the first main init rc.
- Init rc size: after successful fd stat, call
  `ksu_handle_vfs_fstat(fd, &stat->size)` while `ksu_vfs_read_hook` is enabled.
- Access/stat: the no-SUSFS ABI takes `const char __user **` paths, not
  `struct filename **` paths.
- Reboot: the manager obtains its driver descriptor through the magic reboot
  call; call `ksu_handle_sys_reboot(magic1, magic2, cmd, &arg)` before the
  original reboot capability/argument checks. Preserve the ordinary syscall's
  behavior after the hook.
- UID transitions: the vendor registers `task_fix_setuid` through its LSM
  initialization. Do not add the SUSFS `setresuid` hook for this configuration.
- Input: the vendor registers an input handler for safe-mode volume keys.
  Its inline `ksu_handle_input_handle_event()` stub does nothing, so the old
  KernelSU-Next input-core hook is removed.

Static integration checks and clean patch validation do not establish that
the kernel compiles or boots on the device. The GitHub Actions full build and
an actual A52q boot test are the remaining validation stages.
