# predict.py

face clasificare cookie ului pe baza modelului 

functii 

- predict_cookie
    - clasifica un cookie si returneaza categoria si nivelul de incredere
    1. verificare in known_cookies → 2. daca nu stim din lista predefinita, folosim ml ul. proba_predict 
- predict_batch
    - clasifica o lista de cookies mai eficient ( o singura trecere prin ml )
    - returneaza o lista de tuplu ( cat_id, confidence, cat_name, metoda )