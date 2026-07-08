"""
İdefix Ürün Scraper (Selenium versiyonu)
------------------------------------------
Gerçek bir Chrome tarayıcısını arka planda açıp sayfayı yükler,
bu sayede bot korumasını ve JS render'ı aşar.

Kurulum (gerekliyse):
    pip install selenium webdriver-manager beautifulsoup4 pandas

Çalıştırma:
    python idefix_scraper.py

Çıktı:
    idefix_urunler.csv
"""

import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

CATEGORIES = {
    "Ödüllü Kitaplar": "https://www.idefix.com/odullu-kitaplar-l-252",
    "Öne Çıkan Kitaplar": "https://www.idefix.com/one-cikan-kitaplar-l-184",
    "Pulitzer Ödüllü Kitaplar": "https://www.idefix.com/pulitzer-odullu-kitaplar-l-956",
}


def clean_price(text):
    match = re.search(r"([\d\.]+,\d{2})\s*TL", text)
    if not match:
        return None
    number = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(number)
    except ValueError:
        return None


def extract_products(html, category_name):
    soup = BeautifulSoup(html, "html.parser")
    product_links = soup.find_all("a", href=re.compile(r"-p-\d+"))

    seen_hrefs = set()
    products = []

    for link in product_links:
        href = link.get("href")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        container = link
        h3 = None
        for _ in range(6):
            if container is None:
                break
            container = container.parent
            if container is not None:
                h3 = container.find("h3")
                if h3:
                    break

        if not h3:
            continue

        title_raw = h3.get_text(strip=True)
        text = container.get_text( separator=" ")
        price_matches = re.findall(r"[\d\.]+,\d{2}\s*TL", text)

        if not price_matches:
            continue

        list_price = clean_price(price_matches[0])
        discount_price = clean_price(price_matches[1]) if len(price_matches) > 1 else list_price

        parts = title_raw.split(" - ")
        brand = parts[-1] if len(parts) > 1 else None

        full_url = "https://www.idefix.com" + href if href.startswith("/") else href

        products.append({
            "kategori": category_name,
            "urun_adi": title_raw,
            "marka_yayinevi": brand,
            "liste_fiyat_tl": list_price,
            "indirimli_fiyat_tl": discount_price,
            "url": full_url,
        })

    return products


def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def main():
    driver = build_driver()
    all_products = []

    try:
        for name, url in CATEGORIES.items():
            print(f"-> Çekiliyor: {name} ({url})")
            try:
                driver.get(url)
                time.sleep(4)
                html = driver.page_source
                found = extract_products(html, name)
                print(f"   {len(found)} ürün bulundu.")
                all_products.extend(found)
            except Exception as e:
                print(f"   HATA ({name}): {e}")
            time.sleep(2)
    finally:
        driver.quit()

    df = pd.DataFrame(all_products)
    if not df.empty:
        df = df.drop_duplicates(subset=["urun_adi", "liste_fiyat_tl"])
    df.to_csv("idefix_urunler.csv", index=False, encoding="utf-8-sig")
    print(f"\nToplam {len(df)} ürün kaydedildi -> idefix_urunler.csv")


if __name__ == "__main__":
    main()
