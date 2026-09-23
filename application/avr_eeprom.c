/* SPDX-License-Identifier: GPL-2.0-or-later. Link in application, NOT bootloader. */
#include "ota_request.h"
#include <avr/eeprom.h>
uint8_t ee_read(uint16_t a) {
    return eeprom_read_byte((const uint8_t *)a);
}
void ee_write(uint16_t a, uint8_t b) {
    eeprom_update_byte((uint8_t *)a, b);
    eeprom_busy_wait();
}
