# EEPROM ABI v1

Rezerwacja `0x0F60–0x0FFF` (3936–4095), dokładnie 160 B. Pierwsze 3936 B pozostaje aplikacji. Całkowite zapisy EEPROM z avrdude nadal są obsługiwane i mogą zmienić ten rekord; aplikacja musi respektować rezerwację.

| Offset w rekordzie | Rozmiar | Pole |
|---:|---:|---|
| 0 | 2 | magic `0x4F54`, w EEPROM `54 4F` |
| 2 | 1 | format=1 |
| 3 | 1 | state: `00` IDLE, `A5` PENDING, `5A` ARMING |
| 4 | 4 | image_size, 1..253952 dla OTA, 0 dla fabrycznego IDLE |
| 8 | 4 | expected image CRC32 |
| 12 | 4 | requested version uint32, bez polityki no-downgrade |
| 16 | 6 | MAC, unicast, niezerowy |
| 22 | 1 | url_len, 9..100 dla OTA, 0 dla fabrycznego IDLE |
| 23 | 101 | URL ASCII i końcowy NUL; reszta wyzerowana przez aplikację |
| 124 | 1 | network_mode: 0 DHCP, 1 DHCP + fallback, 2 stałe IP |
| 125 | 4 | IP urządzenia, oktety w kolejności sieciowej |
| 129 | 4 | maska podsieci |
| 133 | 4 | gateway (0.0.0.0 dopuszczalne dla serwera w tej samej podsieci) |
| 137 | 4 | DNS (0.0.0.0 dopuszczalne dla URL z IPv4) |
| 141 | 2 | serial_number, uint16 little-endian, 1..65535 podczas provisioningu |
| 143 | 13 | zarezerwowane, zerować |
| 156 | 4 | record CRC32 z bajtów 4..155 włącznie |

Wszystkie liczby wielobajtowe little-endian, struktura packed, asercja rozmiaru w C/C++. CRC32: IEEE reflected, polynom `0xEDB88320`, init `0xFFFFFFFF`, końcowy XOR `0xFFFFFFFF`; wektor `123456789` daje `CBF43926`. Magic, stały format i stan są sprawdzane osobno. Stan nie wchodzi do CRC, dzięki czemu wyzerowanie stanu po sukcesie nie unieważnia rekordu.

## Brak rekordu i fabryczny IDLE

Podczas startu bootloader tylko odczytuje rekord. Nie tworzy ani nie naprawia danych EEPROM.
Pusty lub niepoprawny rekord wyłącza OTA, ale pozwala uruchomić obecną aplikację
po oknie UART. Wyjątek: bajt stanu PENDING/ARMING blokuje start nawet przy złym
CRC/magic, ponieważ Flash może zawierać niekompletny obraz. Nieznany stan w
poprawnym rekordzie również blokuje start. Zwykły reset nie zapisuje EEPROM.

Fabryczny rekord IDLE tworzy skrypt na PC. Ma ważne magic/format/CRC, S/N, MAC
oraz sieć; URL, image_size, image_crc i requested version są zerowe. Taki rekord
nie jest żądaniem OTA. Przy zmianie samego stanu na PENDING walidacja odrzuci go,
ponieważ brakuje metadanych obrazu. Poprawny IDLE po aktualizacji może nadal
zawierać ostatnie metadane firmware.

Ograniczenie pojedynczego rekordu: uszkodzenie stanu PENDING/ARMING do innej
wartości wraz z uszkodzeniem metadanych może uniemożliwić rozpoznanie przerwanej
aktualizacji. Normalna utrata zasilania podczas pobierania nie zmienia rekordu.

## Transakcyjne żądanie z aplikacji

Implementacja: `application/ota_request.c`. Najpierw aplikacja odczytuje poprawny rekord przez cfg_load(), zachowuje MAC, S/N i konfigurację sieci, a następnie uzupełnia URL, długość, image_size, expected CRC i version. Aplikacja wpisuje również network_mode oraz ip/mask/gateway/dns; zerowy tryb oznacza samo DHCP. Funkcja uzupełnia format/magic/CRC, sprawdza rekord i składnię URL przed zapisem EEPROM oraz odmawia zastąpienia istniejącego PENDING/ARMING. Parser URL jest współdzielony z bootloaderem; API dodatkowo sprawdza numeryczny IPv4 i zgodność url_len z długością tekstu. Zapis:

1. Stan ARMING, aby reset podczas przygotowania prowadził do bezpiecznego zatrzymania.
2. Unieważnienie obu bajtów magic.
3. Payload 4..155 (wraz z URL i metadanymi), następnie CRC 156..159.
4. Format, oba bajty magic.
5. **PENDING jako ostatni zapis**, oczekiwanie na ukończenie EEPROM.
6. Aplikacja włącza watchdog i czeka na reset.

Po restarcie tylko poprawny rekord PENDING uruchamia OTA. ARMING albo uszkodzony rekord ze stanem PENDING zatrzymuje start aplikacji i pozostawia UART recovery. Przygotowanie żądania przerwane przed końcowym commit wymaga naprawienia rekordu przez UART/ISP. Po zaakceptowanym PENDING bootloader nie zmienia metadanych ani stanu aż do dwóch poprawnych CRC obrazu.

Po sukcesie zmieniany jest wyłącznie bajt stanu na IDLE. Power loss przed tą operacją ponawia OTA. Power loss podczas tej operacji może pozostawić PENDING/IDLE albo niepoprawny stan; aplikacja została już wtedy zweryfikowana. Bootloader nie naprawia nieznanego stanu; zasady startu opisano powyżej. ARMING nadal wymaga recovery. Nie ma A/B ani rollbacku.

Przykład bare-metal C, po odebraniu metadanych przez aplikację:

```c
#include "ota_request.h"
#include <avr/interrupt.h>
#include <avr/wdt.h>

Config request;
if (!cfg_load()) { /* brak poprawnego provisioningu: przerwij */ return; }
request = cfg; /* zachowaj MAC, S/N oraz konfigurację sieci */
/* wpisz URL, strlen(URL), image_size, image_crc, version */
if (ota_request(&request)) {
    cli();
    wdt_enable(WDTO_15MS);
    for (;;) {}
}
```

Do aplikacji linkuj `application/ota_request.c`, `application/avr_eeprom.c`, `src/crc32.c`, `src/eeprom_cfg.c`; nie linkuj `main.c` ani `platform.c` bootloadera. Nagłówek jest dostępny także przez `extern "C"` z C++. Pliki C muszą pozostać jednostkami C (np. w lokalnej bibliotece Arduino). Interfejs nie implementuje panelu administratora: aplikacja/backend decydują o aktualizacji.

## Generator metadanych dla backendu / ISP

```sh
avr-objcopy -O binary -R .eeprom application.elf firmware.bin
python tools/eeprom.py firmware.bin --url http://example.com:8080/firmware.bin --mac 02:01:02:03:04:05 --version 42 --out build/request.eep
```

MAC w przykładzie jest wartością demonstracyjną; nadaj urządzeniu unikalny adres. Narzędzie generuje plik Intel HEX **EEPROM**, nie firmware OTA, i JSON z rozmiarem/CRC/version/URL. BIN musi zaczynać się od adresu aplikacji 0, nie zawierać bootloadera. Wydziel `.eeprom` z konwersji ELF. Jeżeli ELF nie ma żadnych danych pod adresem 0, nie jest poprawnym obrazem startowym.

`request.eep` wolno instalować przy kontrolowanym zasilaniu i trzymaniu AVR w resecie przez ISP. Zwykłe wgranie gotowego pliku EEPROM nie gwarantuje kolejności transakcyjnej — produkcyjna aplikacja używa `ota_request()`. Nie resetuj urządzenia w połowie zewnętrznego provisioningu. Do odzyskania uszkodzonego rekordu należy zapisać kompletny poprawny rekord lub świadomie wyczyścić go dopiero po odbudowie aplikacji.

CRC konfiguracji chroni przed przypadkowym uszkodzeniem, nie przed celową modyfikacją. Jednorekordowy format nie obiecuje zachowania starego żądania przy przerwanym zastępowaniu; zastępowanie PENDING jest zabronione przez API.

## Tryby sieciowe w jednym rekordzie

Format pozostaje **v1**, jest nadal rozwijany. Obecny układ ma 160 B od 0x0F60;
wcześniejszego układu deweloperskiego 128 B nie odczytujemy ani nie migrujemy.
Przy instalacji usuń stary rekord i użyj aktualnej aplikacji/generatora.

- `NETWORK_DHCP = 0`: tylko DHCP, błąd DHCP przerywa próbę OTA.
- `NETWORK_FALLBACK = 1`: najpierw DHCP; po błędzie statyczne dane z tego rekordu.
- `NETWORK_STATIC = 2`: od razu dane statyczne, bez wysyłania DHCP.

Wszystkie pola sieciowe są objęte tym samym CRC co URL/metadane. Nie ma osobnego
wpisu ani osobnego zatwierdzania. Po udanej OTA dane pozostają, zmienia się stan.
Aplikacja musi ponownie wpisać lub skopiować konfigurację do każdego nowego
żądania; wyzerowanie struktury i pozostawienie network_mode=0 wybiera DHCP.
Pusty EEPROM nie jest zmieniany przez bootloader; brak rekordu wyłącza OTA.

Przykład pól aplikacji (przed ota_request):

```c
request.network_mode = NETWORK_STATIC; /* albo NETWORK_FALLBACK */
memcpy(request.ip,      (uint8_t[]){192,168,1,50}, 4);
memcpy(request.mask,    (uint8_t[]){255,255,255,0}, 4);
memcpy(request.gateway, (uint8_t[]){192,168,1,1}, 4);
memcpy(request.dns,     (uint8_t[]){192,168,1,1}, 4);
```

Adres urządzenia musi być unikalny/zarezerwowany, maska i brama dobrane do sieci.
Bootloader sprawdza CRC i numer trybu; nie wykrywa konfliktów IP ani błędów
administracyjnych w topologii. FQDN wymaga dostępnego statycznego DNS; URL z IP
nie potrzebuje DNS. Przy braku DHCP fallback czeka na zakończenie prób klienta.

```sh
python tools/eeprom.py firmware.bin --url http://192.168.1.10/fw.bin --mac 02:01:02:03:04:05 --version 42 --network static --ip 192.168.1.50 --mask 255.255.255.0 --gateway 192.168.1.1 --out build/request.eep
```

Zamień `--network static` na `--network fallback`, aby próbować najpierw DHCP.
Dla nazwy serwera podaj też `--dns 192.168.1.1`. Generator tworzy cały rekord
PENDING, nie osobną konfigurację sieci; zapis przez ISP wykonuj przy zatrzymanym
MCU. W działającej aplikacji używaj transakcyjnego `ota_request()`.

## Provisioning przy instalacji bootloadera

```powershell
.\buildAndProgram.ps1 -SerialNumber 0001
.\buildAndProgram.ps1 -SerialNumber 0002
# Tylko build, wygenerowanie EEPROM i pokazanie komend, bez dostępu do urządzenia:
.\buildAndProgram.ps1 -SerialNumber 0001 -DryRun
```

S/N to liczba dziesiętna 1..65535, prezentowana z minimum czterema cyframi.
MAC jest lokalny/unicast: prefiks 02:53:49:4F, ostatnie dwa oktety to S/N
w kolejności big-endian. Pole serial_number w rekordzie jest little-endian.

| S/N | MAC |
|---|---|
| 0001 | 02:53:49:4F:00:01 |
| 0002 | 02:53:49:4F:00:02 |
| 0256 | 02:53:49:4F:01:00 |

Rekord IDLE ma network_mode=1: DHCP, następnie fallback 192.168.1.50/24.
Domyślna brama i DNS to 192.168.1.1; parametry `-Gateway` i `-Dns` pozwalają je
zmienić. Pliki są w `build/provision/0001.eep` i `.json`. Skrypt wymaga S/N,
waliduje dane przed kontaktem z programatorem i zapisuje EEPROM oraz Flash
w jednej sesji ISP, przed ustawieniem lock bitów. Oba zapisy są weryfikowane.

Numery seryjne muszą być unikalne, aby MAC się nie powtarzał. Wszystkie urządzenia
mają ten sam domyślny fallback .50; bez DHCP nie mogą jednocześnie korzystać z
niego w tej samej podsieci. S/N nie zmienia automatycznie fallback IP.

Sam generator (nie zapisuje sprzętu):

```sh
python tools/provision.py --serial-number 0001 --out build/provision/0001.eep
```

`tools/eeprom.py` nadal generuje żądanie PENDING z obrazem; opcjonalne
`--serial-number` pozwala zachować tożsamość. Do fabrycznego IDLE służy wyłącznie
`tools/provision.py`. Format pozostaje v1 i ma 160 B od 0x0F60.
