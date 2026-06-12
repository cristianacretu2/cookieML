#!/bin/bash


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

# transmitem toti parametrii catre main
# $@ = toate argumentele date lui run.sh
python3 main.py "$@"