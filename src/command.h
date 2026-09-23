/* SPDX-License-Identifier: GPL-2.0-or-later
 * Project-authored protocol subset, 2026-09-23.
 * Numeric wire identifiers for Arduino/STK500v2 interoperability.
 * Protocol reference: Microchip AVR068 (doc2591), sections 3 and 5.
 * This is not the Atmel command.h source file. Only the identifiers used by
 * this bootloader and the ATmega2560 baseline build are defined here.
 */
#ifndef MEGA_STK_PROTOCOL_H
#define MEGA_STK_PROTOCOL_H

enum {
    MESSAGE_START = 0x1b,
    TOKEN = 0x0e,
    STATUS_CMD_OK = 0x00,
    STATUS_CMD_FAILED = 0xc0,

    PARAM_HW_VER = 0x90,
    PARAM_SW_MAJOR = 0x91,
    PARAM_SW_MINOR = 0x92,
    PARAM_BUILD_NUMBER_HIGH = 0x81,
    PARAM_BUILD_NUMBER_LOW = 0x80,

    CMD_SIGN_ON = 0x01,
    CMD_GET_PARAMETER = 0x03,
    CMD_SET_PARAMETER = 0x02,
    CMD_SET_DEVICE_PARAMETERS = 0x04,
    CMD_LOAD_ADDRESS = 0x06,
    CMD_ENTER_PROGMODE_ISP = 0x10,
    CMD_LEAVE_PROGMODE_ISP = 0x11,
    CMD_CHIP_ERASE_ISP = 0x12,
    CMD_READ_FLASH_ISP = 0x14,
    CMD_PROGRAM_FLASH_ISP = 0x13,
    CMD_READ_EEPROM_ISP = 0x16,
    CMD_PROGRAM_EEPROM_ISP = 0x15,
    CMD_READ_FUSE_ISP = 0x18,
    CMD_READ_LOCK_ISP = 0x1a,
    CMD_PROGRAM_LOCK_ISP = 0x19,
    CMD_READ_SIGNATURE_ISP = 0x1b,
    CMD_SPI_MULTI = 0x1d
};
#endif
