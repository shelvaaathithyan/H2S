import os
import time
import re
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://www.mosdac.gov.in/"

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_internal_links(driver, url):
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/") or (BASE_URL in href):
            full_url = href if "http" in href else BASE_URL.rstrip("/") + "/" + href.lstrip("/")
            if BASE_URL in full_url:
                links.add(full_url.split("#")[0])
    return list(links)

def detect_source_type(url):
    keywords = {
        "forecast": "Forecast",
        "nowcast": "Nowcast",
        "alert": "Alerts",
        "ocean": "Ocean",
        "cyclone": "Cyclone",
        "monsoon": "Monsoon",
        "weather": "Weather",
        "energy": "Energy",
        "rainfall": "Rainfall",
        "data": "Data",
        "archive": "Archive",
        "announcement": "Announcement",
        "satellite": "Satellite"
    }
    for k, v in keywords.items():
        if k in url.lower():
            return v
    return "General"

def extract_clean_text(driver, url):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    title = soup.title.string.strip() if soup.title else "Untitled Page"
    source_type = detect_source_type(url)
    clean_data = []

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(strip=True)
        if text and len(text.split()) > 5:
            clean_data.append({
                "Page Title": title,
                "Page URL": url,
                "Source Type": source_type,
                "Section Type": tag.name.upper(),
                "Text Content": text
            })

    return clean_data

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:50]

def main():
    driver = setup_driver()
    visited = set()
    links_to_scrape = get_internal_links(driver, BASE_URL)
    print(f"🔍 Found {len(links_to_scrape)} internal pages.")

    for url in links_to_scrape:
        if url in visited:
            continue
        visited.add(url)
        print(f"🧭 Scraping: {url}")
        try:
            content = extract_clean_text(driver, url)
            if content:
                filename = sanitize_filename(url.replace(BASE_URL, "").strip("/")) or "homepage"
                df = pd.DataFrame(content)
                df.to_csv(f"{filename}_text.csv", index=False)
                print(f"✅ Saved: {filename}_text.csv")
        except Exception as e:
            print(f"⚠️ Error scraping {url}: {e}")

    driver.quit()
    print("🎉 Done.")

if __name__ == "__main__":
    main()
