# Deye - algorytm obliczania mocy pozornej i biernej

Repozytorium przeznaczone do opracowania i porównania implementacji algorytmu
obliczania mocy pozornej oraz biernej dla danych z falownika Deye.

Projekt przewiduje dwie implementacje:

- Python - analiza danych, prototypowanie algorytmu i testy automatyczne,
- LabVIEW - implementacja pomiarowa oraz integracja z aplikacją docelową.

## Struktura repozytorium

```text
.
|-- data/
|   `-- history*.csv
|-- context/
|   |-- README.md
|   |-- PROJECT_STATE.md
|   |-- DECISIONS.md
|   |-- DATA_CONTRACT.md
|   |-- DATASET_PROFILE.md
|   |-- SPEC_TRENINGU_MODELU_DEYE_QID.md
|   `-- NEXT_STEPS.md
|-- labview/
|   `-- README.md
|-- src/
|   `-- deye_power_calculation/
|       `-- __init__.py
|-- tests/
|-- .editorconfig
|-- .gitattributes
|-- .gitignore
`-- pyproject.toml
```

## Dane pomiarowe

Pliki `data/history*.csv` zawierają próbki pomiarowe w kolumnach:

- `entity_id` - identyfikator encji pomiarowej,
- `state` - zarejestrowana wartość,
- `last_changed` - znacznik czasu próbki.

Model automatycznie łączy wszystkie pliki pasujące do `history*.csv` ze
wskazanego katalogu. Pozostałe CSV nie trafiają do treningu bazowego. Pliki są
przechowywane bezpośrednio w Git. Przy znacznie większych zbiorach danych warto
rozważyć Git LFS albo publikowanie danych jako osobnego artefaktu.

## Środowisko Python

Wymagany jest Python 3.10 lub nowszy. Utworzenie środowiska i instalacja projektu
w trybie edytowalnym:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Uruchomienie testów i kontroli statycznej:

```powershell
pytest
ruff check .
```

## Model danych Deye

Moduł `src/deye_power_calculation/model_deye.py` jest generatywnym symulatorem
zachowania falownika. Uczy wielowymiarowy model VAR(1) na stabilnych fragmentach
jednego albo wielu plików CSV. Sensory PV i baterii pomagają rozpoznać reżimy
podczas treningu, ale nie występują w wygenerowanym wyjściu.

Najpierw należy wytrenować i zapisać model:

```powershell
deye-model fit `
	--csv data `
	--model models/deye_simulator.pkl `
	--summary
```

Późniejsze generowanie nie wymaga dostępu do CSV:

```powershell
deye-model generate `
	--model models/deye_simulator.pkl `
	--mode grid_on_import `
	--mode grid_on_export `
	--samples-per-mode 100 `
	--output generated/deye_simulated_200.csv
```

Wygenerowany CSV używa formatu wygodnego dla polskich ustawień regionalnych:

```text
separator kolumn: ;
separator dziesiętny: ,
```

Przy ponownym odczycie w pandas należy użyć:

```python
generated=pd.read_csv(
	"generated/deye_simulated_200.csv",
	sep=";",
	decimal=",",
)
```

Z poziomu Pythona:

```python
from deye_power_calculation.model_deye import DeyeModel

model=DeyeModel.load("models/deye_simulator.pkl")
samples=model.generate(
	"grid_on_import + grid_on_export",
	samples_per_mode=100,
	random_state=42,
)
```

Generator zwraca stabilne, syntetyczne sekwencje 28 dozwolonych sensorów. Nie
oblicza `VA` ani `var`, ponieważ te wartości będą należały do późniejszych,
niezależnych modeli obliczeniowych testowanych na wyjściu symulatora. Szczegółowe
założenia i ograniczenia opisano w `docs/model_deye.md`.

Generator zachowuje empiryczny rozkład niewielkiego błędu `Pl-Pg-Pi`. Stany
przejściowe są wykrywane na podstawie zaniku zmian wielu sensorów, a nie stałego
czasu odcięcia.

Pliki `czajnik*.csv` są celowo oddzielane od bazowego treningu. Posłużą do
nauczenia osobnej transformacji czysto czynnej. Do czasu dostarczenia takich
danych `apply_active_load` jawnie odmawia działania zamiast tworzyć sztuczną
odpowiedź falownika.

Tryb `grid_off` może być generowany również bez rzeczywistych przykładów, ale
jest wtedy jawnie oznaczony jako `extrapolation_unverified`. Rejestry Grid są
zerowane, a pozostałe zachowanie pochodzi z najbliższego nauczonego reżimu
`grid_on`. Tego wyniku nie należy traktować jako pomiarowo zweryfikowanego.

## Kontynuacja na innym urządzeniu

Katalog `context` zawiera nadrzędną specyfikację, aktualny stan, decyzje,
kontrakt danych i następne kroki. Należy rozpocząć od `context/README.md`. Dzięki
temu projekt można wznowić z samego repozytorium bez historii poprzedniej sesji.

## LabVIEW

Pliki projektu LabVIEW należy umieszczać w katalogu `labview`. Repozytorium śledzi
pliki źródłowe, między innymi `.vi`, `.ctl`, `.lvlib`, `.lvclass` i `.lvproj`, ale
pomija pliki lokalne, tymczasowe, kopie zapasowe oraz wyniki kompilacji.

## Licencja

Projekt jest udostępniany na warunkach licencji Apache License 2.0. Szczegóły
znajdują się w pliku `LICENSE`.
