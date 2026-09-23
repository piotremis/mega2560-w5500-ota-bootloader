#include "net.h"
#include "w5500_io.h"
#include "board_pins.h"
uint8_t PORTB, DDRB, PORTG, DDRG, SPCR, SPSR;
uint8_t common[64], sock[64], tx[2048], rx[2048];
int host_timeout, host_busy, host_pin_errors;
static uint16_t tick, addr, rx_committed;
static uint8_t step, block, write;
void host_select(void) {
    step = 0;
}
static uint16_t get(uint8_t a) {
    return ((uint16_t)sock[a] << 8) | sock[a + 1];
}
static void set(uint8_t a, uint16_t v) {
    sock[a] = v >> 8;
    sock[a + 1] = v;
}
uint8_t host_spi(uint8_t v) {
    if ((W5500_CS_PORT & _BV(W5500_CS_BIT)) || !(W5500_CS_DDR & _BV(W5500_CS_BIT)) || !(DDRB & 1)) {
        host_pin_errors++;
    }
    if (step == 0) {
        addr = (uint16_t)v << 8;
        step++;
        return 0;
    }
    if (step == 1) {
        addr |= v;
        step++;
        return 0;
    }
    if (step == 2) {
        block = v >> 3;
        write = v & 4;
        step++;
        return 0;
    }
    uint16_t a = addr++;
    uint8_t *mem = block == 0 ? common : block == 1 ? sock : block == 2 ? tx : rx;
    uint16_t index = a & (block >= 2 ? 2047 : 63);
    uint8_t value = mem[index];
    if (!write) {
        return value;
    }
    if (block == 0 && a == 0 && v == 128) {
        memset(common, 0, 64);
        memset(sock, 0, 64);
        common[0x39] = 4;
        set(0x20, 2048);
        rx_committed = 0;
        return 0;
    }
    if (block == 1 && a == 2) {
        sock[2] &= ~v;
        return 0;
    }
    mem[index] = v;
    if (block == 1 && a == 1) {
        if (v == 1) {
            sock[3] = sock[0] == 2 ? 0x22 : 0x13;
        }
        if (v == 4) {
            sock[3] = 0x17;
        }
        if (v == 0x10) {
            sock[3] = 0;
        }
        if (v == 0x20) {
            sock[2] |= host_timeout ? 8 : 16;
        }
        if (v == 0x40) {
            set(0x26, get(0x26) - (uint16_t)(get(0x28) - rx_committed));
            rx_committed = get(0x28);
        }
        if (!host_busy) {
            sock[1] = 0;
        }
    }
    return 0;
}
uint16_t ticks(void) {
    return ++tick;
}
uint8_t expired(uint16_t t, uint16_t ms) {
    return (uint16_t)(ticks() - t) >= ms;
}
void model_rx(uint16_t at, const uint8_t *p, uint16_t n) {
    set(0x28, at);
    rx_committed = at;
    set(0x26, n);
    for (uint16_t i = 0; i < n; i++) {
        rx[(at + i) & 2047] = p[i];
    }
}
