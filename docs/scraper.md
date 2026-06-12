
# scraper.py

aici sunt colectate cookie urile si alte resurse externe relevante

selenium pt a deschide pagina web 

exista 2 tipuri de analize: inainte de consent si dupa consent 

## functii

- universal_cookie_accept → detecteaza si apasa butonul de accept
- get_cookies → colecteaza cookies post consent
- scan_preconsent → colecteaza cookies inainte de orice interactiune ( pentru partea de gdpr audit )
- extract_external_resources → extrage iframe, img, script din html ul paginii scanate

universal_cookie_accept() 

- incearca sa gaseasca si sa apese butonul de accept din banner cookies

scan_preconsent() 

- analiza preconsent
- deschide fiecare pagian fara sa accepte bannerul si fara cookies salvate anterior ( chrome clean )
- colecteaza cookies setate automat
- colecteaza resurse externe iframe, script, img din html → astea se executa automat si cookie urile vor fi implicit → third party fara consent

niciun cookie non esential nu ar trebui sa existe inainte de consent 

extract_external_resources()

- extrage toate resursele externe dintr o pagina html
- cauta iframe, src, img
- verifica daca domeniul este extern si daca e un tracker cunoscut
    
    resursele astea se incarca automat. fac request uri http catre domeniile externe si pot seta cookies, colecta date, face fingerprinting
    
    este nevoie de consent pt asta 
    

returneaza o lista care contine resursa externa: 

"tag":         "iframe" / "script" ; pot fi adaugate si  "img" / "link" ? 

"src":         URL-ul resursei,

"domain":      domeniul extern,

"category_id": 2 (Analytics) sau 3 (Marketing) sau -1 (necunoscut),

"category":    "Analytics" / "Marketing" / "Unknown",

"tracker":     numele trackerului sau None,

"risk":        "high" ; pentru img si link ? / "medium" / "low",
