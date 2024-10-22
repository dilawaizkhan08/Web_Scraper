import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import time
import os
from dotenv import load_dotenv
import re

class WebCrawler:
    def __init__(self, headless=True):
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Load environment variables if needed
        load_dotenv()

        # Configure headless browser
        self.options = Options()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--disable-setuid-sandbox")

        # Disable Selenium logging
        logging.getLogger('selenium').setLevel(logging.CRITICAL)
        logging.getLogger('urllib3').setLevel(logging.CRITICAL)

    def get_base_url(self, url):
        """
        Extract and return the base domain of the given URL.
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return base_url

    def find_urls(self, search_query, max_results=20):
        service = Service("/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=self.options)
        urls = []
        try:
            driver.get("https://www.google.com")
            search_box = driver.find_element(By.NAME, "q")
            search_box.send_keys(search_query)
            search_box.submit()

            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#search')))

            # Scraping organic search results (with more specific selector to avoid ads)
            results = driver.find_elements(By.CSS_SELECTOR, 'div#search a')

            for result in results[:max_results]:
                href = result.get_attribute("href")
                if href and re.match(r'^https?://', href):
                    parsed_url = urlparse(href)
                    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

                    # Filter out large platforms and irrelevant domains
                    excluded_domains = ["facebook.com", "tiktok.com", "google.com", "youtube.com", "linkedin.com", "instagram.com", "twitter.com"]
                    if any(excluded in domain for excluded in excluded_domains):
                        continue

                    # Get only the base domain
                    base_domain = self.get_base_url(domain)

                    # Avoid adding duplicates
                    if base_domain not in urls:
                        urls.append(base_domain)

            # Save the top results to a file
            with open("urls.txt", "w") as f:
                for url in urls:
                    f.write(f"{url}\n")
            
            logging.info(f"URLs saved to urls.txt")

        except Exception as e:
            logging.error(f"An error occurred while finding URLs: {e}")
        finally:
            driver.quit()  # Ensure the driver is closed properly

    def crawl_urls(self):
        try:
            # Read URLs from the urls.txt file
            with open("urls.txt", "r") as f:
                urls = [line.strip() for line in f.readlines()]

            if not urls:
                logging.error("No URLs found in urls.txt")
                return

            service = Service("/usr/local/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=self.options)

            for url in urls:
                try:
                    logging.info(f"Crawling data from: {url}")
                    driver.get(url)
                    time.sleep(2)  # Allow the page to load

                    # Example: Scraping the title and some body content
                    title = driver.title
                    body_content = driver.find_element(By.TAG_NAME, "body").text[:500]  # Limit body text to first 500 characters

                    # Save the scraped data to a file
                    with open("scraped_data.txt", "a") as f:
                        f.write(f"URL: {url}\n")
                        f.write(f"Title: {title}\n")
                        f.write(f"Content: {body_content}\n\n")
                    
                    logging.info(f"Scraped data from: {url}")

                except Exception as e:
                    logging.error(f"An error occurred while crawling {url}: {e}")

        except Exception as e:
            logging.error(f"An error occurred while reading URLs: {e}")
        finally:
            driver.quit()  # Ensure the driver is closed properly

if __name__ == "__main__":
    web_crawler = WebCrawler(headless=True)  # Set headless=False to see the browser in action
    query = input("Enter your search query: ")
    web_crawler.find_urls(query)  # Find and save base URLs
    web_crawler.crawl_urls()      # Crawl and scrape data from the saved base URLs
