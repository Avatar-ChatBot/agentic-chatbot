import cloudscraper
scraper = cloudscraper.create_scraper()
response = scraper.get("https://peraturan.bpk.go.id/Jenis")
print(response.text)
print(response.status_code)