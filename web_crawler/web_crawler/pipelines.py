from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

Base = declarative_base()

# Define the URLs table for storing scraped URLs
class URL(Base):
    __tablename__ = 'urls'
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    scraped = Column(Integer, default=0)  # Indicates whether the URL has been crawled

# Define the ScrapedData table for storing page data
class ScrapedData(Base):
    __tablename__ = 'scraped_data'
    id = Column(Integer, primary_key=True)
    url_id = Column(Integer, ForeignKey('urls.id'))
    url = Column(String)
    title = Column(String)
    content = Column(Text)

class DatabasePipeline:

    def __init__(self):
        load_dotenv()
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///crawler.db")
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def open_spider(self, spider):
        """Open a new database session when the spider starts."""
        self.session = self.Session()

    def close_spider(self, spider):
        """Close the database session when the spider closes."""
        self.session.close()

    def process_item(self, item, spider):
        """Save the scraped URLs or data to the database."""
        if 'title' in item and 'content' in item:
            # Save the scraped page data into the ScrapedData table
            url_record = self.session.query(URL).filter_by(url=item['url']).first()
            if url_record:
                scraped_data = ScrapedData(
                    url_id=url_record.id,
                    url=item['url'],
                    title=item['title'],
                    content=item['content']
                )
                self.session.add(scraped_data)
                # Mark the URL as scraped
                url_record.scraped = 1
                self.session.commit()
        else:
            # Save the URL into the URLs table
            if not self.session.query(URL).filter_by(url=item['url']).first():
                new_url = URL(url=item['url'])
                self.session.add(new_url)
                self.session.commit()

        return item
