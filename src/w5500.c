/* SPDX-License-Identifier: GPL-2.0-or-later
 * W5500 VDM, socket 0 only. Register definitions per WIZnet W5500 datasheet.
 * Pin configuration: board_pins.h (default Ethernet CS PB0=D53).
 */
#include "net.h"
#ifdef HOST_W5500
#include "../tests/w5500_io.h"
#else
#include <avr/io.h>
#include <util/delay.h>
#endif
#include "board_pins.h"
uint16_t be16(const uint8_t *p) {
    return ((uint16_t)p[0] << 8) | p[1];
}
void put16(uint8_t *p, uint16_t v) {
    p[0] = v >> 8;
    p[1] = v;
}
static uint8_t spi(uint8_t v) {
#ifdef HOST_W5500
    return host_spi(v);
#else
    SPDR = v;
    while (!(SPSR & _BV(SPIF))) {
    }
    return SPDR;
#endif
}
static void transfer(uint8_t block, uint16_t addr, uint8_t *p, uint16_t n, uint8_t wr) {
    W5500_CS_PORT &= ~_BV(W5500_CS_BIT);
#ifdef HOST_W5500
    host_select();
#endif
    spi(addr >> 8);
    spi(addr);
    spi((block << 3) | (wr ? 4 : 0));
    while (n--) {
        uint8_t b = spi(wr ? *p : 0);
        if (!wr) {
            *p = b;
        }
        p++;
    }
    W5500_CS_PORT |= _BV(W5500_CS_BIT);
}
static uint8_t read8(uint8_t b, uint16_t a) {
    uint8_t v;
    transfer(b, a, &v, 1, 0);
    return v;
}
static void write8(uint8_t b, uint16_t a, uint8_t v) {
    transfer(b, a, &v, 1, 1);
}
static uint16_t read16(uint16_t a) {
    uint8_t b[2];
    transfer(1, a, b, 2, 0);
    return be16(b);
}
static void write16(uint16_t a, uint16_t v) {
    uint8_t b[2];
    put16(b, v);
    transfer(1, a, b, 2, 1);
}
static uint16_t stable(uint16_t a) {
    uint16_t t = ticks(), v = read16(a), w;
    do {
        w = v;
        v = read16(a);
        if (expired(t, 100)) {
            return 0;
        }
    } while (w != v);
    return v;
}
static uint8_t command(uint8_t c) {
    write8(1, 1, c);
    uint16_t t = ticks();
    while (read8(1, 1)) {
        if (expired(t, 100)) {
            return 0;
        }
    }
    return 1;
}
uint8_t net_status(void) {
    return read8(1, 3);
}
void net_close(void) {
    command(0x10);
}
uint8_t net_init(const uint8_t *mac) {
    W5500_SPI_PORT |= _BV(W5500_SPI_SS_BIT);
    W5500_CS_PORT |= _BV(W5500_CS_BIT);
    W5500_SPI_DDR |= _BV(W5500_SPI_SS_BIT) | _BV(W5500_SPI_SCK_BIT) | _BV(W5500_SPI_MOSI_BIT);
    W5500_SPI_DDR &= ~_BV(W5500_SPI_MISO_BIT);
    W5500_CS_DDR |= _BV(W5500_CS_BIT);
    SPCR = _BV(SPE) | _BV(MSTR);
    SPSR = _BV(SPI2X);
    write8(0, 0, 0x80);
    _delay_ms(60);
    if (read8(0, 0x39) != 4 || read8(0, 0) != 0) {
        return 0;
    }
    transfer(0, 9, (uint8_t *)mac, 6, 1);
    /* Reset default: 2 KiB RX + 2 KiB TX per socket, including socket 0. */
    write8(0, 0x1b, 3);
    return 1;
}
void net_config(const uint8_t *ip, const uint8_t *mask, const uint8_t *gw) {
    transfer(0, 1, (uint8_t *)gw, 4, 1);
    transfer(0, 5, (uint8_t *)mask, 4, 1);
    transfer(0, 15, (uint8_t *)ip, 4, 1);
}
uint8_t net_open(uint8_t mode, uint16_t port) {
    net_close();
    write8(1, 0, mode);
    write16(4, port);
    write8(1, 2, 255);
    return command(1) && net_status() == (mode == 2 ? 0x22 : 0x13);
}
static void destination(const uint8_t *ip, uint16_t port) {
    transfer(1, 0x0c, (uint8_t *)ip, 4, 1);
    write16(0x10, port);
}
uint8_t net_connect(const uint8_t *ip, uint16_t port) {
    if (!net_open(1, 49152)) {
        return 0;
    }
    destination(ip, port);
    if (!command(4)) {
        return 0;
    }
    uint16_t t = ticks();
    while (net_status() != 0x17) {
        if (net_status() == 0 || expired(t, 3000)) {
            return 0;
        }
    }
    return 1;
}
uint8_t net_send(const void *data, uint16_t n) {
    if (n > 2048) {
        return 0;
    }
    uint16_t t = ticks();
    while (stable(0x20) < n) {
        if (expired(t, 3000)) {
            return 0;
        }
    }
    uint16_t wr = read16(0x24);
    transfer(2, wr, (uint8_t *)data, n, 1);
    write16(0x24, wr + n);
    write8(1, 2, 0x18);
    if (!command(0x20)) {
        return 0;
    }
    t = ticks();
    for (;;) {
        uint8_t ir = read8(1, 2);
        if (ir & 8 || expired(t, 3000)) {
            return 0;
        }
        if (ir & 16) {
            return 1;
        }
    }
}
uint8_t udp_send(const uint8_t *ip, uint16_t port, const void *p, uint16_t n) {
    destination(ip, port);
    return net_send(p, n);
}
static void consume(uint16_t rd, uint16_t n) {
    write16(0x28, rd + n);
    command(0x40);
}
int16_t net_recv(uint8_t *p, uint16_t cap) {
    uint16_t n = stable(0x26);
    if (!n) {
        return net_status() == 0 || net_status() == 0x1c ? -1 : 0;
    }
    if (n > cap) {
        n = cap;
    }
    uint16_t rd = read16(0x28);
    transfer(3, rd, p, n, 0);
    consume(rd, n);
    return n;
}
int16_t udp_recv(uint8_t *p, uint16_t cap, uint8_t *ip, uint16_t *port) {
    uint16_t available = stable(0x26);
    if (available < 8) {
        return 0;
    }
    uint16_t rd = read16(0x28);
    uint8_t h[8];
    transfer(3, rd, h, 8, 0);
    uint16_t n = be16(h + 6);
    if (n > 2040 || available < n + 8) {
        net_close();
        return -1;
    }
    if (n > cap) {
        consume(rd, n + 8);
        return 0;
    }
    memcpy(ip, h, 4);
    *port = be16(h + 4);
    transfer(3, rd + 8, p, n, 0);
    consume(rd, n + 8);
    return n;
}
