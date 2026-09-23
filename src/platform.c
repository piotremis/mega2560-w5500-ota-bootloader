/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "boot.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/boot.h>
#include <avr/eeprom.h>
#include <avr/pgmspace.h>
#include <avr/wdt.h>
#include "board_pins.h"
void platform_init(void) {
    cli();
    TCCR1A = 0;
    TCCR1B = _BV(CS12) | _BV(CS10);
    TCNT1 = 0;
    UCSR0A = _BV(U2X0);
    UBRR0H = 0;
    UBRR0L = 16;
    UCSR0B = _BV(RXEN0) | _BV(TXEN0);
    UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
}
void error_led(void) {
    DDRB |= _BV(7);
    PORTB |= _BV(7);
}
uint16_t ticks(void) {
    return TCNT1;
}
uint8_t expired(uint16_t start, uint16_t ms) {
    /* 64 us ticks. All deadlines <= 3000 ms, strictly below one wrap. */
    return (uint16_t)(ticks() - start) >= (uint16_t)(((uint32_t)ms * 125) / 8);
}
int16_t uart_get(uint16_t timeout) {
    uint16_t t = ticks();
    while (!(UCSR0A & _BV(RXC0))) {
        if (expired(t, timeout)) {
            return -1;
        }
    }
    uint8_t status = UCSR0A, b = UDR0;
    return status & (_BV(FE0) | _BV(DOR0) | _BV(UPE0)) ? -1 : b;
}
void uart_put(uint8_t b) {
    while (!(UCSR0A & _BV(UDRE0))) {
    }
    UDR0 = b;
}
uint8_t ee_read(uint16_t a) {
    return eeprom_read_byte((const uint8_t *)a);
}
void ee_write(uint16_t a, uint8_t b) {
    eeprom_update_byte((uint8_t *)a, b);
    eeprom_busy_wait();
}
uint8_t flash_read(uint32_t a) {
    return pgm_read_byte_far(a);
}
uint8_t flash_write(uint32_t a, const uint8_t *p) {
    if ((a & 255) || !range_ok(a, 256)) {
        return 0;
    }
    eeprom_busy_wait();
    boot_page_erase(a);
    boot_spm_busy_wait();
    for (uint16_t i = 0; i < 256; i += 2) {
        boot_page_fill(a + i, p[i] | ((uint16_t)p[i + 1] << 8));
    }
    boot_page_write(a);
    boot_spm_busy_wait();
    boot_rww_enable();
    return 1;
}
void application(void) {
    while (!(UCSR0A & _BV(UDRE0))) {
    }
    /* Complete last STK reply before disabling UART. */
    __builtin_avr_delay_cycles(3200);
    cli();
    UCSR0B = 0;
    TCCR1B = 0;
    TIFR1 = 0xff;
    SPCR = 0;
    RAMPZ = 0;
    EIND = 0;
    DDRB = 0;
    PORTB = 0;
    W5500_CS_DDR &= ~_BV(W5500_CS_BIT);
    W5500_CS_PORT &= ~_BV(W5500_CS_BIT);
    asm volatile("jmp 0");
    __builtin_unreachable();
}
