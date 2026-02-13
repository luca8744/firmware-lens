#pragma once

/* Minimal STM32F2 stub for static analysis */

#define __IO volatile
#define __I  volatile const
#define __O  volatile

typedef unsigned int uint32_t;
typedef unsigned short uint16_t;
typedef unsigned char uint8_t;

/* Fake peripheral base types */
typedef struct {
    volatile uint32_t CR;
} GPIO_TypeDef;

#define GPIOA ((GPIO_TypeDef*)0x40020000)
