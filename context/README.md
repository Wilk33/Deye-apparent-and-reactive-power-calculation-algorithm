# Kontekst projektu Deye

Ten katalog jest wersjonowanym punktem wznowienia pracy. Ma umożliwić pełną
kontynuację po zmianie sesji, komputera albo osoby wykonującej analizę, bez
polegania na historii rozmowy.

Kolejność czytania:

1. `SPEC_TRENINGU_MODELU_DEYE_QID.md` - nadrzędna specyfikacja badawcza.
2. `PROJECT_STATE.md` - stan wykonanej pracy i zweryfikowane wyniki.
3. `DECISIONS.md` - decyzje architektoniczne i ich uzasadnienie.
4. `DATA_CONTRACT.md` - wymagany format danych historycznych i czajnikowych.
5. `DATASET_PROFILE.md` - zweryfikowany profil aktualnego `history.csv`.
6. `NEXT_STEPS.md` - kolejność dalszych prac.

Dokumentacja użytkowa modelu znajduje się w `docs/model_deye.md`. Kod źródłowy
znajduje się w `src/deye_power_calculation/model_deye.py`, a testy w
`tests/test_model_deye.py`.

## Szybkie wznowienie

```powershell
git clone https://github.com/Wilk33/Deye-apparent-and-reactive-power-calculation-algorithm.git
cd Deye-apparent-and-reactive-power-calculation-algorithm
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
ruff check .
```

Nie należy przenosić do tego katalogu tokenów, haseł, prywatnych kluczy ani
lokalnych ścieżek wymaganych tylko na jednym komputerze.
