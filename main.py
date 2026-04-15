from src.analyzer import analyze_site

url = input("Enter URL: ")

results = analyze_site(url)

print("\nResults:\n")

for cookie, category in results.items():
    print(f"{cookie} → {category}")
