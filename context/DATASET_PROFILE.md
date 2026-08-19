# Profil aktualnego zbioru danych

Stan na: 2026-08-19.

## Plik

```text
data/history.csv
```

Plik został dostarczony lokalnie jako `history(1).csv`, a następnie otrzymał
kanoniczną nazwę `history.csv`, zgodną z poleceniami, dokumentacją i kontraktem
projektu.

## Profil jakości

- Wiersze: 286782.
- Kolumny: `entity_id`, `state`, `last_changed`.
- Encje: 30.
- Zakres czasu: 2026-08-17 22:00:00 UTC - 2026-08-19 12:58:31.023 UTC.
- Niepoprawne znaczniki czasu: 0.
- Dokładne duplikaty wierszy: 0.
- Duplikaty klucza `entity_id,last_changed`: 0.
- Stany nienumeryczne: 240, w tym 210 `unavailable` i 30 `unknown`.

Wartości nienumeryczne występują po 8 razy dla każdej z 30 encji. Model
konwertuje je na braki i nie używa jako obserwacji liczbowych.

## Porównanie z poprzednim `history.csv`

- Wspólne klucze `entity_id,last_changed`: 149518.
- Wspólne klucze z identycznym `state`: 149518.
- Wspólne klucze ze zmienionym `state`: 0.
- Nowe klucze: 137264.
- Klucze występujące tylko w starej wersji: 17228.

Stare wyłączne rekordy należały do 13 wcześniej zapisanych sensorów `Q`, `S`,
margin i diagnostycznych błędów bilansu. Aktualny plik ich nie zawiera, co jest
zgodne z przeznaczeniem bazowego generatora i zmniejsza ryzyko przypadkowego
użycia hipotez `Q/S` jako danych treningowych.

## Wynik synchronizacji i klasyfikacji

- Kompletne chwile po synchronizacji do 5 sekund: 15294.
- Surowe `grid_on_import`: 1129.
- Surowe `grid_on_export`: 3620.
- Surowe `grid_on_idle`: 10545.
- Surowe `grid_off`: 0.
- Stabilne `grid_on_import`: 294.
- Stabilne `grid_on_export`: 1458.
- Stabilne `grid_on_idle`: 6871.
- Odrzucone lub przejściowe: 6671.
- Wykryte gwałtowne zmiany wielosensorowe: 1851.

Minimalne napięcie fazowe Grid wynosi 216,1 V, a maksymalne 243,0 V. Nie ma
podstaw do trenowania fizycznego `grid_off`.

## Ocena

Zbiór jest odpowiedni do ponownego treningu bazowego generatora stabilnych
stanów. Rozszerza poprzednie dane bez zmieniania wspólnych wartości i nie
wprowadza duplikatów. Nie dostarcza danych interwencji czajnikowej ani fizycznego
`grid_off`.
