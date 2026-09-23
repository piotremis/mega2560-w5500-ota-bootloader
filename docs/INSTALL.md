# Kompilacja i instalacja — Windows / AVRISP mkII

## 1. Przygotowanie

Potrzebne są Python 3.9+, PowerShell i narzędzia Arduino AVR: `avr-gcc`, avr-libc,
binutils oraz avrdude. Sprawdzony toolchain to
`7.3.0-atmel3.6.1-arduino7`, avrdude `8.0.0-arduino1`.
Skrypty wykrywają instalację w `%LOCALAPPDATA%/Arduino15`.
Nie wymagają GNU make. Własną instalację AVR można wskazać przez `AVR_PREFIX`,
np. `C:/avr/bin/`; inny kompilator może zmienić rozmiar firmware.

Otwórz PowerShell w katalogu projektu. Dla testów Windows pobierz Zig:

```powershell
python -m pip download ziglang==0.13.0 --dest build/tool-download
```

## 2. Kompilacja i testy

```powershell
.\build.ps1
```

Powstają `build/final/bootloader.hex`, `.elf`, `.map` i raporty rozmiaru.
Build przerywa się, jeżeli kod/dane Flash wyjdą poza `0x3E000–0x3FFFF`.
Każde uruchomienie kompiluje źródła ponownie; czyszczenie nie jest wymagane.
Nie uruchamiaj kilku buildów jednocześnie (wspólne pliki tymczasowe LTO).

## 3. Połączenia

AVRISP mkII podłącz do ICSP docelowego Mega: RESET, MOSI, MISO, SCK, GND
oraz VTG do zasilania celu. Zapewnij zasilanie płytki; nie zakładaj, że programator
ją zasila. Pierwsza instalacja i wymiana bootloadera wymagają ISP.
CH340 służy do późniejszego uploadu aplikacji.

| W5500 | Mega2560 |
|---|---|
| CS | **D53 / PB0**, aktywny niski |
| SCK | D52 / PB1 |
| MOSI | D51 / PB2 |
| MISO | D50 / PB3 |
| GND | wspólna masa |

Zasilanie/poziomy logiczne dobierz do modułu W5500. RSTn wymaga poprawnego resetu
sprzętowego; bootloader wykonuje także reset programowy. INT nie jest używany.
CS jest konfigurowalny w [board_pins.h](../src/board_pins.h); sprzętowe SPI ma
stałe piny. Inne urządzenia na SPI muszą mieć nieaktywne CS. Brak obsługi SD.

## 4. Wgranie bootloadera i EEPROM

**Operacja kasuje aplikację i może skasować EEPROM.** Numer seryjny musi być
unikalną liczbą dziesiętną 1–65535. Dla pierwszego urządzenia:

```powershell
.\buildAndProgram.ps1 -SerialNumber 0001
```

Skrypt kolejno:

1. Generuje i waliduje fabryczny IDLE w EEPROM, wykonuje build/testy.
2. Odczytuje sygnaturę celu (ATmega2560: `1E 98 01`).
3. Kasuje Flash i ustawia fuse `LF=FF`, `HF=D8`, `EF=FD` dla Mega 16 MHz/boot 8 KiB.
4. W jednej sesji ISP zapisuje i weryfikuje EEPROM, następnie Flash.
5. Ustawia lock `0F`, ponownie weryfikuje Flash/EEPROM i odczytuje fuse.

Każdy błąd przerywa dalsze kroki. Nie stosujemy `-F` ani wyłączania weryfikacji.
Lock może być odczytany jako `CF` przez nieużywane bity. Ustawienie lock następuje
po poprawnym zapisie, aby chronić Boot Loader Section.

S/N 0001 daje MAC `02:53:49:4F:00:01`. IDLE ma DHCP z fallbackiem
`192.168.1.50/24`, bramą/DNS `192.168.1.1`. Pliki `.eep` i `.json` znajdują się
w `build/provision/0001.*`. Bootloader sam nie tworzy wpisu przy pustym EEPROM.
[Pełny format i zasady recovery](EEPROM.md).

## Przydatne opcje

```powershell
# Build + generowanie EEPROM + podgląd, bez dostępu do sprzętu:
.\buildAndProgram.ps1 -SerialNumber 0001 -DryRun
# Inna brama/DNS i konkretny programator USB:
.\buildAndProgram.ps1 -SerialNumber 0001 -Gateway 192.168.1.254 -Dns 192.168.1.254 -Port 'usb:000200212345'
# Własny interpreter:
.\build.ps1 -Python 'C:\Python313\python.exe'
```

Oba skrypty obsługują `-SkipTests` (kontrola rozmiaru pozostaje).
Programujący ma również `-Avrdude`, `-AvrdudeConfig`, `-BitClock` (domyślnie 10 us).
Jeżeli PowerShell blokuje skrypt, można uruchomić zaufaną lokalną kopię jednorazowo:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1`.

## 5. Aplikacja przez CH340

Odłącz ISP, podłącz USB/UART i zresetuj płytkę. W Arduino IDE wybierz
**Arduino Mega or Mega 2560 / ATmega2560**, port CH340 i zwykłe Upload.
Nie używaj „Wypal bootloader”, bo zastąpi nasz kod wersją standardową.
Parametry avrdude: `-p m2560 -c wiring -b 115200 -D`; maksymalny obraz 253952 B.

Po resecie jest 2-sekundowe okno UART. Upload aplikacji nie kasuje PENDING;
przy recovery najpierw wgraj kompletną aplikację, dopiero potem napraw rekord.
Nie przerywaj zasilania podczas instalacji ISP. Testy OTA/power-loss wykonuj
według [TESTING.md](TESTING.md); poprawny zapis ISP nie dowodzi działania OTA.
