/* Host substitute for AVR registers; only used with HOST_W5500. */
#include <stdint.h>
#define _BV(n) (1U << (n))
#define SPE 6
#define MSTR 4
#define SPI2X 0
extern uint8_t PORTB, DDRB, PORTG, DDRG, SPCR, SPSR;
void host_select(void);
uint8_t host_spi(uint8_t v);
#define _delay_ms(ms) ((void)(ms))
