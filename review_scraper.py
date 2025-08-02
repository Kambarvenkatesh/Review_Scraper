import time
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import re


class ReviewScraper:
    def __init__(self, headless=True, max_retries=3):
        self.driver = None
        self.headless = headless
        self.max_retries = max_retries
        self.setup_logger()

    def setup_driver(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=chrome_options)

    def setup_logger(self):
        self.logger = logging.getLogger("ReviewScraper")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        file_handler = logging.FileHandler('scraper.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def get_html(self, url):
        if not self.driver:
            self.setup_driver()

        for attempt in range(self.max_retries):
            try:
                self.driver.get(url)
                time.sleep(3)
                return self.driver.page_source
            except WebDriverException as e:
                self.logger.warning(f"Retry {attempt+1}/{self.max_retries} failed: {e}")
                time.sleep(2)
        raise Exception("Failed to retrieve page after retries.")

    def parse_reviews(self, html, source, start_date=None, end_date=None):
        soup = BeautifulSoup(html, 'html.parser')
        reviews = []

        if source == 'g2':
            review_cards = soup.find_all("div", class_="paper paper--white")
            for card in review_cards:
                title = card.find("h3")
                content = card.find("div", class_="review-body")
                date = card.find("span", class_="review-date")
                if title and content and date:
                    review_date = self.parse_date(date.text, source)
                    if self.is_within_range(review_date, start_date, end_date):
                        reviews.append({
                            "title": title.text.strip(),
                            "content": content.text.strip(),
                            "date": review_date.strftime('%Y-%m-%d'),
                            "source": source
                        })

        elif source == 'capterra':
            review_cards = soup.find_all("div", class_="reviewCard")
            for card in review_cards:
                title = card.find("h2")
                content = card.find("p")
                date = card.find("div", class_="date")
                if title and content and date:
                    review_date = self.parse_date(date.text, source)
                    if self.is_within_range(review_date, start_date, end_date):
                        reviews.append({
                            "title": title.text.strip(),
                            "content": content.text.strip(),
                            "date": review_date.strftime('%Y-%m-%d'),
                            "source": source
                        })

        elif source == 'trustpilot':
            review_cards = soup.find_all("article", attrs={"data-service-review-card-title-typography": True})
            for card in review_cards:
                title_elem = card.find("h2")
                content_elem = card.find("p", attrs={"data-service-review-card-typography": "review-content"})
                date_elem = card.find("time")
                if title_elem and content_elem and date_elem:
                    review_date = self.parse_date(date_elem.text.strip(), source)
                    if self.is_within_range(review_date, start_date, end_date):
                        reviews.append({
                            "title": title_elem.text.strip(),
                            "content": content_elem.text.strip(),
                            "date": review_date.strftime('%Y-%m-%d'),
                            "source": source
                        })

        return reviews

    def is_within_range(self, date_obj, start_date=None, end_date=None):
        if start_date and date_obj < start_date:
            return False
        if end_date and date_obj > end_date:
            return False
        return True

    def parse_date(self, date_str, source):
        try:
            if source == 'g2':
                return datetime.strptime(date_str.strip(), '%b %d, %Y')
            elif source == 'capterra':
                return datetime.strptime(date_str.strip(), '%B %d, %Y')
            elif source == 'trustpilot':
                return datetime.strptime(date_str.strip(), '%d %B %Y')
        except Exception:
            return datetime.now()

    def scrape_reviews(self, company_name, start_date=None, end_date=None, source='g2'):
        base_urls = {
            'g2': f"https://www.g2.com/products/{company_name}/reviews",
            'capterra': f"https://www.capterra.com/p/{company_name}/reviews/",
            'trustpilot': f"https://www.trustpilot.com/review/{company_name}.com"
        }

        url = base_urls.get(source)
        if not url:
            raise ValueError(f"Unsupported source: {source}")
        self.logger.info(f"Scraping reviews from {url} ...")

        try:
            html = self.get_html(url)
            start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
            reviews = self.parse_reviews(html, source, start_dt, end_dt)
            return reviews
        except Exception as e:
            print(f"Error: {e}")
            self.logger.error(f"Failed to scrape {source}: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def save_reviews(self, reviews, filename="sample_output.json"):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(reviews, f, indent=4, ensure_ascii=False)
            self.logger.info(f"Saved {len(reviews)} reviews to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save reviews: {e}")
