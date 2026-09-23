/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "net.h"
static uint16_t rx_pos, rx_len;
#include "url_parse.h"
uint8_t url_parse(char *s, Url *u) {
    return url_parse_impl(s, u);
}
int16_t http_byte(void) {
    if (rx_pos == rx_len) {
        uint16_t t = ticks();
        int16_t n;
        do {
            n = net_recv(packet, sizeof(packet));
            if (n < 0 || expired(t, 3000)) {
                return -1;
            }
        } while (!n);
        rx_pos = 0;
        rx_len = n;
    }
    return packet[rx_pos++];
}
static uint8_t equal(const char *a, const char *b) {
    while (*a && *b) {
        char c = *a++;
        if (c >= 'A' && c <= 'Z') {
            c += 32;
        }
        if (c != *b++) {
            return 0;
        }
    }
    return !*a && !*b;
}
int8_t http_header(char *line, uint32_t expected, uint8_t *seen) {
    if (!*line) {
        return *seen ? 1 : -1;
    }
    char *colon = strchr(line, ':');
    if (!colon || colon == line) {
        return -1;
    }
    *colon++ = 0;
    for (char *p = line; *p; p++) {
        if (*p <= 32 || *p >= 127) {
            return -1;
        }
    }
    while (*colon == ' ' || *colon == '\t') {
        colon++;
    }
    if (equal(line, "transfer-encoding") || equal(line, "content-encoding")) {
        return -1;
    }
    if (equal(line, "content-length")) {
        if (*seen || *colon < '0' || *colon > '9') {
            return -1;
        }
        uint32_t v = 0;
        while (*colon >= '0' && *colon <= '9') {
            uint8_t digit = *colon++ - '0';
            if (v > APP_END / 10) {
                return -1;
            }
            v = v * 10 + digit;
            if (v > APP_END) {
                return -1;
            }
        }
        while (*colon == ' ' || *colon == '\t') {
            colon++;
        }
        if (*colon || !v || v != expected) {
            return -1;
        }
        *seen = 1;
    }
    return 0;
}
static uint8_t sendstr(const char *s) {
    return net_send(s, strlen(s));
}
uint8_t http_open(const Url *u, const uint8_t *ip, uint32_t size) {
    if (!net_connect(ip, u->port)) {
        return 0;
    }
    /* A bounded request in page buffer, independent of RX packet buffer. */
    char *p = (char *)page;
    strcpy(p, "GET /");
    strcat(p, u->path);
    strcat(p, " HTTP/1.0\r\nHost: ");
    strcat(p, u->host);
    if (u->port != 80) {
        char digits[6];
        uint16_t v = u->port;
        uint8_t n = 0;
        do {
            digits[n++] = '0' + v % 10;
            v /= 10;
        } while (v);
        uint16_t i = strlen(p);
        p[i++] = ':';
        while (n) {
            p[i++] = digits[--n];
        }
        p[i] = 0;
    }
    strcat(p, "\r\nConnection: close\r\n\r\n");
    if (!sendstr(p)) {
        return 0;
    }
    rx_pos = rx_len = 0;
    uint16_t total = 0;
    uint8_t first = 1, seen = 0;
    for (;;) {
        uint16_t n = 0;
        for (;;) {
            int16_t c = http_byte();
            if (c < 0 || ++total > 2048) {
                return 0;
            }
            if (c == '\r') {
                if (http_byte() != '\n' || ++total > 2048) {
                    return 0;
                }
                break;
            }
            if (c == '\n' || !c || n >= 255) {
                return 0;
            }
            page[n++] = c;
        }
        page[n] = 0;
        if (first) {
            if (n < 12 || memcmp(page, "HTTP/1.", 7) || (page[7] != '0' && page[7] != '1') ||
                memcmp(page + 8, " 200", 4) || (n > 12 && page[12] != ' ')) {
                return 0;
            }
            first = 0;
        } else {
            int8_t r = http_header((char *)page, size, &seen);
            if (r) {
                return r == 1;
            }
        }
    }
}
