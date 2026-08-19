# Generatywny symulator falownika Deye

## Cel

Model tworzy stabilne, prawdopodobne sekwencje sensorów falownika. Wygenerowane
dane służą jako powtarzalne wejście do testowania przyszłych algorytmów
obliczających między innymi moc pozorną i bierną.

Model nie implementuje obecnie wzorów Q1 ani Q2 z dokumentu
`podsumowanie_model_Q_Deye.md`. Ten dokument pozostaje materiałem dla późniejszych
modeli obliczeniowych, które będą testowane na wyjściu symulatora.

## Trening i generowanie

Proces składa się z dwóch niezależnych etapów:

1. trening na jednym albo wielu plikach CSV i zapis modelu do `.pkl`,
2. wczytanie zapisanego modelu i generowanie bez dostępu do CSV.

Przykład:

```powershell
deye-model fit `
	--csv data/history.csv `
	--model models/deye_simulator.pkl `
	--summary

deye-model generate `
	--model models/deye_simulator.pkl `
	--mode grid_on_import `
	--mode grid_on_export `
	--samples-per-mode 100 `
	--random-state 42 `
	--output generated/deye_simulated_import_export_200.csv
```

Pliki pickle mogą wykonywać kod podczas wczytywania. Należy wczytywać wyłącznie
pliki modelu utworzone lokalnie albo pochodzące z zaufanego źródła.

## Znaczenie próbki

Jedna próbka to jednoczesny wektor wszystkich 28 dozwolonych sensorów. Dane
wejściowe są synchronizowane do siatki 5 sekund. Wartość sensora może zostać
przeniesiona do przodu najwyżej o 65 sekund.

Wynik zawiera dodatkowo:

- `sample_index` - indeks całego wyniku,
- `mode_sample_index` - indeks w żądanym trybie,
- `sequence_id` - identyfikator niezależnej stabilnej sekwencji,
- `simulation_time_s` - czas symulacji w sekundach,
- `operating_mode` - tryb żądany przez użytkownika,
- `source_regime` - szczegółowy reżim użyty przez generator,
- `model_type` - typ generatora.

## Sensory używane tylko do treningu

Sensory:

```text
sensor.deye_pv_power
sensor.deye_battery_power
```

pomagają wykrywać zmiany reżimu i odcinać okresy przejściowe. Model rozdziela
każdy publiczny tryb na ukryte stany:

- PV aktywne albo nieaktywne,
- moc baterii dodatnia, ujemna albo bliska zera.

Zmiana ukrytego stanu rozpoczyna nowy segment. Początek i koniec segmentu są
usuwane z treningu. PV i bateria nie są później zwracane przez generator.

Pozostałe sensory wskazane jako wykluczone również nie występują w wyjściu.

## Rozpoznawane tryby

Połączenie z siecią jest rozpoznawane na podstawie napięć trzech faz:

- `grid_on` - minimalne napięcie fazowe wynosi co najmniej 180 V,
- `grid_off` - maksymalne napięcie fazowe wynosi najwyżej 50 V,
- obszar pomiędzy progami jest nierozpoznany i nie służy do treningu.

Przy aktywnym Grid reżim jest dalej dzielony według sumy mocy fazowej Grid:

- `grid_on_import` - suma większa niż 150 W,
- `grid_on_export` - suma mniejsza niż -150 W,
- `grid_on_idle` - suma od -150 W do 150 W.

`grid_on` jest trybem zbiorczym. Podczas generowania wybiera reżimy import,
eksport i idle zgodnie z ich udziałem w danych treningowych.

Aktualny CSV nie zawiera `grid_off`. Najniższe napięcie Grid wynosi 216,1 V.
Generator odmawia więc generowania `grid_off`. Tryb pojawi się automatycznie po
ponownym treningu na danych zawierających co najmniej 100 stabilnych próbek z
napięciami wszystkich faz poniżej 50 V.

## Usuwanie przejść

Przejścia nie są odrzucane przez sztywny czas po zmianie trybu. Model oblicza
odporny wynik zmian wielu sensorów. Skala każdej cechy wynika z jej typowych
zmian i zakresu, a próg gwałtownej zmiany jest wyznaczany z rozkładu danych za
pomocą kwantyla i medianowego odchylenia bezwzględnego.

Próbka staje się stabilna dopiero po potwierdzonym zaniku zmian w kolejnych
pomiarach. Stabilny fragment musi mieć co najmniej 6 próbek. Segment jest także
przerywany, gdy zmienia się:

- stan połączenia i przepływu Grid,
- aktywność PV,
- kierunek lub bezczynność baterii.

Dzięki temu długość odrzuconego przejścia wynika z rzeczywistego zaniku zmian,
a nie z arbitralnej liczby sekund.

## Generator VAR(1)

Dla każdego dostępnego trybu model uczy jednocześnie wszystkich 28 sensorów:

```text
X[t+1]=intercept+X[t]*A+residual[t]
```

gdzie:

- `X[t]` jest wektorem wszystkich sensorów w chwili `t`,
- `A` opisuje zależność następnej próbki od poprzedniej,
- `residual[t]` jest całym rzeczywistym wektorem reszt losowanym z treningu.

Losowanie całego wektora reszt zachowuje współzależności pomiędzy sensorami.
Macierz przejścia jest stabilizowana do promienia spektralnego najwyżej 0,98.
Wygenerowane wartości są ograniczane do przedziału od kwantyla 0,5 procent do
kwantyla 99,5 procent danych treningowych danego trybu.

Generator tworzy nowe sekwencje. Nie kopiuje całych gotowych wierszy z CSV.
Parametr `random_state` umożliwia dokładne odtworzenie tego samego wyniku.

Po generowaniu odtwarzany jest empiryczny rozkład błędu bilansu mocy czynnej:

```text
E_P=Pload_phase-Pgrid_phase-Pinverter_phase
```

Błędy trzech faz oraz błędy rejestrów sum Grid, Inverter i Load są losowane jako
jeden wspólny wektor z rzeczywistych stabilnych danych. Zachowuje to niewielki
szum pomiarowy i współzależności błędów. Skrajne wartości są ograniczane do
odpornych kwantyli, aby szpilki przejściowe nie stawały się normalnym zachowaniem.

## Interwencje czysto czynne

Pliki pasujące do `czajnik*.csv` są automatycznie oddzielane od zwykłych danych
bazowych. Nie trafiają do modelu VAR stabilnych stanów.

Model udostępnia interfejs:

```python
changed=model.apply_active_load(
	state=base_state,
	delta_p=2000.0,
	target_phase="L1",
	mode="grid_on_idle",
)
```

Dopóki nie zostaną dostarczone rzeczywiste pary przed/po dla danego trybu i
fazy, wywołanie zwraca `InterventionUnavailableError`. Jest to celowe. Model nie
zastępuje brakujących danych prostym dodawaniem mocy do `Pl` albo `Pi` i nie
przypisuje próbkom sztucznego `Q` lub `S`.

Szczegóły kontraktu przyszłych danych znajdują się w `context/DATA_CONTRACT.md`.

## Minimalna liczba próbek

Do wytrenowania szczegółowego trybu wymagane jest co najmniej 100 stabilnych
próbek. Generowanie również wymaga co najmniej 100 próbek na żądany tryb.

Wywołanie:

```python
samples=model.generate(
	"grid_on_import + grid_on_export",
	samples_per_mode=100,
	random_state=42,
)
```

zwraca dokładnie 200 próbek.

## Dodawanie kolejnych danych

Po dostarczeniu nowych plików należy ponownie wytrenować model na całym katalogu:

```powershell
deye-model fit `
	--csv data `
	--model models/deye_simulator.pkl `
	--summary
```

Nowy plik zastępuje wcześniejszy model i uwzględnia wszystkie zwykłe CSV
znajdujące się w katalogu. Pliki `czajnik*.csv` są wykrywane, raportowane i
wyłączane z bazowego treningu. Jeśli zwykłe dane zawierają brakujący tryb,
zostanie on dodany pod warunkiem osiągnięcia minimalnej liczby stabilnych próbek.

## Celowo pominięte VA i var

Symulator nie zwraca `VA` ani `var`. Wartości te byłyby wynikiem konkretnego
algorytmu obliczeniowego, a zadaniem tego modelu jest dostarczenie niezależnych
danych wejściowych do porównywania takich algorytmów. Zostaną dodane dopiero po
ustaleniu wiarygodnej wartości referencyjnej lub osobnego modelu celu.
