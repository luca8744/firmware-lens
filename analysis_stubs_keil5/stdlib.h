#pragma once

void *malloc(unsigned long size);
void free(void *ptr);
void *calloc(unsigned long n, unsigned long size);
void *realloc(void *ptr, unsigned long size);

void exit(int code);
