/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BOARD_PINS_H
#define BOARD_PINS_H
/* ATmega2560 / Arduino Mega. Edit these three macros together to move CS.
 * D53 = PORTB bit 0 (default); D10 = PORTB bit 4.
 * Values are AVR port bit numbers, NOT Arduino digital pin numbers.
 * Register definitions must be included before this header. */
#ifndef W5500_CS_PORT
#define W5500_CS_PORT PORTB
#endif
#ifndef W5500_CS_DDR
#define W5500_CS_DDR DDRB
#endif
#ifndef W5500_CS_BIT
#define W5500_CS_BIT 0
#endif

/* Hardware SPI pins are FIXED by ATmega2560, not software-remappable.
 * Hardware SS must stay an output, even when Ethernet CS uses another pin. */
#define W5500_SPI_PORT PORTB
#define W5500_SPI_DDR DDRB
#define W5500_SPI_SS_BIT 0   /* D53: may also serve as W5500 CS */
#define W5500_SPI_SCK_BIT 1  /* D52 / ICSP SCK */
#define W5500_SPI_MOSI_BIT 2 /* D51 / ICSP MOSI */
#define W5500_SPI_MISO_BIT 3 /* D50 / ICSP MISO */
/* RSTn: hardware reset plus W5500 MR software reset. INT: unused (polling). */
#endif
