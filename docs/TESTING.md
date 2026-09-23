# Walidacja i ograniczenia dowodów

## Wykonano

| Warstwa | Wynik / dowód |
|---|---|
| verified by compilation | AVR-GCC 7.3.0, ATmega2560/16 MHz, GNU make; finalne źródła z `-Wall -Wextra -Werror`; ELF, HEX, MAP i raporty |
| verified by static analysis | przegląd zakresów SPM, 32-bitowego adresowania, stanu PENDING i parserów; disassembly i ELF/LMA; nie jest to formalny dowód ani wynik komercyjnego analizatora |
| simulated/tested | produkcyjny kod C kompilowany na hosta, podstawione wyłącznie I/O; testy CRC, URL, HTTP, DNS, DHCP, EEPROM, Flash, OTA i STK |
| protocol integration | prawdziwy avrdude 8.0-arduino.1, backend wiring, zapis+odczyt+verify 248 KiB Flash i 4 KiB EEPROM przez hostową implementację transportu UART/TCP |
| driver model | produkcyjny w5500.c z modelem SPI/rejestrów/socket/ring-buffer; timeouty, MAC, UDP header, zawijanie |
| hardware tested | Upload przez UART0/CH340 i OTA przez W5500 przetestowano na docelowym sprzęcie 2026-09-22 — obie ścieżki działają poprawnie. Wcześniej starszą rewizję 8122 B zapisano przez AVRISP mkII oraz zweryfikowano Flash i fuse/lock. |

Testy nie wykonują ELF w emulatorze instrukcji AVR. Nie zastępują pomiaru SPI, rzeczywistego SPM, zegara, CH340, auto-resetu, PHY/linku ani brown-out. Sukces kompilacji nie jest uznany za sukces na sprzęcie.

Sprawdzono również dostarczane archiwum: rozpakowano ZIP do nowego katalogu, wykonano ponowny build AVR i otrzymano identyczny bajtowo HEX. Log: `build/tests/release.txt`. Archiwum zawiera manifest SHA256 wszystkich dołączonych plików; ZIP CRC i SHA256 zweryfikowano po utworzeniu. Pobierane kompilatory, cache i zagnieżdżone katalogi `.git` są wyłączone z paczki.

## Software

Regresje publikacyjne: linkowanie API C z programem C++ (także cfg_load/CRC),
zgodność walidacji URL generatora i API, odrzucenie portu 0/niepoprawnego IPv4
przed jakimkolwiek zapisem EEPROM oraz zachowanie poprawnego URL bez zmian.
CI buduje AVR-GCC 7.3.0, kontroluje limit Flash i przebudowuje ZIP.

Na Linuxie model hosta jest linkowany z `-Wl,-Bsymbolic`, aby jego wewnętrzne
wywołania `crc32(data, size)` nie trafiły do eksportowanej przez zlib funkcji
o tej samej nazwie i innym ABI. Testy celowo udostępniają symbole zlib globalnie,
aby sprawdzać tę kolizję. Flaga dotyczy wyłącznie biblioteki testowej, nie AVR.
Zobacz [opis opcji GNU ld](https://sourceware.org/binutils/docs/ld/Options.html).
CI uruchamia Python z `-X faulthandler` i pokazuje częściowy log po awarii.

`make test` uruchamia:

- `tests/run.py`: 27 grup unittest rzeczywistych funkcji C, ponad 2000 deterministycznych pakietów fuzz, wszystkie ucięcia odpowiedzi DHCP/DNS, CRC32 kontra zlib, parser portu/URL, nagłówki i overflow Content-Length, pola/CRC EEPROM, 256 wartości stanu startowego, przerwanie każdego zapisu EEPROM przy przygotowaniu żądania z rekordu pustego oraz IDLE, zakresy Flash, STK komendy, checksum/token/length/sequence ramek, `!!!` bez monitora. Testy sprawdzają brak zapisów przy pustym/uszkodzonym EEPROM, ochronę PENDING/ARMING, fabryczny IDLE, mapowanie S/N na MAC, odrzucenie niepoprawnego S/N oraz zachowanie tożsamości przy żądaniu OTA.
- Pełny łańcuch DHCP → DNS → HTTP → Flash → CRC na modelu: obrazy 1/255/256/257/700/253952 B, TCP podzielony na 17-bajtowe fragmenty, błędny CRC, błędny readback, przerwanie po 2 stronach i ponowienie, 404, brak/duplikat/rozbieżny Content-Length, chunked, ucięcie body, brak DHCP/DNS.
- `tests/w5500.py`: model rejestrów, MAC z argumentu, UDP 68, TCP connect, odczyt datagramu, RX/TX na granicach 2048 i 65536, odrzucanie za dużego datagramu, timeout SEND i wiszącej komendy. Sprawdza CS jako aktywne-niskie wyjście podczas każdego bajtu SPI, sprzętowy SS jako wyjście oraz stany GPIO po transakcji. Warianty: domyślny D53 i CS na innym porcie; pozostałe bity portu pozostają bez zmian.
- `tests/link_limit.py`: celowo zbyt duże `.text` oraz inicjalizatory `.data`; linker musi zwrócić błąd, co potwierdza, że sprawdzany jest też Flash używany przez dane RAM.

`python tests/avrdude.py` jest osobnym testem integracyjnym Windows/Arduino15. Pełny trace i stdout są w `build/tests`. Nie korzysta z portu COM i nie zmienia urządzenia. W repo zawarto testy/źródła modelu; kompilator hostowy jest zależnością zewnętrzną, nie częścią firmware.

## SRAM i stos

Statyczny SRAM finalnego ELF: 1205 B = `.data` 160 B + `.bss` 1045 B. Największe bufory: wspólny pakiet 600 B, strona Flash/linia HTTP 256 B, Config 160 B. URL jest częścią Config. Bufory 2 KiB W5500 są pamięcią kontrolera i nie wchodzą do 1205 B. Brak malloc, VLA, rekursji i przerwań w bootloaderze.

Pozostaje 6987 B **przed stosem**. GCC 7 z LTO emituje rzeczywiste ramki dopiero do `build/final/bootloader.elf.ltrans0.ltrans.su` (źródłowe `.su` są puste). Ramki zmieniają się z optymalizacją LTO; plik .su nie daje samodzielnie maksimum całego stosu. Budżet 512 B na stos daje duży zapas (6475 B pozostałego SRAM), ale **nie jest pomiarem high-water mark ani formalnie wyznaczonym maksimum stosu**. Zmierz watermark w wariancie diagnostycznym na sprzęcie przed wdrożeniem. Brak przerwań usuwa nieprzewidywalny narzut ISR.

## Hardware acceptance — dla bieżącej rewizji

**Przetestowano na sprzęcie 2026-09-22:** upload przez UART0/CH340 oraz OTA przez
W5500. Obie ścieżki działają poprawnie. Testy utraty zasilania, wymuszonych błędów
i wartości granicznych pozostają do wykonania w ramach poniższej listy.

| Test | Kryterium zaliczenia |
|---|---|
| ISP / fuse / lock | ELF/HEX tylko w boot; odczyt HFUSE D8, poprawny zegar i lock; start pod 0x3E000 |
| Arduino IDE → CH340 | auto-reset, sign-on, upload małego i >128 KiB szkicu, poprawne verify i start aplikacji |
| EEPROM przez UART | zapis/odczyt niskich i wysokich adresów, zachowanie rezerwacji |
| W5500 na SPI | CS D53 (PB0), SS D53 jako output, VERSIONR=4, poprawne przebiegi SPI |
| normalne OTA | DHCP DISCOVER/OFFER/REQUEST/ACK, DNS A, HTTP GET, CRC pobrania/readback, IDLE i start |
| reset podczas OTA | reset w każdej fazie oraz w 1./środkowej/ostatniej stronie; PENDING i pobranie od 0 |
| power loss | wielokrotne odcięcie VCC podczas EEPROM commit, SPM i weryfikacji; nigdy start częściowej aplikacji |
| błędny CRC/readback | LED błędu, PENDING, brak skoku do aplikacji |
| firmware >253952 B | odrzucenie przed programowaniem; boot niezmieniony |
| firmware dokładnie 253952 B | 992 strony, ostatnia pod 0x3DF00, poprawny CRC i brak zmian w boot |
| DNS niedostępny | timeout/retry, brak startu częściowej aplikacji, możliwość UART recovery |
| serwer HTTP niedostępny / link down | timeout/retry i zachowanie PENDING |
| HTTP 404 / brak Content-Length | błąd przed pierwszym SPM |
| niepełne body | błąd, ponowienie, PENDING |
| długi transfer i wrap W5500 | poprawne >64 KiB oraz wielokrotne zawinięcie TX/RX |
| stos/zasilanie | watermark SRAM, VCC/BOD/supervisor, brak niekontrolowanego działania podczas spadku zasilania |
| boot protection | odczyt boot przez ISP i porównanie checksum przed/po testach, w tym złośliwych adresach UART |

Do każdego testu sprzętowego zapisz model płytki/W5500, fuse, napięcie, toolchain i hash HEX, log avrdude, log serwera/pcap oraz wynik. Dopiero po tych testach można oznaczyć wydanie jako zwalidowane sprzętowo.

Testy IPv4 obejmują oktety graniczne, niepoprawne liczby i liczbę oktetów, dziesiętne zera wiodące oraz brak pakietów DNS. Pełne OTA po IP przechodzi przy braku odpowiedzi DNS, z portem 80 i 8080; sprawdzane są adres TCP, port i Host header. Nazwa 123.example.com nadal generuje DNS.

Testy sieci statycznej: wymuszenie bez pakietów DHCP, fallback po timeout DHCP, preferencja poprawnego DHCP, DNS z konfiguracji statycznej, jednoczesny brak DHCP/DNS dla URL z IP, CRC wszystkich nowych pól oraz odrzucenie nieznanego trybu.
