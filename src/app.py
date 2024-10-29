from flask import Flask, render_template, request, jsonify
from threading import Thread
from main import WebCrawler
import logging

app = Flask(__name__)

# Initialize WebCrawler
web_crawler = WebCrawler(headless=True)

# Start the web crawler in a separate thread
def start_scraping(query):
    web_crawler.find_urls(query)
    web_crawler.crawl_urls()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-scraping', methods=['POST'])
def start_scraping_endpoint():
    query = request.json.get('query')
    if query:
        # Start scraping in a new thread
        thread = Thread(target=start_scraping, args=(query,))
        thread.start()
        logging.info(f"Started scraping for query: {query}")
        return jsonify({"status": "Scraping started"})
    return jsonify({"error": "No query provided"}), 400

if __name__ == '__main__':
    app.run(debug=True)
