# Następne kroki

## Po dodaniu plików czajnikowych

1. Sprawdzić schemat, zakres czasu, kompletność sensorów i ciągłość każdego pliku.
2. Potwierdzić lub utworzyć manifest tryb/faza/moc.
3. Wykryć fragmenty bazowy/transition/active/transition/recovery na podstawie
   zaniku zmian, nie stałego czasu.
4. Zbudować pary i trójki `X0 -> X1 -> X2` na poziomie całych zdarzeń.
5. Podzielić dane według zdarzeń, bez przecieku sąsiednich próbek.
6. Nauczyć osobny model transformacji dla dostępnych par tryb/faza.
7. Zaimplementować wynik wiarygodności: interpolacja, ekstrapolacja albo brak
   pokrycia.
8. Uruchomić test round-trip `+DeltaP` i `-DeltaP`.
9. Sprawdzić reakcję pozostałych faz i balansowanie.
10. Dopiero po zaliczeniu testów udostępnić działające `apply_active_load`.

## Kryteria akceptacji

- Test A - stabilne próbki bez nienaturalnych szpilek.
- Test B - zgodny empiryczny rozkład `Pl-Pg-Pi`.
- Test C - realistyczna odpowiedź na `+DeltaP_active`.
- Test D - statystyczny powrót po round-trip.
- Test E - poprawna obsługa fazy docelowej.
- Test F - wielofazowa odpowiedź w trybie balansowania.
- Test G - brak sztucznego ground truth `Q` i `S`.

## Rutynowa walidacja po każdej zmianie

```powershell
pytest
ruff check .
python -m compileall -q src
deye-model fit --csv data --model models\deye_simulator.pkl --summary
deye-model generate --model models\deye_simulator.pkl `
	--mode grid_on_export --mode grid_on_idle `
	--samples-per-mode 100 --random-state 42 `
	--output generated\validation.csv
```

Jeżeli po nowych danych pojawi się co najmniej 100 stabilnych próbek importu lub
fizycznego `grid_off`, należy ponownie sprawdzić dostępne tryby w `inspect`.
