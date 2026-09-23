/* SPDX-License-Identifier: GPL-2.0-or-later
 * Project adaptation modified 2026-09-18; original attribution follows.
 * Derived from Arduino stk500boot.c, Peter Fleury (C) 2006,
 * Worapoht Kornkaewwattanakul and Mark Sproul; see docs/ARDUINO-NOTICE.txt.
 * AVR068 framing/dispatcher retained; bounded lengths, raw word addressing,
 * page read/modify/write and recovery integration replace unsafe legacy paths.
 */
#include "boot.h"
#include "command.h"
#ifdef __AVR__
#include <avr/boot.h>
#else
uint8_t host_fuse(uint8_t a);
#define boot_lock_fuse_bits_get(a) host_fuse(a)
#define GET_LOW_FUSE_BITS 0
#define GET_HIGH_FUSE_BITS 3
#define GET_EXTENDED_FUSE_BITS 2
#define GET_LOCK_BITS 1
#endif
#define CONFIG_PARAM_BUILD_NUMBER_LOW 0
#define CONFIG_PARAM_BUILD_NUMBER_HIGH 0
#define CONFIG_PARAM_HW_VER 15
#define CONFIG_PARAM_SW_MAJOR 2
#define CONFIG_PARAM_SW_MINOR 10
static uint32_t address;
static uint8_t leave;
static uint8_t sig(uint8_t i) {
    return i == 0 ? 0x1e : i == 1 ? 0x98 : 0x01;
}
static uint8_t fuse(uint8_t op, uint8_t sub) {
    if (op == 0x50) {
        if (sub == 8) {
            return boot_lock_fuse_bits_get(GET_EXTENDED_FUSE_BITS);
        }
        return boot_lock_fuse_bits_get(GET_LOW_FUSE_BITS);
    }
    if (sub == 8) {
        return boot_lock_fuse_bits_get(GET_HIGH_FUSE_BITS);
    }
    return boot_lock_fuse_bits_get(GET_LOCK_BITS);
}
/* Out-of-line dispatcher keeps LTO within the 8 KiB boot budget. */
uint16_t __attribute__((noinline)) stk_command(uint16_t n) {
    uint16_t out = 2, size = 0;
    uint32_t a;
    if (!n) {
        return 0;
    }
    uint8_t cmd = packet[0];
    /* Validate before accessing any command-specific field. */
    uint8_t need = 1;
    switch (cmd) {
    case CMD_GET_PARAMETER:
        need = 2;
        break;
    case CMD_SET_PARAMETER:
        need = 3;
        break;
    case CMD_LOAD_ADDRESS:
    case CMD_READ_SIGNATURE_ISP:
    case CMD_READ_FUSE_ISP:
    case CMD_READ_LOCK_ISP:
        need = 5;
        break;
    case CMD_SPI_MULTI:
        need = 8;
        break;
    case CMD_READ_FLASH_ISP:
    case CMD_READ_EEPROM_ISP:
        need = 4;
        break;
    case CMD_PROGRAM_FLASH_ISP:
    case CMD_PROGRAM_EEPROM_ISP:
        need = 10;
        break;
    }
    if (n < need) {
        packet[1] = STATUS_CMD_FAILED;
        return 2;
    }
    switch (cmd) {
#include "arduino_cases.inc"
    case CMD_SET_DEVICE_PARAMETERS:
    case CMD_SET_PARAMETER:
    case CMD_ENTER_PROGMODE_ISP:
        packet[1] = STATUS_CMD_OK;
        break;
    case CMD_LEAVE_PROGMODE_ISP:
        leave = 1;
        packet[1] = STATUS_CMD_OK;
        break;
    case CMD_LOAD_ADDRESS:
        address = ((uint32_t)(packet[1] & 0x7f) << 24) | ((uint32_t)packet[2] << 16) |
                  ((uint16_t)packet[3] << 8) | packet[4];
        packet[1] = STATUS_CMD_OK;
        break;
    case CMD_READ_SIGNATURE_ISP:
        packet[2] = sig(packet[4]);
        packet[1] = packet[3] = STATUS_CMD_OK;
        out = 4;
        break;
    case CMD_READ_FUSE_ISP:
    case CMD_READ_LOCK_ISP:
        packet[2] = fuse(packet[2], packet[3]);
        packet[1] = packet[3] = STATUS_CMD_OK;
        out = 4;
        break;
    case CMD_SPI_MULTI: {
        if (packet[1] != 4 || packet[2] != 4 || packet[3] != 0) {
            goto fail;
        }
        uint8_t op = packet[4], ans = 0;
        if (op == 0x30) {
            ans = sig(packet[6]);
        } else if (op == 0x50 || op == 0x58) {
            ans = fuse(op, packet[5]);
        }
        packet[1] = 0;
        packet[2] = 0;
        packet[3] = op;
        packet[4] = 0;
        packet[5] = ans;
        packet[6] = 0;
        out = 7;
        break;
    }
    case CMD_PROGRAM_FLASH_ISP:
    case CMD_PROGRAM_EEPROM_ISP:
    case CMD_READ_FLASH_ISP:
    case CMD_READ_EEPROM_ISP: {
        uint8_t flash = cmd == CMD_PROGRAM_FLASH_ISP || cmd == CMD_READ_FLASH_ISP;
        uint8_t write = cmd == CMD_PROGRAM_FLASH_ISP || cmd == CMD_PROGRAM_EEPROM_ISP;
        size = ((uint16_t)packet[1] << 8) | packet[2];
        if (!size || size > 256 || (write && n != size + 10)) {
            goto fail;
        }
        if (flash) {
            if (address >= (write ? APP_END / 2 : 0x20000UL) || (size & 1)) {
                goto fail;
            }
            a = address * 2;
            if (write ? !range_ok(a, size) : size > 0x40000UL - a) {
                goto fail;
            }
        } else {
            a = address;
            if (a >= 4096 || size > 4096 - a) {
                goto fail;
            }
        }
        if (write && flash) {
            /* avrdude sends <=256 bytes. Preserve unspecified page bytes. */
            if ((a & 255) + size > 256) {
                goto fail;
            }
            uint32_t base = a & ~255UL;
            for (uint16_t i = 0; i < 256; i++) {
                page[i] = flash_read(base + i);
            }
            memcpy(page + (uint8_t)a, packet + 10, size);
            if (!flash_write(base, page)) {
                goto fail;
            }
        } else {
            for (uint16_t i = 0; i < size; i++) {
                if (write) {
                    ee_write(a + i, packet[10 + i]);
                } else {
                    packet[2 + i] = flash ? flash_read(a + i) : ee_read(a + i);
                }
            }
        }
        address += flash ? size / 2 : size;
        packet[1] = STATUS_CMD_OK;
        if (!write) {
            out = size + 3;
            packet[out - 1] = STATUS_CMD_OK;
        }
        break;
    }
    default:
    fail:
        packet[1] = STATUS_CMD_FAILED;
        break;
    }
    return out;
}
void stk500(void) {
    uint8_t state = 0, seq = 0, sum = 0;
    uint16_t n = 0, i = 0;
    leave = 0;
    address = 0;
    while (!leave) {
        int16_t v = uart_get(2000);
        if (v < 0) {
            return;
        }
        uint8_t c = v;
        switch (state) {
        case 0:
            if (c == MESSAGE_START) {
                sum = c;
                state = 1;
            }
            break;
        case 1:
            seq = c;
            sum ^= c;
            state = 2;
            break;
        case 2:
            n = (uint16_t)c << 8;
            sum ^= c;
            state = 3;
            break;
        case 3:
            n |= c;
            sum ^= c;
            state = n && n <= 266 ? 4 : 0;
            break;
        case 4:
            if (c != TOKEN) {
                state = 0;
                break;
            }
            sum ^= c;
            i = 0;
            state = 5;
            break;
        case 5:
            packet[i++] = c;
            sum ^= c;
            if (i == n) {
                state = 6;
            }
            break;
        case 6:
            state = 0;
            if (c != sum) {
                break;
            }
            n = stk_command(n);
            uart_put(MESSAGE_START);
            uart_put(seq);
            uart_put(n >> 8);
            uart_put(n);
            uart_put(TOKEN);
            sum = MESSAGE_START ^ seq ^ (n >> 8) ^ (uint8_t)n ^ TOKEN;
            for (i = 0; i < n; i++) {
                uart_put(packet[i]);
                sum ^= packet[i];
            }
            uart_put(sum);
            break;
        }
    }
}
