# Decyzje architektoniczne

## D-001 - Generator jest niezależny od przyszłego estymatora Qid

Model bazowy generuje tylko obserwowalne rejestry. Nie używa wyników obecnych ani
przyszłych wzorów `Qid` jako etykiet. Zapobiega to sprzężeniu zwrotnemu, w którym
generator potwierdzałby hipotezę użytą do jego treningu.

## D-002 - PV i bateria są sygnałami treningowymi

`sensor.deye_pv_power` i `sensor.deye_battery_power` pomagają identyfikować
ukryty stan pracy. Nie są częścią wygenerowanej odpowiedzi modelu.

## D-003 - Stabilność wynika z danych

Stan stabilny jest rozpoznawany przez odporny wynik zmian wielu sensorów,
próg wyznaczony z rozkładu zmian oraz potwierdzenie zaniku zmian. Stała liczba
sekund po każdym zdarzeniu nie jest uznawana za wystarczającą definicję.

## D-004 - Błąd bilansu nie jest zerowany

Dla każdej fazy model zachowuje empiryczny rozkład:

```text
E_P=Pl-Pg-Pi
```

Błędy trzech faz oraz błędy rejestrów sum są losowane jako wspólny wektor z
rzeczywistych stabilnych danych. Skrajne wartości są ograniczane do odpornych
kwantyli, aby stany przejściowe nie wracały jako normalne próbki.

## D-005 - Pliki czajnikowe nie trafiają do bazowego VAR

Pliki pasujące do `czajnik*.csv` są wykrywane, ale wyłączane z treningu
stabilnego generatora. Będą źródłem osobnego modelu transformacji
`X0 -> X1`, po analizie rzeczywistego formatu i zdarzeń.

## D-006 - Brak danych oznacza jawną odmowę

`apply_active_load` nie wykonuje zastępczego `Pl+=delta_p` ani `Pi+=delta_p`.
Jeśli nie istnieje wyuczony model dla trybu i fazy, zwraca
`InterventionUnavailableError`.

## D-007 - Podział walidacyjny będzie zdarzeniowy

Cały cykl czajnika przed/włączony/po musi trafić do jednego splitu. Sąsiadujące
próbki jednego zdarzenia nie mogą być losowo mieszane między train i validation.

## D-008 - Pickle jest tylko zaufanym artefaktem

Pliki pickle mogą wykonywać kod podczas wczytywania. Należy ładować wyłącznie
model utworzony w tym projekcie albo pochodzący z innego zaufanego źródła.

## D-009 - Grid off może działać jako jawna ekstrapolacja

Jeżeli nie ma rzeczywistych danych `grid_off`, generator może wyzerować wszystkie
rejestry Grid i użyć zachowania Inverter z najbliższego nauczonego reżimu
`grid_on`. Load jest ponownie budowany z zachowaniem empirycznego błędu
`Pl-Pg-Pi`.

Każdy taki wynik musi mieć `generation_status=extrapolation_unverified` i opis
założenia. Nie wolno przedstawiać go jako zachowania nauczonego lub pomiarowo
potwierdzonego. Rzeczywiste dane `grid_off`, jeśli kiedyś się pojawią, mają
pierwszeństwo i automatycznie zastępują fallback.

## D-010 - Nazwy wejściowe i regionalny format wyjścia są stałym kontraktem

Trening bazowy przyjmuje ze wskazanego katalogu wyłącznie pliki pasujące do
`history*.csv`. Umożliwia to dokładanie kolejnych eksportów bez zmiany kodu i
chroni model przed przypadkowym wczytaniem innych CSV.

Wyniki generatora są zapisywane z separatorem kolumn `;` i separatorem
dziesiętnym `,`. Jest to domyślny kontrakt pliku wynikowego dla Pythona, LabVIEW
i narzędzi używających polskich ustawień regionalnych.
