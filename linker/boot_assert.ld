/* Augment avr6.x, never replace its AVR startup/data layout. */
SECTIONS { .boot_assert : { PROVIDE(__boot_limit = 0x40000); } }
INSERT AFTER .text;
ASSERT(ADDR(.text) == 0x3e000, "Boot start must be 0x3e000")
ASSERT(ADDR(.text) + SIZEOF(.text) <= 0x40000, "Boot text exceeds 8 KiB")
ASSERT(__data_load_end <= 0x40000, "Boot text plus data initializers exceeds 8 KiB")
