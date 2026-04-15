#!/bin/bash

# rulam asta cand vrem sa verificam site
# ./run.sh site

if [ -z "$1" ]
then
      echo "Eroare: Introdu URL."
      echo "Utilizare: ./run.sh https://exemplu.com"
      exit 1
fi

URL=$1

echo " Pornire scanare pentru: $URL"

python3 << END
import sys
from src.analyzer import analyze_site
import json

try:
    results = analyze_site("$URL")
    print("\n--- REZULTATE SCANARE ---")
    print(json.dumps(results, indent=4))
    print("-------------------------\n")
    print(f" Scanare finalizată. Am găsit {len(results)} cookie-uri.")
except Exception as e:
    print(f" A apărut o eroare la scanare: {e}")
END