/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_SUKISU_H
#define _LINUX_SUKISU_H

#include <linux/types.h>

#ifdef CONFIG_KSU_SUSFS
#error "These a52q builtin hooks require CONFIG_KSU_SUSFS=n"
#endif

struct filename;

/* SukiSU Ultra builtin 6c284e95, without CONFIG_KSU_SUSFS. */
extern bool ksu_vfs_read_hook;

int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd,
			  void __user **arg);
int ksu_handle_execveat(int *fd, struct filename **filename, void *argv,
			void *envp, int *flags);
void ksu_handle_su_execveat_success(void);
int ksu_handle_faccessat(int *dfd, const char __user **filename,
			 int *mode, int *flags);
int ksu_handle_stat(int *dfd, const char __user **filename, int *flags);
int ksu_handle_sys_read(unsigned int fd, char __user **buf, size_t *count);
void ksu_handle_vfs_fstat(int fd, loff_t *size);

#endif /* _LINUX_SUKISU_H */
