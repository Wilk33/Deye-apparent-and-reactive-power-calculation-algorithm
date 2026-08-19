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
|   `-- history.csv
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

Plik `data/history.csv` zawiera próbki pomiarowe w kolumnach:

- `entity_id` - identyfikator encji pomiarowej,
- `state` - zarejestrowana wartość,
- `last_changed` - znacznik czasu próbki.

Plik jest przechowywany bezpośrednio w Git. Przy znacznie większych zbiorach danych
warto rozważyć Git LFS albo publikowanie danych jako osobnego artefaktu.

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

## LabVIEW

Pliki projektu LabVIEW należy umieszczać w katalogu `labview`. Repozytorium śledzi
pliki źródłowe, między innymi `.vi`, `.ctl`, `.lvlib`, `.lvclass` i `.lvproj`, ale
pomija pliki lokalne, tymczasowe, kopie zapasowe oraz wyniki kompilacji.

## Licencja

Projekt jest udostępniany na warunkach licencji Apache License 2.0. Szczegóły
znajdują się w pliku `LICENSE`.
