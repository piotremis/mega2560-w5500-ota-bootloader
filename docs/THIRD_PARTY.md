# Analiza referencji / Third-party code / licenses

| Projekt / sprawdzona rewizja | MCU | W5500 | Aktualizacja | Protokół | Przydatność |
|---|---|---|---|---|---|
| Arduino STK500v2 | m.in. ATmega2560 | nie | UART | STK500v2 | baza produkcyjnej części serial |
| Athena | m.in. ATmega2560 | tak, osobne definicje W5100/5200/5500 | Ethernet i UART | TFTP + STK500v2 | referencja SPI, resetu, EEPROM i organizacji |
| Ariadne, dostępny fork per1234 | ATmega2560 i inne | **nie w analizowanym forku: W5100** | Ethernet i UART | TFTP + STK500v2 | historyczna architektura; nie użyto sterownika W5100 do W5500 |
| MicroBridge | ATmega2560 | brak bezpośredniej obsługi | BIN z SD do Flash | plik/FAT + STK500v2 | strumieniowanie stron i flaga EEPROM; nie klient sieciowy |

Podany URL `arduino/Ariadne-Bootloader` był niedostępny przy próbie pobrania. Projekt kontynuowano na dostępnych źródłach Athena, następnie sprawdzono [fork per1234](https://github.com/per1234/Ariadne-Bootloader). Nie przypisujemy wszystkim wariantom Ariadne tych samych możliwości. Późniejsze warianty tej rodziny mogą mieć W5500, ale badana rewizja ma ramki SPI W5100. Tabela koryguje założenia wejściowe na podstawie rzeczywiście przeczytanego kodu.

## Rewizje i licencje

| Źródło | Commit | Ustalenie licencji |
|---|---|---|
| [Arduino](https://github.com/arduino/Arduino-stk500v2-bootloader) | 06ebf3701162b7b7c557dd64bc10796507dbada5 | stk500boot.c: Peter Fleury, GPL v2 lub późniejsza; zachowane nazwiska modyfikujących |
| [Athena](https://github.com/embeddedartistry/athena-bootloader) | f2066e49dec5077999283cba0f7d801a0dd942f0 | główny LICENSE LGPL-2.1, ale badane spi.c/net.c/tftp.c mają nagłówki GPL-2.0; nie wolno traktować całości automatycznie jako LGPL |
| [Ariadne fork](https://github.com/per1234/Ariadne-Bootloader) | ce0a5a23d3e8087cbb82be42424f779af0e42fd5 | README i spi.c wskazują GPLv2 |
| [MicroBridge](https://github.com/FleetProbe/MicroBridge-Arduino-ATMega2560) | 1aaff1d4fb30c761da0df71cf404aad10e545a5e | stk500boot.c GPL-2.0-or-later; pff.c/pff.h mają osobne warunki Petit FatFs; nie skopiowano FAT/SD |
| [avrdude](https://github.com/avrdudes/avrdude) | 7a4c9a21eca02ee4fb251d4861c3b1b7732be378 | GPL-2.0-or-later; wyłącznie analiza zgodności, nie jest linkowany do bootloadera |

Źródła pochodne i nowe pliki projektu są udostępnione jako GPL-2.0-or-later; pełny tekst w `LICENSE`, nota pierwotna w `docs/ARDUINO-NOTICE.txt`. `src/command.h` jest własną, minimalną deklaracją stałych protokołu; nie zawiera oryginalnego pliku Atmel. avr-libc/libgcc pochodzą z toolchaina Arduino i podlegają swoim licencjom bibliotecznym/runtime; kompilator nie jest dystrybuowany w ZIP projektu.

## Co wykorzystano

**Arduino:** zbudowano oryginalny stk500boot.c bez edycji źródła (zgodnościowy alias usuniętego przez nowy avr-libc typu `prog_char` oraz zastąpienie przestarzałego `-mno-tablejump` przez `-fno-jump-tables`). Baseline 5778 B. Monitor w bazie ma ostrzeżenia kompilatora dotyczące dawnych wskaźników/const; baseline służy porównaniu, nie instalacji. Produkcyjny serial zachowuje pochodzenie i strukturę protokołu, ale usuwa monitor, wielo-MCU, programowanie lock, stare pętle czasu i błędne adresowanie EEPROM. Sign-on i parametry wyodrębnia `tools/derive_stk.py`; reszta jest udokumentowaną adaptacją dyspozytora/parsera i wspólną bezpieczną implementacją zapisu stron.

**Athena:** przeanalizowano `src/ethernet/spi.c`, `net.c`, `w5500.h`, `tftp.c`, konfigurację EEPROM i `main.c`. Istotna różnica: blok sterowania W5500 po 16-bitowym adresie, osobne bloki rejestrów i buforów, wspólne SPI, reset oraz konieczność odłączenia CS innych urządzeń. Athena ma wiele wariantów MCU/controllerów, GPIO konfigurowalne w runtime, debug i TFTP. Nie skopiowano jej sterownika ani TFTP; nowy driver korzysta z [dokumentacji rejestrów WIZnet](https://docs.wiznet.io/Product/Chip/Ethernet/W5500) i implementuje tylko socket 0, VDM i wymagane operacje.

**Ariadne:** przeanalizowano spi.c, organizację bootloaders/ariadne i README. Oryginalna ścieżka W5100 wysyła opcode SPI przed adresem, czego W5500 nie używa. Użyto wyłącznie wiedzy o podziale serial/network i pamięci; nie kopiowano kodu. Nie przenoszono reset-servera z bibliotek aplikacji.

**MicroBridge:** przeanalizowano warunek EEPROM `0x1FF == 0xF0`, otwarcie firmware.bin, pętlę stron do `0x3E000`, dopełnianie FF i usunięcie flagi. Nowy kod ma niezależny rekord CRC i trwały PENDING aż do weryfikacji. Nie skopiowano FAT/SD ani starego kasowania flagi bez sprawdzenia CRC całego obrazu.

Duże biblioteki i sieciowe mechanizmy referencyjnych projektów nie są linkowane. Rozmiar końcowy obejmuje tylko pliki z `src/` oraz niezbędny runtime AVR.

## Zawartość publikowanego repozytorium

Minimalny, niezmieniony snapshot Arduino jest w `third_party/arduino-stk500v2/`,
z rewizją i SHA256. Katalog roboczy `reference/` nie jest zależnością builda
ani częścią ZIP. Athena, Ariadne, MicroBridge i avrdude nie są dystrybuowane.
Pełne teksty licencji avr-libc 2.0.0 i GCC 7.3.0 Runtime Library Exception
wraz z GPLv3 są w `third_party/licenses/`. Własny kod, testy, narzędzia i
tekst dokumentacji projektu podlegają GPL-2.0-or-later; zachowane materiały
upstream pozostają objęte ich oryginalnymi notami i warunkami.

## Weryfikacja licencji przy publikacji (2026-09-18)

Teksty Arduino, avr-libc i GCC porównano z przypiętymi źródłami upstream;
[SOURCES.json](../third_party/licenses/SOURCES.json) zapisuje URL i SHA256.
Zbiorcze warunki publikacji i zakres licencji: [LICENSES.md](../LICENSES.md).
Dnia 2026-09-23 usunięto z bieżącego drzewa oryginalne command.h i avr_cpunames.h,
ponieważ nie ustalono jednoznacznie ich osobnych warunków licencyjnych.
Zastępują je własne pliki projektu: minimalne wartości protokołu w src/command.h
oraz jedna nazwa MCU w tools/baseline/avr_cpunames.h. Nie przenoszono komentarzy,
tabel nazw procesorów ani nieużywanych definicji z usuniętych nagłówków.
Nie jest to nadanie nowej licencji oryginałom. Niezmieniony GPL-2.0-or-later
stk500boot.c zachowano wraz z notices i SHA256. make official nadal kompiluje
oryginalny plik C, ale korzysta z własnych nagłówków pomocniczych.

Wersja 1.0.0 rozpoczyna nową historię Git zawierającą wyłącznie sprawdzone drzewo.
Usuniętych nagłówków nie ma w tej historii ani w paczce ZIP. Nie zmienia to
wstecznie licencji wcześniej rozpowszechnionych kopii. Szczegóły: LICENSES.md.
