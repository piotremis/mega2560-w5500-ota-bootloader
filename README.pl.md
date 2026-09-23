# Bootloader Mega2560 z Ethernet OTA

**Wersja 1.0.0** · [Historia zmian](CHANGELOG.md)

[English](README.md) · [Instalacja](docs/INSTALL.md) · [Licencje](LICENSES.md)

Bootloader C dla **ATmega2560, 16 MHz**, oparty na Arduino STK500v2.
Obsługuje zwykły upload Arduino przez UART0/CH340 oraz OTA z W5500:
**HTTP GET → BIN → Flash → CRC32 i odczyt kontrolny**.

**Build: 7946 / 8192 B Flash**, zapas 246 B, statyczny SRAM 1205 B.
Zakres bootloadera: `0x3E000–0x3FF09`. Build kontroluje adresy ELF i HEX.
[Szczegółowy raport](docs/SIZE.md).

Kompilacja i testy hostowe przeszły. Obie ścieżki — upload przez UART0/CH340
oraz OTA przez W5500 — przetestowano na sprzęcie 2026-09-22. Działają poprawnie.
Testy utraty zasilania i wymuszonych awarii pozostają niepotwierdzone;
zobacz [zakres testów](docs/TESTING.md). CRC32 nie potwierdza autentyczności firmware.

## Kompilacja — Windows

Wymagane: Python 3.9+ i toolchain Arduino AVR
(sprawdzony `7.3.0-atmel3.6.1-arduino7`). Skrypty wykrywają narzędzia w Arduino15.
GNU make nie jest potrzebny. Jednorazowo pobierz kompilator testów hostowych:

```powershell
python -m pip download ziglang==0.13.0 --dest build/tool-download
```

Następnie, z katalogu projektu:

```powershell
.\build.ps1
```

Wyniki: `build/final/bootloader.hex`, `.elf`, `.map` i raporty rozmiaru.
Możesz wskazać interpreter przez `-Python C:\sciezka\python.exe`.
`-SkipTests` pomija testy hostowe, ale nie kontrolę rozmiaru.

## Wgrywanie — AVRISP mkII USB

Podłącz ICSP i zasilanie docelowego Mega2560. Ta operacja **kasuje aplikację
oraz może skasować EEPROM**. Podaj unikalny numer seryjny:

```powershell
.\buildAndProgram.ps1 -SerialNumber 0001
```

Skrypt wykonuje build/testy, sprawdza sygnaturę, ustawia fuse, zapisuje i
weryfikuje EEPROM oraz Flash, po czym ustawia ochronę sekcji boot.
Błąd przerywa procedurę. Podgląd bez dostępu do sprzętu:

```powershell
.\buildAndProgram.ps1 -SerialNumber 0001 -DryRun
```

S/N `0001` → MAC `02:53:49:4F:00:01`; `0002` → `02:53:49:4F:00:02`.
Zakres S/N: 1–65535, zapis dziesiętny. Powstaje rekord **IDLE**, DHCP z fallbackiem
**192.168.1.50/24**, bramą i DNS **192.168.1.1**. Bramę/DNS można zmienić
parametrami `-Gateway` i `-Dns`. Pliki jednostki: `build/provision/`.
Wspólny adres fallback .50 nie może być używany równocześnie przez kilka urządzeń
w jednej podsieci. [Połączenia, fuse i wskazówki](docs/INSTALL.md).

Aplikację wgrywaj potem przez CH340, wybierając standardowe **Arduino Mega 2560**.
Wymiana bootloadera wymaga ISP. W5500 CS: **D53**, SPI D52/D51/D50.

## Konfiguracja i OTA

Jeden rekord EEPROM **160 B od 0x0F60**, format v1, zawiera S/N, MAC, sieć i
metadane OTA ze wspólnym CRC. Bootloader nie tworzy pustego rekordu i nie
migruje starego układu. Tryby: **0 DHCP**, **1 DHCP + fallback**, **2 stałe IP**.
URL z IPv4 pomija DNS; nazwa hosta wymaga DNS A.

Aplikacja zachowuje dane jednostki, zapisuje URL/rozmiar/CRC/wersję,
zatwierdza PENDING i resetuje MCU. Bootloader pobiera BIN, zapisuje strony
256 B i sprawdza CRC pobierania oraz Flash. Błąd pozostawia PENDING do ponowienia.
Brak poprawnego wpisu wyłącza OTA; PENDING/ARMING blokują uruchomienie częściowego
obrazu. Nie ma HTTPS, podpisów, rollbacku, SD, serwera HTTP ani self-update.

- [EEPROM i API aplikacji](docs/EEPROM.md)
- [Protokół OTA](docs/OTA.md)
- [Komendy STK500v2](docs/STK500.md)
- [Testy i ograniczenia](docs/TESTING.md)
- [Rozmiar pamięci](docs/SIZE.md)
- [Przygotowanie wydania](docs/RELEASING.md)
- [Źródła referencyjne](docs/THIRD_PARTY.md)

Kod: `src/`; API aplikacji: `application/`; narzędzia: `tools/`; testy: `tests/`;
źródła bazowe i noty: `third_party/`. Katalogi `build/` i `dist/` są generowane.
Projekt własny/pochodny: **GPL-2.0-or-later**. [Tekst licencji](LICENSE),
[warunki i pochodzenie komponentów](LICENSES.md).
