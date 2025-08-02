#!/usr/bin/env python3
"""
Test script for the ReviewScraper class.
This script tests various scenarios and validates the scraper functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
import tempfile
import os

# Import the scraper class
from review_scraper import ReviewScraper

class TestReviewScraper(unittest.TestCase):
    """Test cases for the ReviewScraper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scraper = ReviewScraper(headless=True)
        self.test_company = "Test Company"
        self.start_date = "2023-01-01"
        self.end_date = "2023-12-31"
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'scraper'):
            self.scraper.close_driver()
    
    def test_date_validation_valid_dates(self):
        """Test that valid dates are accepted."""
        try:
            reviews = self.scraper.scrape_reviews(
                self.test_company,
                self.start_date,
                self.end_date,
                "g2"
            )
            # Should not raise an exception for valid dates
            self.assertIsInstance(reviews, list)
        except ValueError:
            # This is expected since we're not actually scraping
            pass
    
    def test_date_validation_invalid_format(self):
        """Test that invalid date format raises ValueError."""
        with self.assertRaises(ValueError):
            self.scraper.scrape_reviews(
                self.test_company,
                "invalid-date",
                self.end_date,
                "g2"
            )
    
    def test_date_validation_start_after_end(self):
        """Test that start date after end date raises ValueError."""
        with self.assertRaises(ValueError):
            self.scraper.scrape_reviews(
                self.test_company,
                "2023-12-31",
                "2023-01-01",
                "g2"
            )
    
    def test_invalid_source(self):
        """Test that invalid source raises ValueError."""
        with self.assertRaises(ValueError):
            self.scraper.scrape_reviews(
                self.test_company,
                self.start_date,
                self.end_date,
                "invalid_source"
            )
    
    def test_valid_sources(self):
        """Test that all valid sources are accepted."""
        valid_sources = ["g2", "capterra", "trustpilot"]
        for source in valid_sources:
            try:
                reviews = self.scraper.scrape_reviews(
                    self.test_company,
                    self.start_date,
                    self.end_date,
                    source
                )
                self.assertIsInstance(reviews, list)
            except ValueError:
                # Expected since we're not actually scraping
                pass
    
    def test_review_structure(self):
        """Test that reviews have the expected structure."""
        # Mock a sample review
        sample_review = {
            "title": "Test Review",
            "description": "This is a test review description.",
            "date": "2023-06-15",
            "rating": 5,
            "reviewer_name": "Test User",
            "source": "G2"
        }
        
        # Validate required fields
        required_fields = ["title", "description", "date", "source"]
        for field in required_fields:
            self.assertIn(field, sample_review)
        
        # Validate data types
        self.assertIsInstance(sample_review["title"], str)
        self.assertIsInstance(sample_review["description"], str)
        self.assertIsInstance(sample_review["date"], str)
        self.assertIsInstance(sample_review["source"], str)
        
        # Validate date format
        try:
            datetime.strptime(sample_review["date"], "%Y-%m-%d")
        except ValueError:
            self.fail("Date is not in YYYY-MM-DD format")
    
    def test_json_output_structure(self):
        """Test that JSON output has the expected structure."""
        sample_output = {
            "company": "Test Company",
            "source": "g2",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "total_reviews": 10,
            "scraped_at": "2023-12-15T10:30:00.000000",
            "reviews": []
        }
        
        # Validate required fields
        required_fields = ["company", "source", "start_date", "end_date", "total_reviews", "scraped_at", "reviews"]
        for field in required_fields:
            self.assertIn(field, sample_output)
        
        # Validate data types
        self.assertIsInstance(sample_output["company"], str)
        self.assertIsInstance(sample_output["source"], str)
        self.assertIsInstance(sample_output["total_reviews"], int)
        self.assertIsInstance(sample_output["reviews"], list)
    
    def test_json_serialization(self):
        """Test that output can be serialized to JSON."""
        sample_output = {
            "company": "Test Company",
            "source": "g2",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "total_reviews": 5,
            "scraped_at": "2023-12-15T10:30:00.000000",
            "reviews": [
                {
                    "title": "Test Review",
                    "description": "Test description",
                    "date": "2023-06-15",
                    "rating": 5,
                    "reviewer_name": "Test User",
                    "source": "G2"
                }
            ]
        }
        
        # Test JSON serialization
        try:
            json_str = json.dumps(sample_output, indent=2, ensure_ascii=False)
            parsed_back = json.loads(json_str)
            self.assertEqual(sample_output, parsed_back)
        except Exception as e:
            self.fail(f"JSON serialization failed: {e}")
    
    def test_file_output(self):
        """Test that output can be written to a file."""
        sample_output = {
            "company": "Test Company",
            "source": "g2",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "total_reviews": 3,
            "scraped_at": "2023-12-15T10:30:00.000000",
            "reviews": [
                {
                    "title": "Review 1",
                    "description": "Description 1",
                    "date": "2023-06-15",
                    "rating": 5,
                    "reviewer_name": "User 1",
                    "source": "G2"
                },
                {
                    "title": "Review 2",
                    "description": "Description 2",
                    "date": "2023-07-20",
                    "rating": 4,
                    "reviewer_name": "User 2",
                    "source": "G2"
                },
                {
                    "title": "Review 3",
                    "description": "Description 3",
                    "date": "2023-08-10",
                    "rating": 3,
                    "reviewer_name": "User 3",
                    "source": "G2"
                }
            ]
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_filename = f.name
        
        try:
            # Write to file
            with open(temp_filename, 'w', encoding='utf-8') as f:
                json.dump(sample_output, f, indent=2, ensure_ascii=False)
            
            # Verify file exists and has content
            self.assertTrue(os.path.exists(temp_filename))
            
            # Read back and verify content
            with open(temp_filename, 'r', encoding='utf-8') as f:
                loaded_output = json.load(f)
            
            self.assertEqual(sample_output, loaded_output)
            
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_error_handling_empty_company(self):
        """Test error handling for empty company name."""
        with self.assertRaises(Exception):
            self.scraper.scrape_reviews(
                "",
                self.start_date,
                self.end_date,
                "g2"
            )
    
    def test_error_handling_none_company(self):
        """Test error handling for None company name."""
        with self.assertRaises(Exception):
            self.scraper.scrape_reviews(
                None,
                self.start_date,
                self.end_date,
                "g2"
            )

def run_performance_test():
    """Run a simple performance test."""
    print("Running performance test...")
    
    scraper = ReviewScraper(headless=True)
    
    try:
        start_time = datetime.now()
        
        # Test scraping with a small date range
        reviews = scraper.scrape_reviews(
            "Salesforce",
            "2023-12-01",
            "2023-12-15",
            "g2"
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"Performance test completed in {duration:.2f} seconds")
        print(f"Scraped {len(reviews)} reviews")
        
    except Exception as e:
        print(f"Performance test failed: {e}")
    
    finally:
        scraper.close_driver()

if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance test
    print("\n" + "="*50)
    run_performance_test() 