#!/bin/bash

# rulam asta doar cand actualizam datasetul

# oprim scriptul daca apare o eroare
set -e

echo " --- Se incepe antrenarea modelului --- "

# antrenare model
echo " Antrenare model Machine Learning "
python3 src/train.py