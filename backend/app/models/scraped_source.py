from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from app.db.database import Base
import uuid
import enum


class SourceType(str, enum.Enum):
    google_maps = "google_maps"
    yelp = "yelp"
    reddit = "reddit"
    twitter = "twitter"
    nextdoor = "nextdoor"
    craigslist = "craigslist"
    custom = "custom"


class ScrapedSource(Base):
    __tablename__ = "scraped_sources"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), nullable=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    scrape_id = Column(String(255), nullable=True, index=True)
    raw_data = Column(JSONB, nullable=False)
    processed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
