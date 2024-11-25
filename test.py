from hexaa_business_scraper import scrape_businesses

# Parameters:
search_query = "restaurants in New York"  # Search term for businesses
total_results = 10  # Number of results to scrape

# Scrape and save results to a CSV file
scrape_businesses(search_query, total_results)