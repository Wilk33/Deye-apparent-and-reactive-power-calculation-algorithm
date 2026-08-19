# Specyfikacja treningu modelu generatora stanów falownika Deye

## 1. Cel modelu

Model ma odwzorowywać zachowanie falownika na podstawie rzeczywistych danych z CSV i generować realistyczne, stabilne próbki dla różnych trybów pracy.

Model NIE ma wyznaczać ani generować prawdziwych wartości:

- `S` - mocy pozornej,
- `Q` - mocy biernej.

W danych treningowych tych wartości nie znamy, dlatego nie wolno tworzyć ich sztucznych etykiet i używać jako ground truth.

Głównym celem modelu jest wygenerowanie wiarygodnego odwzorowania:

$$
X=(U_g,I_g,U_i,I_i,P_g,P_i,P_l,\ldots)
$$

dla zadanego stanu pracy falownika.

Dopiero osobna warstwa analityczna ma później szukać takich wielkości:

$$
Q_{id}=F(X)
$$

oraz:

$$
S_{id}=\sqrt{P_l^2+Q_{id}^2}
$$

które zachowują poprawną matematykę i są możliwie niezależne od trybu pracy falownika.

---

## 2. Najważniejsze ograniczenie danych

Dane treningowe zawierają przede wszystkim obciążenie mieszane.

Nie wiadomo dla pojedynczej próbki, jaka część obserwowanego zachowania wynika z:

- mocy czynnej `P`,
- mocy biernej `Q`,
- naturalnej mocy biernej falownika,
- sposobu działania wewnętrznego balansowania faz,
- specyficznego sposobu reprezentacji prądów `Ig` i `Ii`.

Model nie ma więc informacji pozwalającej stwierdzić, że konkretna próbka ma znane `Q` lub `S`.

Zabronione jest tworzenie syntetycznych etykiet `S` albo `Q` na podstawie aktualnych hipotez matematycznych i późniejsze trenowanie modelu tak, jakby były to wartości rzeczywiste.

---

## 3. Co model ma nauczyć się z CSV

Model powinien nauczyć się rzeczywistych zależności pomiędzy obserwowalnymi wielkościami, w szczególności:

- `Ug1..3`, `Ig1..3`,
- `Ui1..3`, `Ii1..3`,
- `Pg1..3`, `Pi1..3`, `Pl1..3`,
- innych dostępnych cech potrzebnych do rozpoznania trybu pracy.

Model ma nauczyć się między innymi:

- korelacji pomiędzy rejestrami,
- rozkładów wartości,
- zależności pomiędzy fazami,
- zachowania `Ig` i `Ii` w różnych trybach,
- zachowania balansowania faz,
- zależności `Pg`, `Pi` i `Pl`,
- wpływu poziomu obciążenia,
- naturalnego rozrzutu danych,
- różnic napięć,
- zachowania falownika w stabilnych stanach pracy.

### Potwierdzony warunek fizyczny

Dla każdej fazy bardzo dobrze zachodzi:

$$
\boxed{P_l=P_g+P_i}
$$

Definiujemy:

$$
E_P=P_l-P_g-P_i
$$

Rozkład `E_P` generowany przez model powinien przypominać rozkład z rzeczywistych stabilnych danych. Nie należy wymuszać idealnego `E_P=0` dla każdej próbki, jeśli rzeczywiste dane zawierają niewielki szum.

---

## 4. Stany przejściowe i szpilki

Krótkie szpilki podczas:

- przełączania trybu pracy,
- aktywnego balansowania,
- gwałtownej zmiany rozdziału `Pg/Pi`,
- włączania i wyłączania dużego odbiornika,

nie są traktowane jako stabilny stan systemu.

W takich chwilach rejestry mogą reprezentować różne momenty działania regulatora i chwilowo tworzyć matematycznie niespójny zestaw danych.

### Wymaganie treningowe

Podstawowy generator stabilnych stanów:

- nie powinien uczyć się tych szpilek jako normalnego zachowania,
- powinien trenować przede wszystkim na ustabilizowanych fragmentach,
- próbki przejściowe powinny być usuwane albo oznaczane osobną klasą.

Nie należy ustalać sztywnego czasu odrzucania próbek bez analizy danych. Okno przejściowe powinno być identyfikowane na podstawie zaniku gwałtownych zmian i osiągnięcia stabilnego stanu.

---

## 5. Model bazowy nie zna `Q` ani `S`

Najważniejsza zasada:

$$
\boxed{\text{Model bazowy nie zna }Q}
$$

$$
\boxed{\text{Model bazowy nie zna }S}
$$

Dlatego interfejs typu `wygeneruj próbkę dla Q=300 var` jest niedozwolony, jeśli model nie posiada niezależnego modelu fizycznego.

Poprawny interfejs może wyglądać np. tak:

`wygeneruj stabilną próbkę dla grid_idle przy zadanym zakresie obserwowalnej mocy czynnej`.

Model może wtedy wygenerować realistyczne `Ug`, `Ig`, `Ui`, `Ii`, `Pg`, `Pi`, `Pl` itd., ale nie wolno twierdzić, że próbka ma znane `Q`.

---

## 6. Dodatkowa informacja treningowa - kontrolowana zmiana czysto czynna

Do modelu można dodać informację wynikającą z testu czajnika.

Nie znamy całkowitej mocy biernej instalacji przed ani po włączeniu czajnika. Wiemy jednak, że czajnik jest bardzo dobrym przybliżeniem dodatkowego obciążenia czynnego.

Dla takiej interwencji przyjmujemy:

$$
\boxed{\Delta Q\approx0}
$$

$$
\boxed{\Delta P=\Delta P_{active}}
$$

Stan początkowy może być dowolnym obciążeniem mieszanym:

$$
(P_0,Q_0)
$$

Po dołączeniu czajnika:

$$
P_1=P_0+\Delta P_{active}
$$

$$
\boxed{Q_1\approx Q_0}
$$

Nie znamy `Q0`. Znamy tylko warunek `DeltaQ≈0`. To nie jest informacja o absolutnym `Q`, lecz bardzo cenna informacja o zachowaniu układu pod kontrolowaną interwencją.

---

## 7. Model interwencji czysto czynnej

Generator powinien posiadać możliwość odwzorowania transformacji:

$$
X_0 \xrightarrow{+\Delta P_{active}} X_1
$$

gdzie:

- `X0` jest realistycznym mieszanym stanem instalacji,
- `X1` jest stanem po ustabilizowanym dołożeniu znanej mocy czynnej,
- charakter nieczynnej części obciążenia pozostaje możliwie niezmieniony.

Model NIE ma przypisywać `Q0` ani `Q1`. Ma nauczyć się z rzeczywistych par przed/po, jak rejestry falownika zmieniają się po dołożeniu prawie czysto czynnego odbiornika.

### Oczekiwany interfejs logiczny

```text
X1 = apply_active_load(
	X0,
	delta_p,
	target_phase,
	mode
)
```

Znaczenie:

- `X0` - wygenerowany lub rzeczywisty stabilny stan mieszany,
- `delta_p` - moc czynna dodawana albo odejmowana,
- `target_phase` - faza odbiornika,
- `mode` - tryb pracy falownika, który ma zostać zachowany.

---

## 8. Interwencja NIE jest prostym dodaniem `P`

Nie wolno realizować całego modelu jako:

```text
Pl[target_phase] += delta_p
Pi[target_phase] += delta_p
```

Taki skrót jest poprawny tylko w części stanów pracy.

Przy aktywnym balansowaniu dołożenie obciążenia na L1 może zmienić również:

- `Pg1`, `Pg2`, `Pg3`,
- `Pi1`, `Pi2`, `Pi3`,
- `Ig1..3`,
- `Ii1..3`.

Model ma odtworzyć tę odpowiedź zgodnie z zachowaniem nauczonym z CSV.

Interwencja `+DeltaP_active` jest zmianą fizyczznego obciążenia, a model ma wygenerować wynikający z niej stabilny rozdział mocy.

---

## 9. Zachowanie trybu pracy podczas interwencji

Domyślnie interwencja ma zachowywać zadany tryb pracy.

Przykładowo `grid_idle` powinien pozostać `grid_idle`, jeśli stan po zmianie mieści się w zakresie fizycznie obserwowanym dla tego trybu.

Analogicznie `grid_import_balancing` ma pozostać trybem balansowania.

Model nie powinien sam przełączać trybu tylko dlatego, że zmieniła się moc czynna, chyba że taki mechanizm jest świadomie modelowany.

Jeżeli warunki wychodzą poza zakres treningowy, próbka powinna być oznaczona jako ekstrapolacja albo niewiarygodna dla celów badawczych.

---

## 10. Budowanie par treningowych `+DeltaP`

Najlepszy schemat zdarzenia:

1. stabilny fragment przed włączeniem czajnika,
2. odrzucenie okresu przejściowego,
3. stabilny fragment podczas pracy czajnika,
4. odrzucenie okresu przejściowego przy wyłączeniu,
5. stabilny fragment po wyłączeniu.

Powstaje:

$$
X_0\rightarrow X_1\rightarrow X_2
$$

- `X0` - stan bazowy,
- `X1` - stan po dołożeniu `+DeltaP`,
- `X2` - stan po usunięciu `-DeltaP`.

Oczekujemy:

$$
P(X_1)>P(X_0)
$$

$$
P(X_2)\approx P(X_0)
$$

Nie zakładamy znajomości `Q`. Zakładamy tylko, że ukryta fizyczna wielkość bierna spełnia w przybliżeniu:

$$
Q(X_0)\approx Q(X_1)\approx Q(X_2)
$$

---

## 11. Reprezentacja ukryta

Jeżeli architektura posiada przestrzeń latentną, warto rozdzielić reprezentację na:

- część opisującą moc czynną i jej rozdział,
- część opisującą pozostały charakter obciążenia.

Nie należy nazywać drugiej części `Q`, ponieważ nie znamy jej skali ani fizycznej interpretacji. Można użyć np. `z_nonactive`.

Dla par czajnikowych model powinien być zachęcany do spełnienia:

$$
\boxed{z_{nonactive}(X_0)\approx z_{nonactive}(X_1)\approx z_{nonactive}(X_2)}
$$

przy jednoczesnej dużej zmianie składowej czynnej.

Jeżeli model nie ma jawnej przestrzeni latentnej, można uczyć bezpośrednio transformacji:

$$
T(X,\Delta P_{active},mode)\rightarrow X'
$$

---

## 12. Interpolacja i ekstrapolacja `DeltaP`

Nie wolno zakładać, że pojedynczy test czajnika automatycznie daje zweryfikowane dane dla dowolnego `DeltaP`.

### Interpolacja

Generowanie `DeltaP` w zakresie dobrze pokrytym przez dane może być traktowane jako najbardziej wiarygodne.

### Ekstrapolacja

Generowanie znacznie większych zmian niż obserwowane w treningu powinno być jawnie oznaczone jako ekstrapolowane. Takie próbki nie mogą być traktowane jak równoważny ground truth.

---

## 13. Test round-trip

Model powinien przechodzić test:

$$
X_0\xrightarrow{+\Delta P}X_1\xrightarrow{-\Delta P}X_2
$$

Oczekujemy:

$$
\boxed{X_2\approx X_0}
$$

w sensie rozkładu stabilnych parametrów.

Nie oczekujemy identyczności każdej liczby, jeśli generator jest probabilistyczny. Oczekujemy jednak powrotu do tego samego regionu przestrzeni stanów.

---

## 14. Zachowanie innych faz

Jeżeli obciążenie czynne zostanie dodane na jednej fazie, pozostałe fazy nie muszą pozostać numerycznie niezmienione.

W trybie balansowania model może poprawnie odpowiedzieć zmianą na wszystkich fazach.

Nie wolno ręcznie narzucać `DeltaX_L2=0` i `DeltaX_L3=0` tylko dlatego, że odbiornik dołączono na L1.

Model ma nauczyć się odpowiedzi wielofazowej z CSV.

---

## 15. Zmiana trybu bez zmiany fizycznego obciążenia

Drugim bardzo wartościowym rodzajem danych są przejścia:

$$
mode_A\rightarrow mode_B
$$

przy prawie niezmienionym fizycznym obciążeniu.

Przykład:

$$
battery\rightarrow grid\_import\_balancing
$$

Rejestry mogą zmienić się mocno, mimo że odbiorniki praktycznie się nie zmieniły.

Model powinien potrafić generować różne reprezentacje rejestrowe podobnego stanu obciążenia w różnych trybach pracy. Takie pary będą później kluczowe do wyszukiwania `Qid`.

---

## 16. Do czego generator będzie używany

Generator NIE jest końcowym estymatorem `Q`.

Ma utworzyć wirtualne stanowisko badawcze do testowania funkcji:

$$
Q_{id}=F(X)
$$

Dobra funkcja `F` powinna później spełniać:

### Niezmienność na dołożenie mocy czynnej

$$
F(X_0)\approx F(X_{+\Delta P})
$$

### Niezmienność na zmianę trybu

Jeżeli fizyczne obciążenie pozostaje podobne:

$$
F(X_{modeA})\approx F(X_{modeB})
$$

### Matematyczna zgodność

Po znalezieniu `Qid` definiujemy:

$$
\boxed{S_{id}=\sqrt{P_l^2+Q_{id}^2}}
$$

co zapewnia:

$$
\boxed{S_{id}^2=P_l^2+Q_{id}^2}
$$

---

## 17. Czego NIE wolno robić

### Nie generować arbitralnego `Q`

Nie wolno przypisywać losowego `Q` wygenerowanej próbce jako ground truth.

### Nie generować arbitralnego `S`

Nie wolno przypisywać losowego `S` jako prawdziwej mocy pozornej, jeśli nie wynika z niezależnego modelu fizycznego.

### Nie trenować na `Q` policzonym aktualnym wzorem

Aktualne i przyszłe wzory są hipotezami badawczymi. Użycie ich wyników jako etykiet treningowych spowodowałoby sprzężenie zwrotne i utratę wartości badawczej.

### Nie zakładać, że `Ig` i `Ii` są klasycznymi RMS

Dane wskazują, że takie założenie nie jest uniwersalnie poprawne.

### Nie zakładać, że cały układ jest czysto czynny

Test czajnika daje tylko:

$$
\boxed{\Delta Q\approx0}
$$

Nie daje `Q_total=0`.

---

## 18. Zalecana funkcja kosztu

Dokładna postać zależy od architektury, ale powinna uwzględniać niezależne cele:

$$
L=w_1L_{data}+w_2L_{balance}+w_3L_{mode}+w_4L_{active}+w_5L_{cycle}
$$

- `L_data` - zgodność rozkładu generowanych rejestrów z rzeczywistymi stabilnymi danymi.
- `L_balance` - zgodność rozkładu `Pl-Pg-Pi` z CSV, bez sztucznego wymuszania dokładnego zera.
- `L_mode` - kara za próbkę niezgodną z zadanym trybem.
- `L_active` - zgodność transformacji `+DeltaP` z rzeczywistymi parami czajnikowymi.
- `L_cycle` - kara za brak powrotu po `+DeltaP` i `-DeltaP`.

---

## 19. Podział danych treningowych i walidacyjnych

Nie należy losowo mieszać sąsiadujących próbek z jednego zdarzenia pomiędzy train i validation. Powoduje to leakage czasowy.

Zalecane:

- całe zdarzenia ON/OFF trafiają tylko do jednego splitu,
- całe stabilne fragmenty czasowe trafiają tylko do jednego splitu,
- jeśli danych jest wystarczająco dużo, całe dni mogą być niezależnymi hold-outami.

Test używany do końcowej walidacji nie powinien być identycznym zdarzeniem użytym do treningu transformacji.

---

## 20. Minimalne testy akceptacyjne generatora

### Test A - stabilny stan
Generator tworzy próbki odpowiadające rozkładowi rzeczywistych stabilnych danych i nie generuje nienaturalnych szpilek jako normalnego stanu.

### Test B - bilans mocy czynnej
Rozkład `Pl-Pg-Pi` jest zgodny z rzeczywistym CSV.

### Test C - aktywna interwencja
Po `+DeltaP_active` moc czynna Load rośnie zgodnie z żądaniem, a pozostałe rejestry reagują zgodnie z trybem pracy.

### Test D - round-trip
`+DeltaP` i późniejsze `-DeltaP` prowadzi do stanu zgodnego z bazowym.

### Test E - faza docelowa
Model poprawnie reaguje na dodanie odbiornika na wskazanej fazie.

### Test F - balansowanie
W trybie balansowania model może zmieniać wszystkie fazy zgodnie z zachowaniem z danych.

### Test G - brak sztucznego `Q/S`
Model nie używa sztucznej etykiety `Q` ani `S` do generowania próbek.

---

## 21. Docelowy eksperyment dla poszukiwania `Qid`

Po wytrenowaniu generatora należy tworzyć rodziny próbek, np.:

```text
base = generate(mode="grid_idle", ...)
x0 = base
x1 = apply_active_load(base, +500 W, L1)
x2 = apply_active_load(base, +1000 W, L1)
x3 = apply_active_load(base, +1500 W, L1)
```

Wszystkie te próbki powinny reprezentować ten sam nieznany składnik bierny bazowego obciążenia, o ile wartości `DeltaP` mieszczą się w wiarygodnym zakresie modelu.

Następnie testujemy kandydatów:

$$
Q_{id}=F(X)
$$

i oczekujemy:

$$
\boxed{F(x_0)\approx F(x_1)\approx F(x_2)\approx F(x_3)}
$$

Analogicznie należy badać odpowiedniki podobnego obciążenia w różnych trybach pracy.

---

## 22. Najważniejsza zasada dla Codexu

Model ma nauczyć się:

$$
\boxed{\text{jak zachowują się obserwowalne rejestry falownika}}
$$

Nie ma nauczyć się:

$$
\boxed{\text{jakie jest prawdziwe }Q}
$$

bo tej informacji nie ma w danych.

Informacja z czajnika dodaje tylko kontrolowaną relację:

$$
\boxed{\Delta P\neq0,\qquad \Delta Q\approx0}
$$

Nie dostarcza wartości absolutnej `Q`.

Generator ma dzięki temu umożliwić tworzenie kontrolowanych rodzin próbek, które później posłużą do matematycznego poszukiwania `Qid`.

---

## 23. Kryterium sukcesu

Model jest poprawny, jeżeli potrafi:

- generować realistyczne stabilne dane w różnych trybach pracy,
- realistycznie zasymulować dołożenie czysto czynnej mocy do istniejącego mieszanego obciążenia,
- zachować strukturę wielofazową i zachowanie balansowania,
- zachować realny rozkład błędu `Pl-Pg-Pi`,
- nie wymyślać ground truth `Q` ani `S`,
- tworzyć wiarygodne kontrfaktyczne rodziny próbek do późniejszego wyszukiwania `Qid`.

Model NIE musi znać prawdziwego `Q`.

Sukces oznacza, że późniejsza analiza otrzyma dobre wirtualne eksperymenty do znalezienia funkcji:

$$
Q_{id}=F(X)
$$

takiej, która nie reaguje sztucznie na samo `DeltaP_active`, zachowuje się możliwie podobnie przy zmianie trybu pracy i pozwala następnie zdefiniować:

$$
\boxed{S_{id}=\sqrt{P_l^2+Q_{id}^2}}
$$

bez przypisywania fałszywego ground truth `Q` do danych treningowych.
