#pragma once

#include <stdint.h>

/* CMSIS-RTOS v1 minimal but COMPLETE stub for static analysis */

typedef enum {
    osEventSignal = 0x08,
    osEventMessage = 0x10,
    osEventMail = 0x20,
    osEventTimeout = 0x40,
    osErrorOS = 0x80
} osStatus;

typedef struct {
    osStatus status;
    union {
        uint32_t v;
        void *p;
    } value;
} osEvent;

typedef void *osThreadId;
typedef void *osMutexId;
typedef void *osSemaphoreId;
typedef void *osMessageQId;
typedef void *osTimerId;

#define osWaitForever 0xFFFFFFFFU

/* Thread definitions */
typedef enum {
    osPriorityIdle = -3,
    osPriorityLow,
    osPriorityBelowNormal,
    osPriorityNormal,
    osPriorityAboveNormal,
    osPriorityHigh,
    osPriorityRealtime
} osPriority;

typedef struct {
    const char *name;
    osPriority priority;
    uint32_t instances;
    uint32_t stacksize;
} osThreadDef_t;

#define osThreadDef(name, priority, instances, stacksz)

/* API stubs */
osThreadId osThreadCreate(const osThreadDef_t *thread_def, void *arg);
void osDelay(uint32_t millisec);
void osThreadYield(void);

osEvent osSignalWait(uint32_t signals, uint32_t millisec);
int32_t osSignalSet(osThreadId thread_id, int32_t signals);
