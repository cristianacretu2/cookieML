# features.py

transforma datele legate de cookie in numere care pot fi intelese de ml. modelul nu intelege text. numere = features. cu cat mai multe cu atat mai bine 

biblioteci → math pt calcul entropie
                     re pt expresii regulate 

### functii

- get_clean_domain → `"https://magazin.ro/produse"`  in `"magazin.ro"`
- is_third_party → verifica daca e acelasi domeniu
- value_enthropy → calculeaza entropia (”dezordinea”) unui cookie. cat de random este valoarea cookie ului. entropie mare indica tracking. formula folosita shannon entropy
- name_pattern_score → cauta pattern uri cunoscute. returneaza categoria sau -1 daca nu gaseste in datele predefinite
- domain_reputation_score → returneaza categoria daca recunoaste domeniul printre cele cunoscute, -1 altfel
- parse_duration_days → returneaza nr de zile pana la expirare
- combine_features → ia un cookie si returneaza o lista cu 14 valori, features urile

`Aceasta e funcția pe care o apelează train.py și predict.py.Modelul ML primește întotdeauna exact 14 numere în aceeași ordine.IMPORTANT: Ordinea și numărul features-urilor TREBUIE să fie identicela antrenament și la predicție. Dacă schimbi ceva aici, re-antrenează modelul!Parametri:  cookie   - dicționar cu datele cookie-ului (name, domain, value, etc.)  site_url - URL-ul site-ului scanat (pentru a detecta third-party)`