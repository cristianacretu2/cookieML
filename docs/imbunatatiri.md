# imbunatatiri

la elementele html nu am facut complet ok. sunt luate toate, ceea ce nu este ok din urmatoarele motive: 

- daca primul <script> este unul de la cookiepro, onetrust etc, acesta este un script special care blocheaza toate scripturile, iframe urile urmatoare pentru a nu lua date inainte de consent. asta este una din variante de a respecta politicile gdpr. in momentul in care este acceptat bannerul, scriptul este dezactivat. in cazul in care exista scripturi de la google de ex inainte de acest script, atunci este incalcare ptc browserul il incarca inainte de scriptul de la cookiepro
- o alta varianta de a respecta politica gdpr este de a face scriptul text/plain si a adauga o clasa la element. in momentul in care bannerul este acceptat, prin clasa se schimba din text/plain in text/javascript si este rulat scriptul.
-