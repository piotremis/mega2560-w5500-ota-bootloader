/* SPDX-License-Identifier: GPL-2.0-or-later. Host substitutes ONLY hardware I/O. */
#include "net.h"
#include <stdlib.h>
uint8_t packet[600], page[256], host_flash[0x40000], host_eeprom[4096];
static uint16_t clock_tick;
static uint8_t stream[0x40000 + 4096], udp[600], peer[4];
static uint32_t stream_len, stream_pos;
static uint16_t udp_len, peer_port;
int host_chunk = 600, host_cut = -1, host_writes, host_corrupt, host_closes;
int host_ee_cut = -1, host_ee_writes;
uint8_t host_connect_ip[4];
uint16_t host_connect_port;
uint8_t host_network[12];
static uint8_t (*on_send)(const uint8_t *, uint16_t, uint8_t);
static int16_t (*on_uart_get)(void);
static void (*on_uart_put)(uint8_t);
void host_uart(int16_t (*get)(void), void (*put)(uint8_t)) {
    on_uart_get = get;
    on_uart_put = put;
}
void host_callback(uint8_t (*cb)(const uint8_t *, uint16_t, uint8_t)) {
    on_send = cb;
}
void host_stream(const uint8_t *p, uint32_t n) {
    memcpy(stream, p, n);
    stream_len = n;
    stream_pos = 0;
}
void host_udp(const uint8_t *p, uint16_t n, const uint8_t *ip, uint16_t port) {
    memcpy(udp, p, n);
    udp_len = n;
    memcpy(peer, ip, 4);
    peer_port = port;
}
void host_reset(void) {
    clock_tick = 0;
    stream_len = stream_pos = udp_len = 0;
    host_cut = -1;
    host_writes = host_corrupt = host_closes = 0;
    host_chunk = 600;
}
uint16_t ticks(void) {
    return ++clock_tick;
}
uint8_t expired(uint16_t t, uint16_t ms) {
    return (uint16_t)(ticks() - t) >= ms;
}
uint8_t flash_read(uint32_t a) {
    return host_flash[a] ^ (host_corrupt && a == 0);
}
uint8_t flash_write(uint32_t a, const uint8_t *p) {
    if (!range_ok(a, 256) || (a & 255)) {
        return 0;
    }
    if (host_cut >= 0 && host_writes >= host_cut) {
        return 0;
    }
    memcpy(host_flash + a, p, 256);
    host_writes++;
    return 1;
}
uint8_t ee_read(uint16_t a) {
    return host_eeprom[a];
}
void ee_write(uint16_t a, uint8_t b) {
    if (host_ee_cut >= 0 && host_ee_writes >= host_ee_cut) {
        return;
    }
    host_ee_writes++;
    host_eeprom[a] = b;
}
uint8_t host_fuse(uint8_t a) {
    return a == 0 ? 255 : a == 3 ? 0xd8 : a == 2 ? 0xfd : 0x2f;
}
int16_t uart_get(uint16_t t) {
    (void)t;
    return on_uart_get ? on_uart_get() : -1;
}
void uart_put(uint8_t b) {
    if (on_uart_put) {
        on_uart_put(b);
    }
}
uint16_t be16(const uint8_t *p) {
    return ((uint16_t)p[0] << 8) | p[1];
}
void put16(uint8_t *p, uint16_t v) {
    p[0] = v >> 8;
    p[1] = v;
}
uint8_t net_init(const uint8_t *m) {
    (void)m;
    return 1;
}
void net_config(const uint8_t *a, const uint8_t *b, const uint8_t *c) {
    memcpy(host_network, a, 4);
    memcpy(host_network + 4, b, 4);
    memcpy(host_network + 8, c, 4);
}
uint8_t net_open(uint8_t m, uint16_t p) {
    (void)m;
    (void)p;
    return 1;
}
void net_close(void) {
    host_closes++;
}
uint8_t net_connect(const uint8_t *ip, uint16_t p) {
    memcpy(host_connect_ip, ip, 4);
    host_connect_port = p;
    return 1;
}
uint8_t net_status(void) {
    return 0x17;
}
uint8_t net_send(const void *p, uint16_t n) {
    return on_send ? on_send(p, n, 1) : 1;
}
uint8_t udp_send(const uint8_t *ip, uint16_t port, const void *p, uint16_t n) {
    (void)ip;
    return on_send ? on_send(p, n, port == 67 ? 2 : 3) : 1;
}
int16_t net_recv(uint8_t *p, uint16_t cap) {
    if (stream_pos == stream_len) {
        return -1;
    }
    uint32_t n = stream_len - stream_pos;
    if (n > cap) {
        n = cap;
    }
    if (n > (uint32_t)host_chunk) {
        n = host_chunk;
    }
    memcpy(p, stream + stream_pos, n);
    stream_pos += n;
    return n;
}
int16_t udp_recv(uint8_t *p, uint16_t cap, uint8_t *ip, uint16_t *port) {
    if (!udp_len) {
        return 0;
    }
    uint16_t n = udp_len;
    udp_len = 0;
    if (n > cap) {
        return -1;
    }
    memcpy(p, udp, n);
    memcpy(ip, peer, 4);
    *port = peer_port;
    return n;
}
