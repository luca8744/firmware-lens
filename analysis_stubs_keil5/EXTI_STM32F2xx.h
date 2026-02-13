#pragma once

#include <stdint.h>

/* Minimal EXTI stub for static analysis */

typedef struct {
    volatile uint32_t IMR;
    volatile uint32_t EMR;
    volatile uint32_t RTSR;
    volatile uint32_t FTSR;
    volatile uint32_t SWIER;
    volatile uint32_t PR;
} EXTI_TypeDef;

#define EXTI ((EXTI_TypeDef *)0x40013C00)

/* Fake EXTI lines */
#define EXTI_Line0   (1U << 0)
#define EXTI_Line1   (1U << 1)
#define EXTI_Line2   (1U << 2)
#define EXTI_Line3   (1U << 3)
#define EXTI_Line4   (1U << 4)
