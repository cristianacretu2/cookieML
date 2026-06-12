# analyzer.py

Analizeaza toate cookie urile de pe site.

Primeste cookie uri colectate de pe mai multe site uri → deduplicare → analizare, pune in categorii → scor GDPR.

## functii

- deduplicate_cookies → returneaza toate cookie urile unice. criteriu: name, domain
- calculate_gdpr_risk → calculeaza scor gdpr
- gdpr_verdict → returneaza un raspuns final bazat pe scor + recomandari ( ceva simplu )
- analyze_site → functia principala
- format_lifespan → functie pt vizualizare a datei de expirare
- calculate_stats → pentru interfata
- analyze_preconsent → analizeaza inainte de consent
- compare_analyses → compara cele 2 analize

### pentru scor

- scorul este intre 0 - 100
- 0-30 → scazut; 31-60 → mediu; 61-100 → ridicat
- logica de sco
    - marketing third party -15
    - marketing first party -8
    - analytics third party -5
    - analytics first party -2
    - preferences -1
    - daca are cookie consent → bonus 10