/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef URL_PARSE_H
#define URL_PARSE_H
#include "net.h"
/* Shared parser: callers supply a bounded, NUL-terminated mutable copy. */
static uint8_t url_parse_impl(char *s, Url *u) {
    if (strncmp(s, "http://", 7)) {
        return 0;
    }
    char *host = s + 7, *p = host;
    uint8_t label = 0;
    while (*p && *p != ':' && *p != '/') {
        char c = *p++;
        if (c == '.') {
            if (!label) {
                return 0;
            }
            label = 0;
        } else {
            if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
                  c == '-') ||
                ++label > 63) {
                return 0;
            }
        }
    }
    if (!label) {
        return 0;
    }
    char *end = p;
    u->port = 80;
    if (*p == ':') {
        uint16_t port = 0;
        p++;
        char *start = p;
        while (*p >= '0' && *p <= '9') {
            if (port > 6553 || (port == 6553 && *p > '5')) {
                return 0;
            }
            port = port * 10 + (*p++ - '0');
        }
        if (p == start || !port) {
            return 0;
        }
        u->port = port;
    }
    if (*p != '/') {
        return 0;
    }
    /* Path stored without initial slash, emitted separately after GET. */
    u->path = p + 1;
    u->host = host;
    for (char *q = p; *q; q++) {
        if ((uint8_t)*q <= 32 || (uint8_t)*q >= 127 || *q == '#') {
            return 0;
        }
    }
    *end = 0;
    return 1;
}
#endif
