# HTTP OTA v1

Bootloader działa wyłącznie na żądanie aplikacji. Nie wyszukuje aktualizacji, nie porównuje wersji i nie udostępnia endpointu. Przepływ: UART window → poprawny EEPROM PENDING → reset/init W5500 → DHCP lub konfiguracja statyczna → IPv4 bez DNS / DNS A dla nazwy → TCP → HTTP/1.0 GET → strony Flash → CRC pobrania → CRC readback → IDLE → aplikacja.

## Sieć

Jeden socket W5500, numer 0, używany kolejno jako UDP DHCP, UDP DNS i TCP HTTP. Domyślne 2 KiB RX/TX znajdują się **w W5500**, nie w SRAM AVR. Pozostałe sockety są zamknięte. Nie implementujemy TCP/IP programowo. DNS nie jest rejestrem W5500 — adres serwera znajduje się w 4-bajtowej zmiennej AVR.

DHCP: klient UDP 68, broadcast do 67; DISCOVER/OFFER i REQUEST/ACK, weryfikacja BOOTP, xid, MAC, cookie, długości opcji i server identifier. ACK musi zawierać maskę, router i DNS, zgodny server-id i oferowany adres. Brak wymaganych opcji kończy próbę błędem. Trzy próby każdej fazy, po 2 s na odpowiedź. NAK jest odrzucany; nowa próba pełnego OTA zaczyna nowy DISCOVER. Brak renew/rebind, DHCP option overload, przechowywania lease i detekcji konfliktów ARP.

DNS: UDP do pierwszego DNS z DHCP, port 53, trzy próby po 2 s. QTYPE A, QCLASS IN, jedna nazwa, weryfikowane źródło/port/id/question/flags, nazwa właściciela odpowiedzi i długości. Obsługiwane wskaźniki kompresji nazw z limitem liczby kroków; cykle i ucięte dane są odrzucane. Nie obsługuje CNAME chain, AAAA, DNSSEC, EDNS ani przejścia DNS na TCP. Odpowiedź DNS ma zmieścić się w 600 B (klasyczny DNS bez EDNS do 512 B).

URL: `http://HOST[:PORT]/PATH`, do 100 B w EEPROM; port 1..65535, domyślnie 80. ASCII, bez spacji/CR/LF/fragmentu `#`, userinfo i IPv6. HOST to nazwa DNS z etykietami do 63 znaków albo adres IPv4, np. `http://192.168.1.20:8080/fw.bin`. IPv4 wymaga dokładnie czterech oktetów 0..255 (1..3 cyfry każdy); zera wiodące są dziesiętne, nie ósemkowe. Host złożony tylko z cyfr i kropek jest traktowany jako adres liczbowy; błędny format kończy próbę bez zapytania DNS. Dla poprawnego IPv4 resolver nie otwiera socketu DNS ani nie wysyła zapytań. Nazwy takie jak `123.example.com` nadal używają DNS. W trybie DHCP klient oczekuje opcji DNS w ACK, ale dostępność serwera DNS nie jest potrzebna dla URL z IP. Tryb 1 umożliwia fallback na konfigurację statyczną po błędzie DHCP, a tryb 2 pomija DHCP całkowicie. Wszystkie dane sieciowe są częścią jednego rekordu OTA w EEPROM. Root `/` i query string są obsługiwane; kod nie wykonuje percent-encoding, więc URL musi być już zakodowany przez backend.

## HTTP

```http
GET /firmware/mega.bin HTTP/1.0
Host: example.com:8080
Connection: close

```

Na przewodzie każda linia ma CRLF. Serwer odpowiada HTTP/1.0 lub HTTP/1.1 ze statusem 200 i **dokładnie jednym** Content-Length równym EEPROM image_size, większym od 0 i nie większym od 253952. Nazwy nagłówków są case-insensitive. Obsługiwane końcowe CRLFCRLF. Limit nagłówków 2048 B łącznie, linii 255 B. Nadmiarowe/długie nagłówki powodują błąd. Każdy Transfer-Encoding lub Content-Encoding jest odrzucany. Brak TLS, redirectów, chunked, gzip, auth, POST, cookies i JSON w bootloaderze. Nieznane zwykłe nagłówki są pomijane.

Timeout połączenia TCP 3 s, bezczynności odbioru 3 s, operacji SEND 3 s; komendy W5500 mają ograniczony czas oczekiwania. Nie ma absolutnego deadline całej aktualizacji — powolny serwer dostarczający regularnie dane może wydłużyć próbę. Reset/DTR zawsze otwiera ponownie okno UART.

## Flash i recovery

Body odbierane w buforze 600 B, następnie uzupełnia stronę 256 B. Każda strona jest kasowana i zapisywana z przerwaniami wyłączonymi. Ostatnia niepełna strona dopełniana `0xFF`. Strony po końcu obrazu nie są kasowane; nie są częścią CRC ani nowego firmware. Wszystkie adresy SPM przechodzą wspólny zakres `0 <= address`, `address+256 <= 0x3E000` i kontrolę wyrównania. Ochrona dotyczy również STK500v2. Lock bits zapewniają dodatkową blokadę sekcji boot.

CRC32 jest liczone z dokładnie image_size bajtów body. Następnie bootloader czyta dokładnie ten zakres Flash i ponownie liczy CRC32. Przy błędzie HTTP, timeout, niezgodnym rozmiarze, CRC lub SPM nie usuwa PENDING i nie skacze do aplikacji. LED D13 zostaje zaświecona, następuje kolejne okno UART i ponowienie pełnego OTA. Po restarcie pobieranie zawsze zaczyna się od bajtu 0, bez Range/resume.

Po odebraniu Content-Length dodatkowe bajty po body nie należą do obrazu; połączenie jest zamykane. Content-Length i CRC stanowią kontrakt pliku. Backend powinien serwować niezmienny zasób na czas całego procesu, bez dynamicznej kompresji, redirectów i CDN wymagającego HTTPS. W pliku BIN nie ma nagłówka firmowego ani Intel HEX.

**CRC32 nie jest mechanizmem autentyczności.** HTTP i metadane mogą zostać zmodyfikowane przez aktywnego przeciwnika. Ten etap nie zapewnia podpisów ani TLS. Recovery nie jest rollbackiem: podczas zapisu poprzednia aplikacja zostaje zniszczona; bez sprawnego serwera urządzenie pozostaje w recovery i można je naprawić przez UART/ISP.
