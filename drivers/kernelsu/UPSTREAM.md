# KernelSU Next legacy

Source: https://github.com/KernelSU-Next/KernelSU-Next

Pinned commit: b933b1f728116a456fbebf27b6a8772a640cdf23 (2026-10-28).
Version: 33318 (30000 + 3029 commits + 289); tag v3.4.0-legacy-b933b1f7.
Built into Samsung A52q kernel 4.14 with manual hooks.

Local compatibility adjustments: use the backported ktime_get_boottime_ts64 API and Samsung SELinux enforcing accessors, and register the fsnotify mark destructor required by this kernel. The upstream UAPI symlink is vendored as ordinary files.
