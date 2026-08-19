# LabVIEW

Ten katalog jest przeznaczony na kod źródłowy LabVIEW.

Zalecana organizacja:

- `Deye Power Calculation.lvproj` - główny projekt,
- `VIs/` - funkcje i główne przyrządy wirtualne,
- `Controls/` - współdzielone kontrolki i definicje typów,
- `Tests/` - testy algorytmu wykonywane w LabVIEW.

Pliki źródłowe LabVIEW są traktowane przez Git jako pliki binarne. Lokalne pliki
ustawień, kopie zapasowe i artefakty kompilacji są pomijane przez `.gitignore`.
