#!/bin/bash

# ./run.sh https://site.ro
# ./run.sh https://site.ro --max-pages 10
# ./run.sh https://site.ro --max-pages 5 --output raport_custom.html

if [ -z "$1" ]; then
    echo "Eroare: Introdu URL."
    echo "Utilizare: ./run.sh https://exemplu.com"
    exit 1
fi

# ne asiguram ca suntem in directorul proiectului
cd "$(dirname "$0")"

# activam venv daca exista
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "Pornire scanare pentru: $1"

# transmitem TOȚI parametrii mai departe către main.py
# $@ = toate argumentele date lui run.sh
python3 main.py "$@"