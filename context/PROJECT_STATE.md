# Stan projektu

Stan na: 2026-08-19.

## Cel

Projekt buduje generator stabilnych stanów falownika Deye. Generator ma tworzyć
realistyczne wektory obserwowalnych rejestrów i służyć jako wirtualne stanowisko
do późniejszego badania niezależnych funkcji `Qid=F(X)`.

Model bazowy nie zna i nie generuje referencyjnych wartości `Q` ani `S`.

## Zaimplementowane

- Wielowymiarowy generator VAR(1) z bootstrapem całych wektorów reszt.
- Trening na jednym lub wielu zwykłych plikach CSV.
- Zapis modelu do zaufanego pliku pickle i generowanie bez ponownego czytania CSV.
- Minimum 100 generowanych próbek dla każdego żądanego trybu.
- Łączenie trybów, na przykład import i eksport daje po 100 próbek na tryb.
- Ukryte użycie `pv_power` i `battery_power` do segmentacji bez ich publikowania.
- Wykluczenie sensorów diagnostycznych oraz hipotez `Q` i `S` z wyjścia.
- Klasyfikacja `grid_on_import`, `grid_on_export`, `grid_on_idle` i `grid_off`.
- Automatyczna detekcja stabilności na podstawie wielosensorowego wyniku zmian.
- Wymaganie potwierdzonego zaniku zmian zamiast stałego czasu odcięcia.
- Bootstrap empirycznego, wspólnego rozkładu błędów `Pl-Pg-Pi` i błędów sum.
- Automatyczne oddzielenie plików `czajnik*.csv` od treningu modelu bazowego.
- Bezpieczny interfejs `apply_active_load`, który odmawia tworzenia sztucznej
  reakcji do czasu wyuczenia modelu na rzeczywistych parach interwencyjnych.

## Zweryfikowane dane bazowe

Plik `data/history.csv` ma format długi: `entity_id`, `state`, `last_changed`.
W ostatniej walidacji zawierał 30 encji i 286782 wiersze, z których po
synchronizacji powstały 15294 kompletne chwile pomiarowe. Zakres danych wynosi
od 2026-08-17 22:00:00 UTC do 2026-08-19 12:58:31.023 UTC. Dane obejmują
fizycznie połączoną sieć. Nie zawierają potwierdzonego `grid_off`.

Po odrzuceniu przejść model został wytrenowany na:

- 294 stabilnych próbkach `grid_on_import`,
- 1458 stabilnych próbkach `grid_on_export`,
- 6871 stabilnych próbkach `grid_on_idle`.

Szczegółowe porównanie z poprzednią wersją znajduje się w `DATASET_PROFILE.md`.

Dokładne, aktualne liczby po każdym treningu należy odczytać poleceniem:

```powershell
deye-model inspect --model models\deye_simulator.pkl
```

## Brakujące dane

- Rzeczywiste zdarzenia czajnikowe dla poszczególnych trybów i faz.
- Potwierdzone dane fizycznego `grid_off`.
- Sparowane zmiany trybu przy możliwie niezmienionym obciążeniu fizycznym.

Brak tych danych nie może być zastępowany założeniami fizycznymi ani sztucznym
ground truth `Q` lub `S`.
