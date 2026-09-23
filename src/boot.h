/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BOOT_H
#define BOOT_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
/* Byte addresses: APP_END is exclusive and is also the boot section start. */
#define APP_END 0x3e000UL
#define PAGE_SIZE 256
#define CFG_BASE 3936
#define CFG_FORMAT 1
#define NETWORK_DHCP 0
#define NETWORK_FALLBACK 1
#define NETWORK_STATIC 2
#define PENDING 0xa5
#ifndef STAGE
#define STAGE 12
#endif
/* EEPROM ABI: little endian, exactly 160 bytes. See docs/EEPROM.md. */
typedef struct __attribute__((packed)) {
    uint16_t magic;
    uint8_t format, state;
    uint32_t image_size, image_crc, version;
    uint8_t mac[6], url_len;
    char url[101];
    uint8_t network_mode;
    uint8_t ip[4], mask[4], gateway[4], dns[4];
    uint16_t serial_number;
    uint8_t reserved[13];
    uint32_t record_crc;
} Config;
#ifdef __cplusplus
static_assert(sizeof(Config) == 160, "EEPROM ABI");
#else
_Static_assert(sizeof(Config) == 160, "EEPROM ABI");
_Static_assert(offsetof(Config, network_mode) == 124, "Network mode ABI");
_Static_assert(offsetof(Config, record_crc) == 156, "Record CRC ABI");
_Static_assert(offsetof(Config, serial_number) == 141, "Serial number ABI");
#endif
#ifdef __cplusplus
extern "C" {
#endif
extern Config cfg;
/* Shared across serial/network phases; no concurrent users or heap allocation. */
extern uint8_t packet[600], page[256];
uint16_t ticks(void);
uint8_t expired(uint16_t start, uint16_t ms);
void platform_init(void);
void error_led(void);
void application(void) __attribute__((noreturn));
int16_t uart_get(uint16_t timeout);
void uart_put(uint8_t b);
uint8_t flash_write(uint32_t address, const uint8_t *p);
uint8_t flash_read(uint32_t address);
uint8_t ee_read(uint16_t address);
void ee_write(uint16_t address, uint8_t value);
uint8_t range_ok(uint32_t address, uint16_t count);
uint32_t crc_byte(uint32_t crc, uint8_t b);
uint32_t crc32(const void *data, uint16_t n);
uint8_t cfg_load(void);
uint8_t cfg_valid(const Config *c);
uint8_t cfg_bootable(uint8_t valid);
void cfg_done(void);
void stk500(void);
uint16_t stk_command(uint16_t n);
uint8_t ota(void);
#ifdef __cplusplus
}
#endif
#endif
