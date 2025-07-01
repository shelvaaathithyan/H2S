import os
import time
import csv
import re
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse
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
                links.add(full_url.split("#")[0])  # remove anchors
    return list(links)

def detect_source_type(url):
    keywords = {
        "forecast": "Forecast",
        "nowcast": "Nowcast",
        "alert": "Alerts",
        "ocean": "Ocean Applications",
        "cyclone": "Cyclone",
        "monsoon": "Monsoon",
        "weather": "Weather",
        "energy": "Energy",
        "rainfall": "Rainfall",
        "data": "Dataset",
        "archive": "Archive",
        "announcement": "Announcement",
        "satellite": "Satellite"
    }
    for k, v in keywords.items():
        if k in url.lower():
            return v
    return "General"

def extract_content(driver, url):
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    title = soup.title.string.strip() if soup.title else "Untitled Page"
    data = []

    # Extract Text
    for tag in soup.find_all(["h1", "h2", "h3", "p", "div", "span"]):
        text = tag.get_text(strip=True)
        if text and len(text) > 30:
            data.append({
                "Page Title": title,
                "Page URL": url,
                "Source Type": detect_source_type(url),
                "Section Type": "Text",
                "Content/Label": text,
                "Source URL": "",
                "Notes": ""
            })

    # Extract PDFs
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            full_link = href if "http" in href else BASE_URL.rstrip("/") + "/" + href.lstrip("/")
            text = a.get_text(strip=True)
            size_match = re.search(r"Size[:]?\\s*(\\d+(\\.\\d+)?\\s*[KMG]B)", text, re.IGNORECASE)
            size = size_match.group(1) if size_match else ""
            data.append({
                "Page Title": title,
                "Page URL": url,
                "Source Type": detect_source_type(url),
                "Section Type": "PDF",
                "Content/Label": text,
                "Source URL": full_link,
                "Notes": size
            })

    # Extract Images
    for img in soup.find_all("img", src=True):
        src = img["src"]
        full_src = src if "http" in src else BASE_URL.rstrip("/") + "/" + src.lstrip("/")
        alt = img.get("alt", "")
        data.append({
            "Page Title": title,
            "Page URL": url,
            "Source Type": detect_source_type(url),
            "Section Type": "Image",
            "Content/Label": alt,
            "Source URL": full_src,
            "Notes": ""
        })

    return data

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:50]

def main():
    driver = setup_driver()
    visited = set()
    links_to_scrape = get_internal_links(driver, BASE_URL)
    print(f"🔍 Found {len(links_to_scrape)} internal pages to scrape.")

    for url in links_to_scrape:
        if url in visited:
            continue
        visited.add(url)
        print(f"🧭 Scraping: {url}")
        try:
            content = extract_content(driver, url)
            if content:
                filename = sanitize_filename(url.replace(BASE_URL, "").strip("/"))
                if not filename:
                    filename = "homepage"
                df = pd.DataFrame(content)
                df.to_csv(f"{filename}.csv", index=False)
                print(f"✅ Saved: {filename}.csv")
        except Exception as e:
            print(f"⚠️ Error scraping {url}: {e}")

    driver.quit()
    print("🎉 Done.")

if __name__ == "__main__":
    main()
