#!/usr/bin/env python3
"""
Example script demonstrating how to use the ReviewScraper class programmatically.
Scrapes reviews and saves results to JSON.
"""

from review_scraper import ReviewScraper
from datetime import datetime, timedelta
import json
import time

def main():
    scraper = ReviewScraper(headless=True)

    companies = ["Salesforce", "Slack", "Zoom"]
    sources = ["g2", "capterra", "trustpilot"]

    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)

    try:
        for company in companies:
            print(f"\n{'='*60}")
            print(f"Scraping reviews for: {company}")
            print(f"From: {start_date.date()} To: {end_date.date()}")
            print(f"{'='*60}")

            for source in sources:
                print(f"→ Scraping from {source.upper()}...")
                try:
                    reviews = scraper.scrape_reviews(
                        company_name=company,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d'),
                        source=source
                    )

                    output_data = {
                        "company": company,
                        "source": source,
                        "start_date": start_date.strftime('%Y-%m-%d'),
                        "end_date": end_date.strftime('%Y-%m-%d'),
                        "total_reviews": len(reviews),
                        "scraped_at": datetime.now().isoformat(),
                        "reviews": reviews
                    }

                    filename = f"{company.lower()}_{source}_reviews.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, indent=2, ensure_ascii=False)

                    print(f"✓ Saved {len(reviews)} reviews to {filename}")

                except Exception as e:
                    print(f"✗ Error scraping from {source.upper()}: {e}")
                time.sleep(2)

    except Exception as e:
        print(f"✗ General error: {e}")
    finally:
        scraper.close_driver()
        print("\n✅ Scraping finished!")

if __name__ == "__main__":
    main()
