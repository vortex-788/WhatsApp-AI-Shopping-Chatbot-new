import requests, csv, os

# 1-MIN GOOGLE SHEET (zero keys) – best alternative to WooCommerce
SHEET_CSV = os.getenv("SHEET_CSV")  # publish-to-web link

def fetch_sheet():
    """Google Sheet → CSV → products (zero keys, 1-min setup)"""
    if not SHEET_CSV: return []
    resp = requests.get(SHEET_CSV)
    resp.encoding = 'utf-8'
    return list(csv.DictReader(resp.text.splitlines()))

def fetch_google_shopping(query):
    GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
    if not GOOGLE_KEY: return []
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_KEY}&cx={GOOGLE_CSE_ID}&num=5"
    resp = requests.get(url).json()
    prods = []
    for item in resp.get("items", []):
        if "₹" in item["title"]:
            try:
                price = int(item["title"].split("₹")[1].split()[0].replace(",", ""))
                prods.append({
                    "id": item["cacheId"][:10],
                    "name": item["title"][:70],
                    "price": price,
                    "stock": 999,
                    "image": item.get("pagemap", {}).get("cse_image", [{}])[0].get("src", ""),
                    "vendor": "google"
                })
            except: pass
    return prods

def refresh_products():
    google = fetch_google_shopping("sneakers")
    sheet = fetch_sheet()
    merged = google + sheet
    return merged
