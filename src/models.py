from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Model to store URLs
class URL(Base):
    __tablename__ = 'urls'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True)

# Model to store scraped data
class ScrapedData(Base):
    __tablename__ = 'scraped_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)  # Store the URL
    title = Column(String)  # Store the page title
    content = Column(Text)  # Store the page content

