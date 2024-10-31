from flask import Flask, render_template, request, jsonify
from threading import Thread
from main import WebCrawler
from models import ScrapedData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging
import os
import requests
import numpy as np

# Import the embeddings class
from langchain_community.embeddings import HuggingFaceEmbeddings  # or any other embeddings you choose
# from langchain.vectorstores import FAISS  # Uncomment if you decide to use FAISS or any available vector store
# from langchain.vectorstores import Chroma  # Uncomment if you decide to use Chroma

app = Flask(__name__)

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///crawler.db")

# Database setup
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Initialize WebCrawler
web_crawler = WebCrawler(headless=True)

# Groq headers for authorization
groq_headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Function to retrieve documents from SQLite and create a searchable data structure
def get_documents():
    session = Session()
    docs = []
    try:
        # Retrieve scraped data from the database
        results = session.query(ScrapedData).all()

        # Prepare docs with content and metadata
        for result in results:
            docs.append({
                "page_content": result.content,
                "metadata": {"url": result.url, "title": result.title}
            })
        return docs
    except Exception as e:
        logging.error(f"Error in retrieving documents: {e}")
        return None
    finally:
        session.close()

# Function to start the web crawler in a separate thread
def start_scraping(query):
    web_crawler.find_urls(query)
    web_crawler.crawl_urls()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query')
def query():
    return render_template('query.html')

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

@app.route('/generate-answer', methods=['POST'])
def generate_answer():
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    docs = get_documents()
    if not docs:
        return jsonify({"error": "No documents found in the database"}), 500

    try:
        # Initialize the embedding model
        embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # Create embeddings for documents and the query
        doc_embeddings = embedding_model.embed_documents([doc["page_content"] for doc in docs])
        query_embedding = embedding_model.embed_query(query)

        # Retrieve the most relevant documents based on embeddings
        similarities = np.array([np.dot(doc_emb, query_embedding) for doc_emb in doc_embeddings])
        top_indices = np.argsort(similarities)[-3:]  # Get top 3 indices
        
        # Format the top documents into a structured response
        top_results = [
            {
                "url": docs[i]["metadata"]["url"],
                "title": docs[i]["metadata"]["title"],
                "content": docs[i]["page_content"]
            }
            for i in reversed(top_indices)  # Show most relevant first
        ]

        # Return structured response with URLs, titles, and content
        return jsonify({"response": top_results}), 200

    except Exception as e:
        logging.error(f"An error occurred during RAG generation: {e}")
        return jsonify({"error": "An error occurred during generation"}), 500


if __name__ == '__main__':
    app.run(debug=True)
