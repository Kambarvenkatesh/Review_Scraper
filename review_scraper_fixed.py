#!/usr/bin/env python3
"""
Pulse Coding Assignment - Product Review Scraper
Scrapes product reviews from G2, Capterra, and Trustpilot for a specific company and time period.
"""

import json
import re
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus, urljoin
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from dateutil import parser
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReviewScraper:
    """Main class for scraping reviews from multiple sources."""
    
    def __init__(self, headless: bool = True):
        """Initialize the scraper with browser options."""
        self.ua = UserAgent()
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def setup_driver(self):
        """Setup Chrome WebDriver for dynamic content scraping."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"--user-agent={self.ua.random}")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        return self.driver
    
    def close_driver(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
    
    def scrape_reviews(self, company_name: str, start_date: str, end_date: str, source: str) -> List[Dict[str, Any]]:
        """
        Main method to scrape reviews based on source.
        
        Args:
            company_name: Name of the company to search for
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            source: Source to scrape from ('g2', 'capterra', 'trustpilot')
        
        Returns:
            List of review dictionaries
        """
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Dates must be in YYYY-MM-DD format")
        
        if start_dt > end_dt:
            raise ValueError("Start date must be before end date")
        
        source = source.lower()
        if source == 'g2':
            return self._scrape_g2(company_name, start_dt, end_dt)
        elif source == 'capterra':
            return self._scrape_capterra(company_name, start_dt, end_dt)
        elif source == 'trustpilot':
            return self._scrape_trustpilot(company_name, start_dt, end_dt)
        else:
            raise ValueError("Source must be 'g2', 'capterra', or 'trustpilot'")
    
    def _scrape_g2(self, company_name: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Scrape reviews from G2."""
        logger.info(f"Scraping G2 reviews for {company_name}")
        reviews = []
        
        try:
            # Search for the company on G2
            search_url = f"https://www.g2.com/search?utf8=%E2%9C%93&query={quote_plus(company_name)}"
            
            if not self.driver:
                self.setup_driver()
            
            self.driver.get(search_url)
            time.sleep(3)
            
            # Find the first product link
            try:
                product_link = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/products/']"))
                )
                product_url = product_link.get_attribute('href')
                
                # Navigate to reviews page
                reviews_url = f"{product_url}/reviews"
                self.driver.get(reviews_url)
                time.sleep(3)
                
                # Scrape reviews with pagination
                page = 1
                while True:
                    logger.info(f"Scraping G2 page {page}")
                    
                    # Wait for reviews to load
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='review-card']"))
                    )
                    
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    review_cards = soup.find_all("div", {"data-testid": "review-card"})
                    
                    if not review_cards:
                        break
                    
                    page_reviews = []
                    for card in review_cards:
                        try:
                            review = self._parse_g2_review(card, start_date, end_date)
                            if review:
                                page_reviews.append(review)
                        except Exception as e:
                            logger.warning(f"Error parsing G2 review: {e}")
                            continue
                    
                    if not page_reviews:
                        break
                    
                    reviews.extend(page_reviews)
                    
                    # Check for next page
                    try:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, "[aria-label='Next page']")
                        if 'disabled' in next_button.get_attribute('class'):
                            break
                        next_button.click()
                        time.sleep(3)
                        page += 1
                    except Exception:
                        break
                        
        except Exception as e:
            logger.error(f"Error scraping G2: {e}")
        
        logger.info(f"Scraped {len(reviews)} reviews from G2")
        return reviews
    
    def _parse_g2_review(self, card, start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """Parse individual G2 review card."""
        try:
            # Extract review title
            title_elem = card.find("h3", {"data-testid": "review-title"})
            title = title_elem.get_text(strip=True) if title_elem else "No title"
            
            # Extract review content
            content_elem = card.find("div", {"data-testid": "review-content"})
            content = content_elem.get_text(strip=True) if content_elem else ""
            
            # Extract date
            date_elem = card.find("time")
            if date_elem:
                date_str = date_elem.get('datetime', '')
                try:
                    review_date = parser.parse(date_str)
                    if not (start_date <= review_date <= end_date):
                        return None
                except Exception:
                    review_date = datetime.now()
            else:
                review_date = datetime.now()
            
            # Extract rating
            rating_elem = card.find("div", {"data-testid": "rating"})
            rating = None
            if rating_elem:
                stars = rating_elem.find_all("svg", {"data-testid": "star-filled"})
                rating = len(stars)
            
            # Extract reviewer name
            reviewer_elem = card.find("span", {"data-testid": "reviewer-name"})
            reviewer = reviewer_elem.get_text(strip=True) if reviewer_elem else "Anonymous"
            
            return {
                "title": title,
                "description": content,
                "date": review_date.strftime('%Y-%m-%d'),
                "rating": rating,
                "reviewer_name": reviewer,
                "source": "G2"
            }
            
        except Exception as e:
            logger.warning(f"Error parsing G2 review card: {e}")
            return None
    
    def _scrape_capterra(self, company_name: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Scrape reviews from Capterra."""
        logger.info(f"Scraping Capterra reviews for {company_name}")
        reviews = []
        
        try:
            # Search for the company on Capterra
            search_url = f"https://www.capterra.com/search/?q={quote_plus(company_name)}"
            
            if not self.driver:
                self.setup_driver()
            
            self.driver.get(search_url)
            time.sleep(3)
            
            # Find the first product link
            try:
                product_link = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/p/']"))
                )
                product_url = product_link.get_attribute('href')
                
                # Navigate to reviews page
                reviews_url = f"{product_url}/reviews"
                self.driver.get(reviews_url)
                time.sleep(3)
                
                # Scrape reviews with pagination
                page = 1
                while True:
                    logger.info(f"Scraping Capterra page {page}")
                    
                    # Wait for reviews to load
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".review-item"))
                    )
                    
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    review_items = soup.find_all("div", class_="review-item")
                    
                    if not review_items:
                        break
                    
                    page_reviews = []
                    for item in review_items:
                        try:
                            review = self._parse_capterra_review(item, start_date, end_date)
                            if review:
                                page_reviews.append(review)
                        except Exception as e:
                            logger.warning(f"Error parsing Capterra review: {e}")
                            continue
                    
                    if not page_reviews:
                        break
                    
                    reviews.extend(page_reviews)
                    
                    # Check for next page
                    try:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, ".pagination-next:not(.disabled)")
                        next_button.click()
                        time.sleep(3)
                        page += 1
                    except Exception:
                        break
                        
        except Exception as e:
            logger.error(f"Error scraping Capterra: {e}")
        
        logger.info(f"Scraped {len(reviews)} reviews from Capterra")
        return reviews
    
    def _parse_capterra_review(self, item, start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """Parse individual Capterra review item."""
        try:
            # Extract review title
            title_elem = item.find("h3", class_="review-title")
            title = title_elem.get_text(strip=True) if title_elem else "No title"
            
            # Extract review content
            content_elem = item.find("div", class_="review-content")
            content = content_elem.get_text(strip=True) if content_elem else ""
            
            # Extract date
            date_elem = item.find("time")
            if date_elem:
                date_str = date_elem.get('datetime', '')
                try:
                    review_date = parser.parse(date_str)
                    if not (start_date <= review_date <= end_date):
                        return None
                except Exception:
                    review_date = datetime.now()
            else:
                review_date = datetime.now()
            
            # Extract rating
            rating_elem = item.find("div", class_="rating")
            rating = None
            if rating_elem:
                stars = rating_elem.find_all("span", class_="star-filled")
                rating = len(stars)
            
            # Extract reviewer name
            reviewer_elem = item.find("span", class_="reviewer-name")
            reviewer = reviewer_elem.get_text(strip=True) if reviewer_elem else "Anonymous"
            
            return {
                "title": title,
                "description": content,
                "date": review_date.strftime('%Y-%m-%d'),
                "rating": rating,
                "reviewer_name": reviewer,
                "source": "Capterra"
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Capterra review item: {e}")
            return None
    
    def _scrape_trustpilot(self, company_name: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Scrape reviews from Trustpilot (third source)."""
        logger.info(f"Scraping Trustpilot reviews for {company_name}")
        reviews = []
        
        try:
            # Search for the company on Trustpilot
            search_url = f"https://www.trustpilot.com/search?query={quote_plus(company_name)}"
            
            if not self.driver:
                self.setup_driver()
            
            self.driver.get(search_url)
            time.sleep(3)
            
            # Find the first business link
            try:
                business_link = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/review/']"))
                )
                business_url = business_link.get_attribute('href')
                
                # Navigate to reviews page
                reviews_url = f"{business_url}/reviews"
                self.driver.get(reviews_url)
                time.sleep(3)
                
                # Scrape reviews with pagination
                page = 1
                while True:
                    logger.info(f"Scraping Trustpilot page {page}")
                    
                    # Wait for reviews to load
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-service-review-card-typography='review-title']"))
                    )
                    
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    review_cards = soup.find_all("article", {"data-service-review-card-typography": "review-title"})
                    
                    if not review_cards:
                        break
                    
                    page_reviews = []
                    for card in review_cards:
                        try:
                            review = self._parse_trustpilot_review(card, start_date, end_date)
                            if review:
                                page_reviews.append(review)
                        except Exception as e:
                            logger.warning(f"Error parsing Trustpilot review: {e}")
                            continue
                    
                    if not page_reviews:
                        break
                    
                    reviews.extend(page_reviews)
                    
                    # Check for next page
                    try:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, "[data-pagination-button-next='true']")
                        if 'disabled' in next_button.get_attribute('class'):
                            break
                        next_button.click()
                        time.sleep(3)
                        page += 1
                    except Exception:
                        break
                        
        except Exception as e:
            logger.error(f"Error scraping Trustpilot: {e}")
        
        logger.info(f"Scraped {len(reviews)} reviews from Trustpilot")
        return reviews
    
    def _parse_trustpilot_review(self, card, start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """Parse individual Trustpilot review card."""
        try:
            # Extract review title
            title_elem = card.find("h2", {"data-service-review-card-typography": "review-title"})
            title = title_elem.get_text(strip=True) if title_elem else "No title"
            
            # Extract review content
            content_elem = card.find("p", {"data-service-review-card-typography": "review-content"})
            content = content_elem.get_text(strip=True) if content_elem else ""
            
            # Extract date
            date_elem = card.find("time")
            if date_elem:
                date_str = date_elem.get('datetime', '')
                try:
                    review_date = parser.parse(date_str)
                    if not (start_date <= review_date <= end_date):
                        return None
                except Exception:
                    review_date = datetime.now()
            else:
                review_date = datetime.now()
            
            # Extract rating
            rating_elem = card.find("div", {"data-service-review-rating": True})
            rating = None
            if rating_elem:
                rating_attr = rating_elem.get('data-service-review-rating')
                try:
                    rating = int(rating_attr)
                except Exception:
                    pass
            
            # Extract reviewer name
            reviewer_elem = card.find("span", {"data-service-review-card-typography": "consumer-name"})
            reviewer = reviewer_elem.get_text(strip=True) if reviewer_elem else "Anonymous"
            
            return {
                "title": title,
                "description": content,
                "date": review_date.strftime('%Y-%m-%d'),
                "rating": rating,
                "reviewer_name": reviewer,
                "source": "Trustpilot"
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Trustpilot review card: {e}")
            return None

def main():
    """Main function to handle command line arguments and execute scraping."""
    parser = argparse.ArgumentParser(description='Scrape product reviews from G2, Capterra, and Trustpilot')
    parser.add_argument('--company', required=True, help='Company name to search for')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--source', required=True, choices=['g2', 'capterra', 'trustpilot'], 
                       help='Source to scrape from')
    parser.add_argument('--output', default='reviews.json', help='Output JSON file name')
    parser.add_argument('--headless', action='store_true', default=True, 
                       help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    # Validate dates
    try:
        start_dt = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        return
    
    if start_dt > end_dt:
        print("Error: Start date must be before end date")
        return
    
    # Initialize scraper
    scraper = ReviewScraper(headless=args.headless)
    
    try:
        # Scrape reviews
        print(f"Starting to scrape {args.source.upper()} reviews for {args.company}")
        print(f"Date range: {args.start_date} to {args.end_date}")
        
        reviews = scraper.scrape_reviews(
            args.company, 
            args.start_date, 
            args.end_date, 
            args.source
        )
        
        # Save to JSON file
        output_data = {
            "company": args.company,
            "source": args.source,
            "start_date": args.start_date,
            "end_date": args.end_date,
            "total_reviews": len(reviews),
            "scraped_at": datetime.now().isoformat(),
            "reviews": reviews
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully scraped {len(reviews)} reviews")
        print(f"Results saved to {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Scraping failed: {e}")
    
    finally:
        scraper.close_driver()

if __name__ == "__main__":
    main() 