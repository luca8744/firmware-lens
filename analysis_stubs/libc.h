#pragma once

/* Minimal stdio stub for clang static analysis */

typedef struct FILE FILE;

int printf(const char *fmt, ...);
int sprintf(char *str, const char *fmt, ...);
int snprintf(char *str, unsigned long size, const char *fmt, ...);
int puts(const char *s);
int putchar(int c);
