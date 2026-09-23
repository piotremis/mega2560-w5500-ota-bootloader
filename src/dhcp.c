/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "net.h"
uint8_t dns_server[4];
static uint8_t offered[4], server[4], mask[4], gateway[4];
uint8_t dhcp_parse(uint16_t n, uint8_t kind, const uint8_t *xid, const uint8_t *mac) {
    if (n < 240 || packet[0] != 2 || packet[1] != 1 || packet[2] != 6 ||
        memcmp(packet + 4, xid, 4) || memcmp(packet + 28, mac, 6) ||
        memcmp(packet + 236, "\x63\x82\x53\x63", 4)) {
        return 0;
    }
    uint8_t type = 0, flags = 0, end = 0;
    uint8_t srv[4], m[4], g[4], d[4];
    for (uint16_t i = 240; i < n;) {
        uint8_t opt = packet[i++];
        if (opt == 255) {
            end = 1;
            break;
        }
        if (!opt) {
            continue;
        }
        if (i >= n) {
            return 0;
        }
        uint8_t len = packet[i++];
        if (len > n - i) {
            return 0;
        }
        uint8_t *p = packet + i;
        i += len;
        if (opt == 53) {
            if (len != 1 || type) {
                return 0;
            }
            type = *p;
        }
        if (opt == 54) {
            if (len != 4) {
                return 0;
            }
            memcpy(srv, p, 4);
            flags |= 1;
        }
        if (opt == 1) {
            if (len != 4) {
                return 0;
            }
            memcpy(m, p, 4);
            flags |= 2;
        }
        if (opt == 3 || opt == 6) {
            if (!len || len % 4) {
                return 0;
            }
            memcpy(opt == 3 ? g : d, p, 4);
            flags |= opt == 3 ? 4 : 8;
        }
    }
    if (!end || type != kind || !(flags & 1) || !packet[16] || packet[16] >= 224) {
        return 0;
    }
    if (kind == 2) {
        memcpy(offered, packet + 16, 4);
        memcpy(server, srv, 4);
        return 1;
    }
    if (flags != 15 || memcmp(server, srv, 4) || memcmp(offered, packet + 16, 4)) {
        return 0;
    }
    memcpy(mask, m, 4);
    memcpy(gateway, g, 4);
    memcpy(dns_server, d, 4);
    return 1;
}
static void request(uint8_t kind, const uint8_t *xid) {
    memset(packet, 0, 300);
    packet[0] = 1;
    packet[1] = 1;
    packet[2] = 6;
    memcpy(packet + 4, xid, 4);
    packet[10] = 0x80;
    memcpy(packet + 28, cfg.mac, 6);
    memcpy(packet + 236, "\x63\x82\x53\x63", 4);
    uint16_t i = 240;
    packet[i++] = 53;
    packet[i++] = 1;
    packet[i++] = kind;
    packet[i++] = 55;
    packet[i++] = 3;
    packet[i++] = 1;
    packet[i++] = 3;
    packet[i++] = 6;
    if (kind == 3) {
        packet[i++] = 50;
        packet[i++] = 4;
        memcpy(packet + i, offered, 4);
        i += 4;
        packet[i++] = 54;
        packet[i++] = 4;
        memcpy(packet + i, server, 4);
        i += 4;
    }
    packet[i] = 255;
}
uint8_t dhcp(void) {
    uint8_t xid[4];
    memcpy(xid, cfg.mac + 2, 4);
    xid[0] ^= 0xb7;
    const uint8_t broadcast[4] = {255, 255, 255, 255};
    if (!net_open(2, 68)) {
        return 0;
    }
    for (uint8_t state = 1; state <= 3; state += 2) {
        uint8_t got = 0;
        for (uint8_t retry = 0; retry < 3 && !got; retry++) {
            request(state, xid);
            if (!udp_send(broadcast, 67, packet, 300)) {
                continue;
            }
            uint16_t t = ticks();
            while (!expired(t, 2000)) {
                uint8_t ip[4];
                uint16_t port;
                int16_t n = udp_recv(packet, sizeof(packet), ip, &port);
                if (n < 0) {
                    return 0;
                }
                if (n && port == 67 && dhcp_parse(n, state == 1 ? 2 : 5, xid, cfg.mac)) {
                    got = 1;
                    break;
                }
            }
        }
        if (!got) {
            return 0;
        }
    }
    net_close();
    net_config(offered, mask, gateway);
    return 1;
}
