#pragma once

#include <stdint.h>

/* Minimal UART driver stub for static analysis */

typedef struct {
    int32_t (*Initialize)(void *cb_event);
    int32_t (*Uninitialize)(void);
    int32_t (*PowerControl)(uint32_t state);
    int32_t (*Send)(const void *data, uint32_t num);
    int32_t (*Receive)(void *data, uint32_t num);
    int32_t (*GetTxCount)(void);
    int32_t (*GetRxCount)(void);
    int32_t (*Control)(uint32_t control, uint32_t arg);
    uint32_t (*GetStatus)(void);
} ARM_DRIVER_UART;

/* Fake driver instance */
extern ARM_DRIVER_UART Driver_UART;
