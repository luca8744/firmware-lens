#pragma once

/* ARMCC / Keil specific keywords */
#define __asm
#define __ASM
#define __irq
#define __packed __attribute__((packed))
#define __weak __attribute__((weak))
#define __align(x) __attribute__((aligned(x)))
#define __forceinline __attribute__((always_inline))
#define __STATIC_INLINE static inline
#define __INLINE inline

/* CMSIS qualifiers */
#define __IO volatile
#define __I  volatile const
#define __O  volatile

/* Ignore attributes not supported by clang */
#define __attribute__(x)

/* Interrupt handlers / misc */
#define __attribute_used__

/* ---- bool support (C99) ---- */
#ifndef __cplusplus
typedef _Bool bool;
#define true  1
#define false 0
#endif

