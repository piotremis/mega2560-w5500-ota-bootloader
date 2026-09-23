/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "net.h"
static uint8_t lower(uint8_t c) {
    return c >= 'A' && c <= 'Z' ? c + 32 : c;
}
/* Compare expanded name against host; cap pointer hops to reject cycles. */
static uint16_t name(uint16_t pos, uint16_t n, const char *host, uint8_t *match) {
    uint16_t end = 0;
    uint8_t steps = 0, chars = 0;
    *match = 1;
    while (pos < n && ++steps < 128) {
        uint8_t len = packet[pos++];
        if (!len) {
            if (host[chars]) {
                *match = 0;
            }
            return end ? end : pos;
        }
        if ((len & 0xc0) == 0xc0) {
            if (pos >= n) {
                return 0;
            }
            if (!end) {
                end = pos + 1;
            }
            pos = ((uint16_t)(len & 63) << 8) | packet[pos];
            continue;
        }
        if (len > 63 || len > n - pos) {
            return 0;
        }
        if (chars) {
            if (host[chars] != '.') {
                *match = 0;
            } else {
                chars++;
            }
        }
        while (len--) {
            if (!host[chars] || lower(host[chars]) != lower(packet[pos])) {
                *match = 0;
            }
            if (host[chars]) {
                chars++;
            }
            pos++;
        }
    }
    return 0;
}
uint8_t dns_parse(uint16_t n, const char *host, uint16_t id, uint8_t *ip) {
    if (n < 12 || be16(packet) != id || (packet[2] & 0xfa) != 0x80 || (packet[3] & 15) ||
        be16(packet + 4) != 1) {
        return 0;
    }
    uint8_t match;
    uint16_t p = name(12, n, host, &match);
    if (!p || !match || n - p < 4 || be16(packet + p) != 1 || be16(packet + p + 2) != 1) {
        return 0;
    }
    p += 4;
    uint16_t count = be16(packet + 6);
    while (count--) {
        p = name(p, n, host, &match);
        if (!p || n - p < 10) {
            return 0;
        }
        uint16_t type = be16(packet + p), cls = be16(packet + p + 2), len = be16(packet + p + 8);
        p += 10;
        if (len > n - p) {
            return 0;
        }
        if (match && type == 1 && cls == 1 && len == 4) {
            memcpy(ip, packet + p, 4);
            return 1;
        }
        p += len;
    }
    return 0;
}
uint8_t dns(const char *host, uint8_t *ip) {
    /* Numeric hosts are IPv4 literals: never send them to the DNS server.
     * Four decimal octets are required; leading zeroes are decimal, not octal. */
    const char *literal = host;
    while ((*literal >= '0' && *literal <= '9') || *literal == '.') {
        literal++;
    }
    if (!*literal) {
        for (uint8_t i = 0; i < 4; i++) {
            uint16_t octet = 0;
            uint8_t digits = 0;
            while (*host >= '0' && *host <= '9') {
                octet = octet * 10 + (*host++ - '0');
                if (++digits > 3 || octet > 255) {
                    return 0;
                }
            }
            if (!digits || *host != (i == 3 ? 0 : '.')) {
                return 0;
            }
            ip[i] = octet;
            if (i != 3) {
                host++;
            }
        }
        return 1;
    }
    if (!net_open(2, 49153)) {
        return 0;
    }
    for (uint8_t retry = 0; retry < 3; retry++) {
        uint16_t id = ticks() ^ 0x5731;
        memset(packet, 0, 12);
        put16(packet, id);
        packet[2] = 1;
        packet[5] = 1;
        uint16_t p = 12;
        const char *s = host;
        while (*s) {
            uint16_t length = p++;
            uint8_t len = 0;
            while (*s && *s != '.') {
                if (++len > 63 || p >= 580) {
                    return 0;
                }
                packet[p++] = *s++;
            }
            if (!len) {
                return 0;
            }
            packet[length] = len;
            if (*s) {
                s++;
            }
        }
        packet[p++] = 0;
        put16(packet + p, 1);
        put16(packet + p + 2, 1);
        p += 4;
        if (!udp_send(dns_server, 53, packet, p)) {
            continue;
        }
        uint16_t t = ticks();
        while (!expired(t, 2000)) {
            uint8_t source[4];
            uint16_t port;
            int16_t n = udp_recv(packet, sizeof(packet), source, &port);
            if (n < 0) {
                return 0;
            }
            if (n && port == 53 && !memcmp(source, dns_server, 4) && dns_parse(n, host, id, ip)) {
                net_close();
                return 1;
            }
        }
    }
    return 0;
}
