# Kontrakt danych

## Zwykłe dane historyczne

Wymagane kolumny:

```text
entity_id
state
last_changed
```

- `entity_id` identyfikuje sensor.
- `state` musi być możliwe do przekształcenia na liczbę dla używanych sensorów.
- `last_changed` musi być poprawnym znacznikiem czasu.
- Czasy są normalizowane do UTC.
- Model synchronizuje sensory na siatce określonej przez `ModelConfig.frequency`.

Pliki bazowe muszą pasować do:

```text
history*.csv
```

Model łączy wszystkie pasujące pliki ze wskazanego katalogu. CSV o innych
nazwach są ignorowane przez trening bazowy. Zapobiega to przypadkowemu użyciu
plików wynikowych, manifestów albo danych innych eksperymentów.

## Format wygenerowanego CSV

Wyniki generatora są zapisywane z ustawieniami:

```text
separator kolumn: ;
separator dziesiętny: ,
kodowanie: UTF-8
```

Przykład odczytu w pandas:

```python
generated=pd.read_csv(path,sep=";",decimal=",")
```

## Dane interwencji czysto czynnej

Pliki przyszłych prób mają pasować do:

```text
czajnik*.csv
```

Każdy plik powinien, o ile to możliwe, zawierać pełny cykl:

1. stabilny stan bazowy,
2. włączenie czajnika,
3. stan przejściowy,
4. stabilną pracę czajnika,
5. wyłączenie czajnika,
6. stan przejściowy,
7. stabilny stan po wyłączeniu.

Nie należy usuwać przejść ręcznie. Są potrzebne do nauczenia detektora granic,
ale nie będą traktowane jako stabilne stany generatora.

## Metadane zdarzenia

Minimalne metadane potrzebne do jednoznacznej walidacji:

- nazwa pliku,
- tryb pracy falownika,
- faza `L1`, `L2` albo `L3`,
- przybliżona moc znamionowa czajnika w watach,
- informacja, czy zapis obejmuje pełny cykl.

Preferowany plik `czajnik_manifest.csv`:

```csv
file,mode,target_phase,rated_power_w,complete_cycle
czajnik1.csv,grid_on_idle,L1,2000,true
```

Jeżeli manifestu nie będzie, model spróbuje wywnioskować tryb, fazę i zmianę
mocy z sensorów, ale wynik będzie wymagał potwierdzenia i może być niejednoznaczny
przy aktywnym balansowaniu.

## Zasady jakości

- Nie tworzyć kolumn ground truth `Q` lub `S` z aktualnych wzorów.
- Nie oznaczać całego obciążenia jako czysto czynne.
- Test czajnika dostarcza relacji `DeltaQ` w przybliżeniu równej zero, a nie
  wartości absolutnego `Q`.
- Całe zdarzenia muszą pozostać w jednym zbiorze train, validation albo test.
- Znacznie większe `DeltaP` niż obserwowane musi być oznaczone jako ekstrapolacja.
