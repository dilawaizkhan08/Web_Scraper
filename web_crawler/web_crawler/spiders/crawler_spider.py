import scrapy
from urllib.parse import urlparse, urljoin
from web_crawler.items import WebCrawlerItem
import re

class CrawlerSpider(scrapy.Spider):
    name = "crawler"

    def __init__(self, search_query=None, *args, **kwargs):
        super(CrawlerSpider, self).__init__(*args, **kwargs)
        self.start_urls = [f"https://www.google.com/search?q={search_query}"]
        self.visited_urls = set()

    def parse(self, response):
        """Parse the search results page and extract URLs."""
        self.log(f"Crawling Google search results for: {response.url}")
        links = response.css('a::attr(href)').getall()

        for href in links:
            # Extract real URL from Google's /url?q= link format
            match = re.search(r'/url\?q=(https?://[^&]+)', href)
            if match:
                url = match.group(1)  # This is the clean URL
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                excluded_domains = ["facebook.com", "tiktok.com", "google.com", "youtube.com", "linkedin.com", "instagram.com", "twitter.com"]
                if not any(excluded in base_url for excluded in excluded_domains):
                    if base_url not in self.visited_urls:
                        self.visited_urls.add(base_url)

                        # Yield the URL to be saved in the URLs table
                        yield WebCrawlerItem(url=base_url)

                        # Request the URL for further crawling
                        yield scrapy.Request(url=base_url, callback=self.parse_page, meta={"base_url": base_url})

    def parse_page(self, response):
        """Crawl individual pages and extract content."""
        self.log(f"Crawling page: {response.url}")

        # Extract title and body content
        title = response.css('title::text').get().strip() if response.css('title::text').get() else 'No title'
        
        # Join all body text content
        body_content = ' '.join(response.css('body *::text').getall()).strip()[:500] if response.css('body *::text').getall() else 'No content'

        # Yield scraped data for the page
        yield WebCrawlerItem(
            url=response.url,
            title=title,
            content=body_content
        )

        # Follow internal links
        base_url = response.meta.get("base_url")
        links = response.css('a::attr(href)').getall()

        for href in links:
            full_url = urljoin(response.url, href)
            if self.is_internal_link(base_url, full_url) and full_url not in self.visited_urls:
                self.visited_urls.add(full_url)
                yield scrapy.Request(url=full_url, callback=self.parse_page, meta={"base_url": base_url})

    def is_internal_link(self, base_url, link):
        """Check if a link is internal to the base domain."""
        parsed_base = urlparse(base_url)
        parsed_link = urlparse(link)
        return parsed_link.netloc == "" or parsed_link.netloc == parsed_base.netloc
