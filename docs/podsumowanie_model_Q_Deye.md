# Model wyznaczania mocy biernej z rejestrów Deye/Sunsynk

## 1. Cel

Celem jest wyznaczenie mocy biernej `Q` dla każdej fazy falownika Deye 3-fazowego LV na podstawie dostępnych rejestrów:

- napięcia Grid `Ug`,
- prądu Grid `Ig`,
- napięcia Inverter `Ui`,
- prądu Inverter `Ii`,
- mocy czynnej Grid `Pg`,
- mocy czynnej Inverter `Pi`,
- opcjonalnie mocy czynnej Load `Pl`.

Problem polega na tym, że rejestry `Ig` i `Ii` nie są w każdym stanie pracy zwykłymi wartościami RMS. W pewnych stanach iloczyny `U*I` zachowują się bardzo dobrze bilansowo, ale pojedynczo mogą odbiegać od klasycznej mocy pozornej.

## 2. Konwencja znaków

Dla jednej fazy:

- `Pg > 0` - import energii z sieci.
- `Pg < 0` - eksport energii do sieci.
- `Ig` jest zawsze dodatnie jako moduł rejestru prądu.
- `Pi > 0` - falownik oddaje moc do strony AC.
- `Pi < 0` - falownik pobiera moc z danej fazy.
- `Ii > 0` - falownik oddaje energię.
- `Ii < 0` - falownik pobiera energię.

Potwierdzony bilans mocy czynnej:

\[
\boxed{P_l=P_g+P_i}
\]

Dla trzech faz:

\[
\boxed{
P_{l1}+P_{l2}+P_{l3}
=
P_{g1}+P_{g2}+P_{g3}
+
P_{i1}+P_{i2}+P_{i3}
}
\]

## 3. Rejestry używane w analizie

Prądy:

- Grid current: `610`, `611`, `612`.
- Inverter current: `630`, `631`, `632`.

Napięcia:

- Grid voltage: `598`, `599`, `600`.
- Inverter voltage: `627`, `628`, `629`.

Moce czynne Grid:

- L1 `604/700`.
- L2 `605/701`.
- L3 `606/702`.

Moce czynne Inverter:

- L1 `633/691`.
- L2 `634/692`.
- L3 `635/693`.

## 4. Co wiadomo o `UgIg` i `UiIi`

`Ig` i `Ii` nie zachowują się uniwersalnie jak klasyczne RMS.

Często obserwowano sytuację, w której:

\[
U_gI_g
\]

jest o około `20-30 VA` za małe, natomiast:

\[
U_iI_i
\]

o podobną wartość za duże.

Nie znaleziono jednak stałego offsetu. Około `30 VA` jest tylko częstą obserwacją.

W części stanów pracy błędy są skorelowane:

\[
U_gI_g=A-e
\]

\[
U_iI_i=B+e
\]

więc:

\[
U_gI_g+U_iI_i=A+B
\]

i błąd `e` znika.

# 5. Pierwszy model - odrzucony jako uniwersalny

Testowano:

\[
S'=U_gI_g+U_iI_i+2\min(P_g,0)
\]

\[
Q'=\sqrt{S'^2-(P_g+P_i)^2}
\]

Model przechodził testy teoretyczne dla:

- baterii,
- importu,
- eksportu,
- obciążenia czysto czynnego,
- obciążenia z mocą bierną.

Problem ujawnił się na rzeczywistych danych z czajnikiem i piekarnikiem.

Jeżeli:

\[
M=S'-|P|
\]

to:

\[
S'=P+M
\]

a więc:

\[
Q'^2=(P+M)^2-P^2
\]

\[
\boxed{Q'^2=2PM+M^2}
\]

Dlatego nawet przy prawie stałym `M` sam wzrost mocy czynnej `P` powoduje sztuczny wzrost `Q'`.

Przykład czajnika:

- przed: około `P=818 W`, `Q'≈992 var`,
- czajnik ON: około `P=2203 W`, `Q'≈1521 var`.

Wzrost około `1.4 kW` mocy prawie czysto czynnej powodował ponad `500 var` sztucznego wzrostu `Q'`.

Wniosek:

\[
\boxed{
S'=U_gI_g+U_iI_i+2\min(P_g,0)
}
\]

nie może być traktowane jako rzeczywista całkowita moc pozorna Load.

# 6. Model nr 1 - bateria / PV bez aktywnego balansowania

Dla tego stanu przyjęto model:

\[
U_gI_g=S_g-e
\]

\[
U_iI_i=P_i+e
\]

Dodając:

\[
U_gI_g+U_iI_i
=
S_g-e+P_i+e
\]

otrzymujemy:

\[
\boxed{
S_g'=U_gI_g+U_iI_i-P_i
}
\]

Następnie:

\[
\boxed{
Q_1'=
\sqrt{
S_g'^2-P_g^2
}
}
\]

czyli:

\[
\boxed{
Q_1'=
\sqrt{
\left(
U_gI_g+U_iI_i-P_i
\right)^2
-
P_g^2
}
}
\]

## 6.1. Kompensacja błędów

Dla przykładowego błędu:

\[
U_gI_g=S_g-25
\]

\[
U_iI_i=P_i+25
\]

mamy:

\[
S_g'
=
S_g-25+P_i+25-P_i
\]

\[
\boxed{S_g'=S_g}
\]

Błąd `-25/+25 VA` znika całkowicie.

## 6.2. Test teoretyczny - obciążenie czysto czynne

Założono:

- L1: `P=500 W`,
- L2: `P=800 W`,
- L3: `P=1700 W`,
- `Q=0`.

W stanie bateria/PV bez aktywnego balansowania:

\[
\boxed{Q_1'=0}
\]

dla wszystkich faz.

## 6.3. Test teoretyczny - obciążenie z mocą bierną

Założono:

- L1: `P=500 W`, `Q=250 var`,
- L2: `P=800 W`, `Q=400 var`,
- L3: `P=1700 W`, `Q=850 var`.

Model odzyskuje:

\[
Q_{1,L1}'=250var
\]

\[
Q_{1,L2}'=400var
\]

\[
Q_{1,L3}'=850var
\]

## 6.4. Test rzeczywisty - czajnik

Po wdrożeniu modelu wykonano test czajnika.

Na L1:

- przed: `P≈719 W`, `Q_1'≈402 var`,
- czajnik ON: `P≈2148 W`, `Q_1'≈437 var`.

Zmiana:

\[
\Delta P\approx1429W
\]

\[
\Delta Q'\approx+35var
\]

To był dobry wynik. Duży wzrost mocy czynnej nie powodował już wcześniejszego sztucznego wzrostu `Q'`.

## 6.5. Ograniczenie modelu nr 1

Po wymuszeniu `import + aktywne balansowanie` model przestał działać.

Przykład L2:

\[
P_g\approx356W
\]

\[
P_i\approx-201W
\]

\[
U_gI_g\approx331VA
\]

\[
U_iI_i\approx-230VA
\]

Model nr 1:

\[
S_g'=331-230-(-201)
\]

\[
S_g'\approx302VA
\]

ale:

\[
|P_g|\approx356W
\]

więc:

\[
S_g'<|P_g|
\]

i:

\[
S_g'^2-P_g^2<0
\]

Wniosek:

\[
\boxed{
\text{model nr 1 obowiązuje tylko dla bateria/PV bez aktywnego balansowania}
}
\]

# 7. Znaczenie znaku `Pi`

Przy balansowaniu `Pi` może być ujemne na fazach, z których falownik pobiera moc.

W takim stanie wcześniejsza kompensacja błędów nie zachowuje się tak samo.

Może wystąpić sytuacja efektywnie podobna do:

\[
-e-e=-2e
\]

zamiast:

\[
-e+e=0
\]

Samo zastosowanie modułów:

\[
U_g|I_g|+U_i|I_i|-|P_i|
\]

usuwa część problemu z ujemnym argumentem pierwiastka, ale nie odzyskuje całej mocy biernej.

# 8. Ogólny model fazorowy

Dla dowolnego stanu:

\[
\underline S_g=P_g+jQ_g
\]

\[
\underline S_i=P_i+jQ_i
\]

\[
\underline S_l=\underline S_g+\underline S_i
\]

czyli:

\[
\boxed{P_l=P_g+P_i}
\]

oraz:

\[
\boxed{Q_l=Q_g+Q_i}
\]

Aktywna funkcja kompensacji mocy biernej falownika jest wyłączona.

Falownik może jednak naturalnie generować pewną moc bierną wynikającą ze zwykłej pracy.

Nie można więc uznać:

\[
Q_i=0
\]

za uniwersalne dla wszystkich stanów pracy.

# 9. Model nr 2 - import + aktywne balansowanie

W tym stanie zachodzi charakterystycznie:

\[
\boxed{
P_{g1}\approx P_{g2}\approx P_{g3}>0
}
\]

Dla każdej fazy:

\[
\boxed{
P_i=P_l-P_g
}
\]

Na jednej fazie może wystąpić `Pi<0`, na innej `Pi>0`, mimo prawie takiego samego `Pg`.

## 9.1. Model empiryczno-matematyczny

Z przejścia bateria -> import + balansowanie otrzymano zależność:

\[
\boxed{
A^2=P_g^2+Q^2-kP_gQ
}
\]

gdzie:

\[
A=U_gI_g
\]

Dla trzech faz jednego eksperymentu:

\[
k_1\approx0.727
\]

\[
k_2\approx0.691
\]

\[
k_3\approx0.724
\]

Średnio:

\[
\boxed{k\approx0.714}
\]

`k≈0.714` nie jest jeszcze potwierdzoną stałą falownika. Jest to parametr modelu wyprowadzony z jednego przejścia.

## 9.2. Wyprowadzenie równania nr 2

Start:

\[
A^2=P_g^2+Q^2-kP_gQ
\]

czyli:

\[
Q^2-kP_gQ+P_g^2-A^2=0
\]

Równanie kwadratowe względem `Q`:

\[
\boxed{
Q=
\frac{
kP_g
\pm
\sqrt{
k^2P_g^2-4(P_g^2-A^2)
}
}{2}
}
\]

Po uporządkowaniu:

\[
\boxed{
Q_2'=
\frac{
k|P_g|
\pm
\sqrt{
4(U_gI_g)^2-(4-k^2)P_g^2
}
}{2}
}
\]

dla stanu:

\[
\boxed{
\text{import + aktywne balansowanie}
}
\]

## 9.3. Przykład L1

Dla:

\[
P_g=356W
\]

\[
U_gI_g=427VA
\]

\[
k=0.714
\]

otrzymujemy jedną z gałęzi około:

\[
\boxed{Q_2'\approx395var}
\]

co jest bliskie wartości obserwowanej przed przejściem na balansowanie.

## 9.4. Dwie gałęzie rozwiązania

Równanie daje:

\[
Q_+
\]

oraz:

\[
Q_-
\]

Dla części faz obie wartości mogą być dodatnie.

Przykładowo L2 może dawać około:

\[
163var
\]

lub:

\[
91var
\]

Dlatego potrzebny jest dodatkowy warunek wyboru gałęzi.

Najbardziej naturalny:

\[
\boxed{
Q[k]\text{ powinno zachowywać ciągłość względem }Q[k-1]
}
\]

czyli wybieramy rozwiązanie bliższe ostatniej wiarygodnej wartości `Q`.

# 10. Interpretacja współczynnika `k`

Klasycznie:

\[
S^2=P^2+Q^2
\]

Model balansowania:

\[
A^2=P^2+Q^2-kPQ
\]

można zapisać jako:

\[
A^2=P^2+Q^2+2PQ\cos\theta
\]

stąd:

\[
2\cos\theta=-k
\]

\[
\boxed{
\cos\theta=-\frac{k}{2}
}
\]

Dla:

\[
k=0.714
\]

otrzymujemy:

\[
\theta\approx111^\circ
\]

Nie jest to interpretowane jako rzeczywisty kąt fazowy prądu. To jedynie matematyczny opis zachowania rejestru `Ig`.

# 11. Obecny podział na stany pracy

## Stan 1 - bateria / PV bez aktywnego balansowania

Wzór:

\[
\boxed{
S_g'=U_gI_g+U_iI_i-P_i
}
\]

\[
\boxed{
Q_1'=
\sqrt{
S_g'^2-P_g^2
}
}
\]

## Stan 2 - import + aktywne balansowanie

Warunki charakterystyczne:

\[
P_{g1}\approx P_{g2}\approx P_{g3}>0
\]

oraz typowo:

- co najmniej jedna faza ma `Pi<0`,
- co najmniej jedna faza ma `Pi>0`.

Kandydat:

\[
\boxed{
Q_2'=
\frac{
k|P_g|
\pm
\sqrt{
4(U_gI_g)^2-(4-k^2)P_g^2
}
}{2}
}
\]

z roboczym:

\[
\boxed{k\approx0.714}
\]

## Stan 3 - do opracowania

Trzeci model pozostaje do opracowania.

Prawdopodobny przypadek:

- eksport z aktywnym balansowaniem,
- albo inny stan przepływu, w którym model 1 i model 2 nie obowiązują.

Na tym etapie nie należy wymuszać jednego uniwersalnego równania.

# 12. Próbki przejściowe

Podczas przełączania trybu pracy falownik aktywnie zmienia rozdział mocy czynnej.

W bardzo krótkich oknach czasowych:

- `Pg`,
- `Pi`,
- `Ig`,
- `Ii`

mogą reprezentować różne chwile procesu regulacyjnego.

Powstają wtedy:

- szpilki,
- krótkie wahania,
- ujemne marginesy,
- pozornie niefizyczne wyniki.

Nie należy traktować ich jako błędu wzoru.

Do walidacji używa się stabilnych odcinków po zakończeniu regulacji.

# 13. Co zostało potwierdzone

## Bardzo dobrze potwierdzone

\[
\boxed{P_l=P_g+P_i}
\]

## Potwierdzone dla bateria/PV bez balansowania

\[
\boxed{
Q_1'=
\sqrt{
(U_gI_g+U_iI_i-P_i)^2-P_g^2
}
}
\]

Model przeszedł:

- testy teoretyczne,
- test kompensacji `-25/+25 VA`,
- test rzeczywistego obciążenia rezystancyjnego czajnikiem.

## Odrzucone jako uniwersalne

\[
S'=U_gI_g+U_iI_i+2\min(P_g,0)
\]

oraz użycie tego `S'` jako całkowitej mocy pozornej Load.

## Odrzucone jako uniwersalne

\[
Q_i=0
\]

dla każdego stanu pracy.

# 14. Co nadal wymaga sprawdzenia

1. Czy `k≈0.714` pozostaje podobne przy innych poziomach obciążenia.
2. Czy `k` jest wspólne dla wszystkich faz.
3. Czy `k` zależy od `Pg`.
4. Czy `k` zależy od znaku `Pi`.
5. Jak najlepiej wybierać gałąź `Q_+` / `Q_-`.
6. Czy model nr 2 działa dla długiego stabilnego import + balansowanie.
7. Opracowanie stanu nr 3.
8. Test eksportu z aktywnym balansowaniem.
9. Test z odbiornikiem o znanej dużej mocy biernej.

# 15. Aktualna strategia implementacji

1. Rozpoznać aktualny stan pracy falownika.
2. Dla stanu 1 używać `Q1'`.
3. Dla import + balansowanie używać `Q2'`.
4. Odrzucać próbki przejściowe.
5. Zachowywać ostatnią wiarygodną wartość `Q` jako pomoc przy wyborze gałęzi.
6. Nie tworzyć jednego uniwersalnego równania na siłę.
7. Dopiero po zebraniu kolejnych testów opracować stan nr 3.

# 16. Najważniejsze wzory

## Bilans mocy czynnej

\[
\boxed{P_l=P_g+P_i}
\]

## Stan 1

\[
\boxed{
S_g'=U_gI_g+U_iI_i-P_i
}
\]

\[
\boxed{
Q_1'=
\sqrt{
S_g'^2-P_g^2
}
}
\]

## Stan 2

\[
\boxed{
(U_gI_g)^2=P_g^2+Q^2-kP_gQ
}
\]

\[
\boxed{
Q_2'=
\frac{
k|P_g|
\pm
\sqrt{
4(U_gI_g)^2-(4-k^2)P_g^2
}
}{2}
}
\]

Roboczo:

\[
\boxed{k\approx0.714}
\]

## Suma trzech faz

Jeżeli znak `Q` jest taki sam na wszystkich fazach:

\[
\boxed{
Q_{total}=Q_1+Q_2+Q_3
}
\]

Jeżeli znaki `Q` mogą być różne, sam moduł nie wystarcza do poprawnego sumowania.

# 17. Status

- Model 1 - działa i jest potwierdzony dla bateria/PV bez aktywnego balansowania.
- Model 2 - kandydat matematyczny dla import + balansowanie.
- Model 3 - nieopracowany.
- Uniwersalny model - obecnie nie jest celem.
- Priorytet - dalsza identyfikacja modelu nr 2 na kolejnych stabilnych przejściach.
