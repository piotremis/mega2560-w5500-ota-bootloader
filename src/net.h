/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef NET_H
#define NET_H
#include "boot.h"
typedef struct {
    char *host, *path;
    uint16_t port;
} Url;
extern uint8_t dns_server[4];
uint16_t be16(const uint8_t *p);
void put16(uint8_t *p, uint16_t v);
uint8_t net_init(const uint8_t *mac);
void net_config(const uint8_t *ip, const uint8_t *mask, const uint8_t *gw);
uint8_t net_open(uint8_t mode, uint16_t port);
void net_close(void);
uint8_t net_connect(const uint8_t *ip, uint16_t port);
uint8_t net_send(const void *data, uint16_t n);
uint8_t udp_send(const uint8_t *ip, uint16_t port, const void *p, uint16_t n);
int16_t udp_recv(uint8_t *p, uint16_t cap, uint8_t *ip, uint16_t *port);
int16_t net_recv(uint8_t *p, uint16_t cap);
uint8_t net_status(void);
uint8_t dhcp(void);
uint8_t network_configure(void);
uint8_t dhcp_parse(uint16_t n, uint8_t kind, const uint8_t *xid, const uint8_t *mac);
/* Resolve a hostname or parse dotted-decimal IPv4 without any DNS I/O. */
uint8_t dns(const char *host, uint8_t *ip);
uint8_t dns_parse(uint16_t n, const char *host, uint16_t id, uint8_t *ip);
uint8_t url_parse(char *s, Url *u);
uint8_t http_open(const Url *u, const uint8_t *ip, uint32_t size);
int16_t http_byte(void);
int8_t http_header(char *line, uint32_t expected, uint8_t *seen);
#endif
