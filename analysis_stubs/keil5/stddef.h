#pragma once

/* Minimal stddef.h stub for static analysis */

typedef unsigned long size_t;
typedef long ptrdiff_t;

#define NULL ((void*)0)

/* offsetof macro */
#define offsetof(type, member) ((size_t)&(((type *)0)->member))
