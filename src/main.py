import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
import time
import os
from dotenv import load_dotenv
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import URL, ScrapedData, Base

class WebCrawler:
    def __init__(self, headless=True):
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Load environment variables
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
        
        # Database setup
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///crawler.db")
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_base_url(self, url):
        """Extract and return the base domain of the given URL."""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return base_url

    def find_urls(self, search_query, max_results=20):
        service = Service("/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=self.options)
        session = self.Session()
        
        try:
            driver.get("https://www.google.com")
            search_box = driver.find_element(By.NAME, "q")
            search_box.send_keys(search_query)
            search_box.submit()

            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div#search')))

            # Scraping organic search results (with more specific selector to avoid ads)
            results = driver.find_elements(By.CSS_SELECTOR, 'div#search a')
            urls = []

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

                        # Save URL to the database
                        new_url = URL(url=base_domain)
                        session.add(new_url)
                        logging.info(f"Added URL to database: {base_domain}")

            session.commit()

        except Exception as e:
            logging.error(f"An error occurred while finding URLs: {e}")
        finally:
            session.close()
            driver.quit()

    def is_internal_link(self, base_url, link):
        """Check if a link is internal to the base domain."""
        parsed_base = urlparse(base_url)
        parsed_link = urlparse(link)
        return parsed_link.netloc == "" or parsed_link.netloc == parsed_base.netloc

    def crawl_page(self, driver, base_url, visited, session):
        """Crawl a single page and gather internal links."""
        try:
            logging.info(f"Crawling data from: {base_url}")
            driver.get(base_url)
            time.sleep(2)  # Let the page load fully

            # Get the title of the page
            title = driver.title.strip()  # Strip any extra whitespace

            # Get the content from the page body
            body_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            body_content = body_element.text.strip()  # Strip and capture the full body content
            
            # Limit content length if needed
            body_content_snippet = body_content[:500]  # Adjust this as needed

            # Save the URL, title, and content to the database
            scraped_data = ScrapedData(url=base_url, title=title, content=body_content_snippet)
            session.add(scraped_data)
            session.commit()  # Commit the transaction to save the data
            logging.info(f"Scraped data from: {base_url}")

            # Find all internal links on the page and crawl them recursively
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute('href')
                if href and self.is_internal_link(base_url, href):
                    full_url = urljoin(base_url, href)
                    if full_url not in visited:
                        visited.add(full_url)
                        logging.info(f"Found internal link: {full_url}")
                        self.crawl_page(driver, full_url, visited, session)  # Recursive call

        except Exception as e:
            logging.error(f"An error occurred while crawling {base_url}: {e}")


    def crawl_urls(self):
        session = self.Session()
        try:
            # Get URLs from the database
            urls = session.query(URL).all()

            if not urls:
                logging.error("No URLs found in the database")
                return

            service = Service("/usr/local/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=self.options)

            visited = set()  # Track visited URLs

            for url_entry in urls:
                self.crawl_page(driver, url_entry.url, visited, session)  # Start crawling from the base URL

            session.commit()

        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            session.close()
            driver.quit()

if __name__ == "__main__":
    web_crawler = WebCrawler(headless=True)  # Set headless=False to see the browser in action
    query = input("Enter your search query: ")
    web_crawler.find_urls(query)  # Find and save URLs in the database
    web_crawler.crawl_urls()      # Crawl and scrape data from the saved URLs in the database
