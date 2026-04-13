import unittest
from scraper import Scraper


class TestScraper(unittest.TestCase):

    def setUp(self):
        self.scraper = Scraper()

    def test_initialization(self):
        self.assertIsNotNone(self.scraper)

    def test_scrape_functionality(self):
        result = self.scraper.scrape('http://example.com')
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            self.scraper.scrape('invalid_url')


if __name__ == '__main__':
    unittest.main()