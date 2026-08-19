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
W ostatniej walidacji zawierał 43 encje i 166746 wierszy, z których po
synchronizacji powstało 9120 kompletnych chwil pomiarowych. Dane obejmują
fizycznie połączoną sieć. Nie zawierają potwierdzonego `grid_off`.

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
