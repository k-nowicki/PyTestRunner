## Opis Narzędzia: Izolowany Runner Skryptów Python (`py_test_runner`)

### 1. Podsumowanie

`py_test_runner` to narzędzie wiersza poleceń (CLI), które umożliwia uruchamianie skryptów w języku Python w całkowicie odizolowanym, czystym i powtarzalnym środowisku. Wykorzystuje ono technologię kontenerów Docker do stworzenia efemerycznego (tymczasowego) środowiska wykonawczego dla każdego uruchomienia, gwarantując, że skrypt zawsze działa w tych samych warunkach, niezależnie od maszyny, na której jest uruchamiany.

Narzędzie rozwiązuje fundamentalny problem "u mnie działa", eliminując wpływ konfiguracji maszyny hosta, zainstalowanych globalnie bibliotek czy pozostałości po poprzednich uruchomieniach.

### 2. Koncepcja działania

Użytkownik wywołuje `py_test_runner` z terminala, podając **dwa obowiązkowe argumenty**: ścieżkę do skryptu Python do wykonania (`--script`) oraz ścieżkę do pliku `requirements.txt` definiującego jego zależności (`--reqs`). Opcjonalnie można również podać listę dodatkowych plików wejściowych.

Narzędzie w tle wykonuje następujące kroki:

1.  **Przygotowanie Kontekstu:** Tworzy tymczasowy, bezpieczny katalog na maszynie hosta.
2.  **Agregacja Plików:** Kopiuje do tego katalogu skrypt użytkownika, plik `requirements.txt` oraz wszystkie opcjonalne pliki wejściowe.
3.  **Uruchomienie Kontenera:** Uruchamia kontener Docker z predefiniowanego, lekkiego obrazu zawierającego Pythona. Katalog tymczasowy jest montowany wewnątrz kontenera jako wolumen, zapewniając dostęp do plików.
4.  **Wykonanie w Izolacji:** Wewnątrz kontenera, narzędzie automatycznie:
    a. Tworzy nowe, czyste środowisko wirtualne (`venv`).
    b. Instaluje w nim biblioteki z pliku `requirements.txt`.
    c. Uruchamia właściwy skrypt użytkownika.
5.  **Przekazanie Wyników:** Skrypt użytkownika, po wykonaniu swojej logiki, zapisuje plik wynikowy (o ustalonej nazwie, np. `output.txt`) w swoim katalogu roboczym. Dzięki mechanizmowi wolumenów, plik ten natychmiast pojawia się w katalogu tymczasowym na maszynie hosta.
6.  **Sprzątanie:** Po zakończeniu pracy kontenera, narzędzie kopiuje plik wynikowy z katalogu tymczasowego do finalnej lokalizacji, a następnie bezpowrotnie usuwa zarówno kontener Docker, jak i cały katalog tymczasowy wraz z jego zawartością (venv, pobrane biblioteki itp.).

Dzięki temu procesowi, jedynymi artefaktami pozostającymi na maszynie hosta są pliki wejściowe i ostateczny plik wynikowy.

### 3. Przykład użycia

```bash
python py_test_runner.py \
    --script ./moje_skrypty/analiza.py \
    --reqs ./moje_skrypty/requirements.txt \
    --inputs ./dane/zbior_danych.csv ./konfiguracja/model.json
```

---

### 4. Lista Wymagań Funkcjonalnych i Niefunkcjonalnych

#### Wymagania Funkcjonalne (Co narzędzie musi robić)

| ID   | Wymaganie                                                                                                |
| :--- | :------------------------------------------------------------------------------------------------------- |
| **F1**   | Narzędzie **musi** akceptować jako argumenty wiersza poleceń dwie obowiązkowe ścieżki: do skryptu Python (`--script`) oraz do pliku `requirements.txt` (`--reqs`). |
| **F2**   | Narzędzie **musi** umożliwiać przekazanie opcjonalnej listy ścieżek do dodatkowych plików wejściowych (`--inputs`), które będą dostępne dla wykonywanego skryptu. |
| **F3**   | Cały proces wykonania skryptu (instalacja zależności i uruchomienie) **musi** odbywać się wewnątrz kontenera Docker, bazującego na obrazie zawierającym system Linux i środowisko Python. |
| **F4**   | Wewnątrz kontenera, przed instalacją zależności, **musi** zostać utworzone nowe, puste środowisko wirtualne Python (`venv`). |
| **F5**   | Zależności zdefiniowane w pliku podanym w argumencie `--reqs` **muszą** zostać zainstalowane w stworzonym środowisku wirtualnym przy użyciu `pip`. |
| **F6**   | Po zainstalowaniu zależności, skrypt podany w argumencie `--script` **musi** zostać wykonany. |
| **F7**   | Narzędzie **musi** umożliwiać przekazanie jednego pliku wynikowego (o predefiniowanej nazwie `output.txt`) z kontenera z powrotem na maszynę hosta, do katalogu, z którego zostało uruchomione. |

#### Wymagania Niefunkcjonalne (Jak narzędzie musi się zachowywać)

| ID   | Wymaganie                                                                                                |
| :--- | :------------------------------------------------------------------------------------------------------- |
| **NF1**  | Narzędzie **musi** po zakończeniu swojej pracy automatycznie usunąć wszystkie stworzone przez siebie zasoby tymczasowe, w tym kontener Docker oraz lokalny katalog kontekstu. |
| **NF2**  | W przypadku pomyślnego wykonania całego procesu, narzędzie **musi** zakończyć działanie z kodem wyjścia `0`. |
| **NF3**  | W przypadku wystąpienia jakiegokolwiek błędu na dowolnym etapie (np. brak pliku, błąd instalacji `pip`, błąd w skrypcie użytkownika, problem z Dockerem), narzędzie **musi** zakończyć działanie z kodem wyjścia różnym od zera (np. `1`). |
| **NF4**  | Wszystkie komunikaty o błędach **muszą** być drukowane na standardowe wyjście błędów (`stderr`) w spójnym, zwięzłym formacie. |
| **NF5**  | Logi z procesu wykonania wewnątrz kontenera (wyjście `stdout` i `stderr` z `pip install` oraz uruchomionego skryptu) **muszą** być przekazywane na standardowe wyjście (`stdout`) narzędzia `py_test_runner`, aby umożliwić użytkownikowi śledzenie postępów. |
| **NF6**  | Narzędzie **musi** posiadać minimalne zależności po stronie hosta: zainstalowany Python oraz działający demon Dockera. |