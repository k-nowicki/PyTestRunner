# TODO.md

Ten plik opisuje plan implementacji narzędzia `py_test_runner.py`, które uruchamia skrypty Pythona w izolowanym środowisku Docker. Plan ten uwzględnia ujednoliconą obsługę błędów oraz dokumentuje znane ograniczenia.

**Struktura plików testowych (do stworzenia przed Krokiem 6):**
```
test_assets/
├── inputs/
│   └── data.csv
├── reqs/
│   ├── empty_reqs.txt
│   └── faulty_reqs.txt
└── scripts/
    ├── create_output.py
    ├── never_creates_output.py
    ├── read_input.py
    └── simple_print.py
```

## Plan Implementacji

- [x] **Krok 1: Inicjalizacja projektu i obsługa argumentów CLI**
- [x] **Krok 2: Ujednolicona obsługa błędów i kody wyjścia**
- [x] **Krok 3: Przygotowanie tymczasowego kontekstu wykonania**
- [ ] **Krok 4: Podstawowa integracja z Dockerem - uruchomienie testowego kontenera**
- [ ] **Krok 5: Połączenie kontekstu i Dockera - montowanie wolumenu**
- [ ] **Krok 6: Wykonanie pełnej sekwencji poleceń w kontenerze**
- [ ] **Krok 7: Przechwytywanie pliku wynikowego**
- [ ] **Krok 8: Obsługa dodatkowych plików wejściowych**

---

### [x] Krok 1: Inicjalizacja projektu i obsługa argumentów CLI

**Zadanie:** Stworzenie podstawowej struktury projektu i zaimplementowanie parsowania argumentów z linii poleceń.

**Implementacja w `py_test_runner.py`:**
*   Użyj modułu `argparse` do dodania wymaganych argumentów: `--script` i `--reqs`.
*   Po sparsowaniu, skrypt ma wydrukować wartości argumentów i zakończyć działanie.

**Jak testować:**
1.  Stwórz puste pliki `touch placeholder_script.py placeholder_reqs.txt`.
2.  Uruchom: `python py_test_runner.py --script placeholder_script.py --reqs placeholder_reqs.txt`
    *   **Oczekiwany rezultat:** Skrypt wypisze ścieżki do obu plików i zakończy się bez błędu.
3.  Uruchom: `python py_test_runner.py`
    *   **Oczekiwany rezultat:** `argparse` wyświetli błąd o brakujących argumentach.

---

### [x] Krok 2: Ujednolicona obsługa błędów i kody wyjścia

**Zadanie:** Opakowanie głównej logiki skryptu w blok `try...except` oraz zdefiniowanie spójnego sposobu raportowania błędów i używania kodów wyjścia (exit codes).

**Implementacja w `py_test_runner.py`:**
*   Całą logikę skryptu (poza importami i definicjami) umieść w funkcji `main()`.
*   Na końcu pliku umieść standardowy blok `if __name__ == "__main__":`.
*   Wewnątrz `if __name__ == "__main__":`, opakuj wywołanie `main()` w blok `try...except Exception as e:`.
*   W przypadku sukcesu (`main()` zakończy się bez wyjątku), skrypt powinien zakończyć się z kodem `0` (`sys.exit(0)`).
*   W przypadku każdego złapanego wyjątku, skrypt powinien:
    1.  Wydrukować na `stderr` zwięzły komunikat błędu, np. `ERROR: <treść wyjątku>`.
    2.  Zakończyć działanie z kodem `1` (`sys.exit(1)`).
*   Dodaj walidację istnienia plików podanych w `--script` i `--reqs` na samym początku `main()`. Jeśli plik nie istnieje, rzuć `FileNotFoundError` z odpowiednim komunikatem.

**Jak testować:**
1.  Uruchom `python py_test_runner.py --script placeholder_script.py --reqs placeholder_reqs.txt` (pliki muszą istnieć).
    *   **Oczekiwany rezultat:** Skrypt kończy się w ciszy z kodem `0`. W terminalu zweryfikuj kod wyjścia (np. w bash: `echo $?` powinno dać `0`).
2.  Uruchom `python py_test_runner.py --script non_existent_script.py --reqs placeholder_reqs.txt`.
    *   **Oczekiwany rezultat:** Na `stderr` pojawia się komunikat o błędzie, np. `ERROR: File not found: non_existent_script.py`. Skrypt kończy się z kodem `1` (sprawdź `echo $?`).

---

### [x] Krok 3: Przygotowanie tymczasowego kontekstu wykonania

**Zadanie:** Rozbudowanie `runner.py` o tworzenie tymczasowego katalogu i kopiowanie do niego plików.

**Implementacja w `runner.py`:**
*   Użyj `tempfile.TemporaryDirectory` i `shutil.copy`.
*   Dodaj `input("Press Enter...")` przed końcem bloku `with`, aby umożliwić inspekcję na czas testów.

**Jak testować:**
1.  Uruchom: `python py_test_runner.py --script placeholder_script.py --reqs placeholder_reqs.txt`
2.  **Oczekiwany rezultat:** Skrypt wypisze ścieżkę do katalogu tymczasowego, zatrzyma się, a po naciśnięciu Enter usunie katalog i zakończy się z kodem `0`.

---

### [ ] Krok 4: Podstawowa integracja z Dockerem - uruchomienie testowego kontenera

**Zadanie:** Dodanie logiki do uruchomienia prostego kontenera.

**Implementacja w `runner.py`:**
*   Dodaj `docker` do `requirements.txt`.
*   Użyj biblioteki `docker` do uruchomienia kontenera z `python:3.10-slim` z poleceniem `echo "Hello from Docker"`. Ustaw `auto_remove=True`.
*   Dodaj obsługę `docker.errors.DockerException` w bloku `try...except`, aby raportować błąd w ujednolicony sposób.

**Jak testować:**
1.  Z uruchomionym Dockerem: `python py_test_runner.py --script placeholder_script.py --reqs placeholder_reqs.txt`.
    *   **Oczekiwany rezultat:** W logach na konsoli pojawi się `Hello from Docker`, kod wyjścia `0`.
2.  Z zatrzymanym demonem Dockera: `python py_test_runner.py --script placeholder_script.py --reqs placeholder_reqs.txt`.
    *   **Oczekiwany rezultat:** Komunikat błędu na `stderr` (np. `ERROR: Could not connect to Docker daemon.`), kod wyjścia `1`.

---

### [ ] Krok 5: Połączenie kontekstu i Dockera - montowanie wolumenu

**Zadanie:** Połączenie logiki z poprzednich kroków: montowanie tymczasowego kontekstu jako wolumen w kontenerze.

**Implementacja w `runner.py`:**
*   W logice uruchamiania kontenera dodaj parametry `volumes` (mapowanie na `/app`) i `working_dir='/app'`.
*   Zmień polecenie wykonywane w kontenerze na `ls -la /app`.

**Jak testować:**
1.  Uruchom: `python py_test_runner.py --script placeholder_script.py --reqs placeholder_reqs.txt`
2.  **Oczekiwany rezultat:** W logach z kontenera pojawi się listowanie plików, a na nim `placeholder_script.py` i `placeholder_reqs.txt`. Kod wyjścia `0`.

---

### [ ] Krok 6: Wykonanie pełnej sekwencji poleceń w kontenerze

**Zadanie:** Zaimplementowanie głównej logiki: venv, instalacja zależności i uruchomienie skryptu.

**Implementacja w `runner.py`:**
*   Zbuduj i przekaż do kontenera złożone polecenie `sh -c "..."`.
*   Dodaj obsługę `docker.errors.ContainerError`. Ten wyjątek jest rzucany, gdy kontener kończy pracę z niezerowym kodem wyjścia. W komunikacie błędu należy zawrzeć logi z kontenera.

**Jak testować:**
1.  Test sukcesu: Uruchom `runner` z `test_assets/scripts/simple_print.py` i `test_assets/reqs/empty_reqs.txt`.
    *   **Oczekiwany rezultat:** Na końcu logów komunikat: `Script executed successfully!`, kod wyjścia `0`.
2.  Test błędu: Uruchom `runner` z `test_assets/reqs/faulty_reqs.txt` (zawierającym `non-existent-package-123`).
    *   **Oczekiwany rezultat:** Komunikat błędu na `stderr` zawierający logi z `pip`. Kod wyjścia `1`.

---

### [ ] Krok 7: Przechwytywanie pliku wynikowego

**Zadanie:** Umożliwienie skryptowi docelowemu tworzenia pliku wynikowego i udostępnianie go na zewnątrz.

**Implementacja w `runner.py`:**
*   Po zakończeniu pracy kontenera, sprawdź istnienie i skopiuj plik `output.txt` z katalogu tymczasowego do bieżącego katalogu roboczego.
*   Jeśli plik `output.txt` nie istnieje po wykonaniu, rzuć wyjątek.

**Jak testować:**
1.  Test sukcesu: Uruchom `runner` z `test_assets/scripts/create_output.py`.
    *   **Oczekiwany rezultat:** Plik `output.txt` jest tworzony, kod wyjścia `0`.
2.  Test błędu: Uruchom `runner` z `test_assets/scripts/never_creates_output.py`.
    *   **Oczekiwany rezultat:** Komunikat błędu na `stderr` (np. `ERROR: Output file 'output.txt' not found after execution.`). Kod wyjścia `1`.

---

### [ ] Krok 8: Obsługa dodatkowych plików wejściowych

**Zadanie:** Rozszerzenie funkcjonalności o przekazywanie dodatkowych plików wejściowych.

**Implementacja w `runner.py`:**
*   Zmodyfikuj `argparse`, dodając opcjonalny argument `--inputs` (`nargs='+'`).
*   Rozszerz logikę kopiowania plików o te z listy `--inputs`.

**Jak testować:**
1.  Uruchom `runner` ze skryptem `test_assets/scripts/read_input.py` i argumentem `--inputs test_assets/inputs/data.csv`.
2.  **Oczekiwany rezultat:** W katalogu roboczym powstaje plik `output.txt`, którego zawartość jest identyczna z zawartością `data.csv`. Kod wyjścia `0`.

---

## Znane ograniczenia i przypadki brzegowe

1.  **Zależności systemowe:** Narzędzie używa bazowego obrazu `python:3.10-slim`. Jeśli instalacja pakietu z `requirements.txt` wymaga bibliotek systemowych lub narzędzi do kompilacji (np. `gcc`), instalacja `pip` zakończy się błędem. Narzędzie poprawnie zgłosi błąd, ale nie rozwiąże go automatycznie. Użytkownik jest odpowiedzialny za dostarczenie `requirements.txt` kompatybilnego z tym środowiskiem.

2.  **Konflikty nazw plików:** Wszystkie pliki wejściowe (`--script`, `--reqs`, `--inputs`) są kopiowane do jednego, płaskiego katalogu wewnątrz kontenera. Jeśli dwa pliki z różnych lokalizacji źródłowych mają tę samą nazwę, jeden z nich zostanie nadpisany bez ostrzeżenia. Użytkownik jest odpowiedzialny za zapewnienie unikalności nazw plików bazowych.

3.  **Stała nazwa pliku wynikowego:** Obecna implementacja zakłada, że plik wynikowy zawsze nazywa się `output.txt`. Nazwa ta jest na stałe wpisana w kod `runner.py`. W przyszłości można to rozszerzyć o dodatkowy argument CLI.

4.  **Brak obsługi katalogów wejściowych:** Argument `--inputs` akceptuje tylko ścieżki do plików. Próba przekazania katalogu spowoduje błąd podczas operacji kopiowania.

5.  **Dostęp do sieci:** Kontener domyślnie ma dostęp do sieci, co pozwala `pip` na pobieranie pakietów. Jeśli skrypt docelowy wymaga specyficznej konfiguracji sieciowej (lub jej braku), obecne narzędzie tego nie obsługuje.
