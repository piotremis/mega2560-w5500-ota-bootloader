/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <avr/io.h>
#include <avr/wdt.h>
void early(void) __attribute__((naked, section(".init3"), used));
void early(void) {
    MCUSR = 0;
    wdt_disable();
}
