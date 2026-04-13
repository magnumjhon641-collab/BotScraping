#!/usr/bin/env python3
"""
Enhanced Web Scraper with retry logic, caching, and comprehensive metadata extraction.
"""

import sys
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class WebScraper:
    """Enhanced web scraper with retry logic and comprehensive metadata extraction."""
    
    def __init__(self, url: str, db_path: str = "websites.db"):
        self.url = self._normalize_url(url)
        self.db_path = db_path
        self.session = self._create_session()
        self._init_database()
    
    def _normalize_url(self, url: str) -> str:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["HEAD", "GET"])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        return session
    
    def _init_database(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS websites (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE, title TEXT, description TEXT, favicon TEXT, og_image TEXT, logo TEXT, background_image TEXT, scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT)''')
        conn.commit()
        conn.close()
    
    def fetch_page(self) -> Optional[str]:
        try:
            logger.info(f"Fetching: {self.url}")
            response = self.session.get(self.url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {self.url}: {e}")
            return None
    
    def extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return None
    
    def extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"]
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"]
        return None
    
    def extract_favicon(self, soup: BeautifulSoup) -> Optional[str]:
        for tag in soup.find_all("link"):
            if tag.get("rel") and any("icon" in rel.lower() for rel in tag.get("rel", [])):
                if tag.get("href"):
                    return urljoin(self.url, tag["href"])
        return urljoin(self.url, "/favicon.ico")
    
    def extract_og_image(self, soup: BeautifulSoup) -> Optional[str]:
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return urljoin(self.url, og_image["content"])
        return None
    
    def extract_logo(self, soup: BeautifulSoup) -> Optional[str]:
        img = soup.find("img", {"class": lambda x: x and "logo" in x.lower()}) or soup.find("img", {"id": lambda x: x and "logo" in x.lower()})
        if img and img.get("src"):
            return urljoin(self.url, img["src"])
        first_img = soup.find("img")
        if first_img and first_img.get("src"):
            return urljoin(self.url, first_img["src"])
        return None
    
    def extract_background(self, soup: BeautifulSoup) -> Optional[str]:
        import re
        body = soup.body
        if body and body.get("style"):
            bg = self._extract_url_from_css(body["style"])
            if bg:
                return urljoin(self.url, bg)
        for style_tag in soup.find_all("style"):
            if style_tag.string:
                bg = self._extract_url_from_css(style_tag.string)
                if bg:
                    return urljoin(self.url, bg)
        return None
    
    @staticmethod
    def _extract_url_from_css(css_text: str) -> Optional[str]:
        import re
        match = re.search(r"background(?:-image)?\s*: \s*url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", css_text, re.IGNORECASE)
        if match:
            return match.group(1).strip().replace("\\", "")
        return None
    
    def scrape(self) -> Dict:
        html = self.fetch_page()
        if not html:
            return {"url": self.url, "status": "failed"}
        soup = BeautifulSoup(html, "html.parser")
        data = {"url": self.url, "title": self.extract_title(soup), "description": self.extract_description(soup), "favicon": self.extract_favicon(soup), "og_image": self.extract_og_image(soup), "logo": self.extract_logo(soup), "background_image": self.extract_background(soup), "status": "success", "scraped_at": datetime.now().isoformat()}
        logger.info(f"✓ Successfully scraped: {self.url}")
        return data
    
    def save_to_database(self, data: Dict):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO websites (url, title, description, favicon, og_image, logo, background_image, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (data['url'], data.get('title'), data.get('description'), data.get('favicon'), data.get('og_image'), data.get('logo'), data.get('background_image'), data.get('status')))
            conn.commit()
            conn.close()
            logger.info(f"✓ Saved to database: {data['url']}")
        except Exception as e:
            logger.error(f"Database error: {e}")
    
    def save_to_json(self, data: Dict, output_file: str = "output.json"):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"✓ Saved to JSON: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python scraper.py <url> [--db] [--json]")
        sys.exit(1)
    url = sys.argv[1]
    save_db = '--db' in sys.argv
    save_json = '--json' in sys.argv or len(sys.argv) == 2
    scraper = WebScraper(url)
    result = scraper.scrape()
    if result['status'] == 'success':
        if save_json:
            scraper.save_to_json(result)
        if save_db:
            scraper.save_to_database(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        logger.error("Scraping failed")
        sys.exit(1)

if __name__ == "__main__":
    main()