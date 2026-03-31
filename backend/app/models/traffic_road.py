from sqlalchemy import Column, Integer, String, Float, DateTime, Index, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class TrafficRoad(Base):
    """
    Stores DOT Annual Average Daily Traffic (AADT) road segment data.
    Data is downloaded from state DOT ArcGIS services and stored locally
    for fast spatial queries and complete road coverage.
    """
    __tablename__ = "traffic_roads"

    id = Column(Integer, primary_key=True, index=True)
    
    state = Column(String(2), nullable=False, index=True)
    county = Column(String(100), nullable=True, index=True)
    district = Column(String(50), nullable=True)
    
    roadway_id = Column(String(100), nullable=True)
    road_name = Column(String(255), nullable=True)
    description_from = Column(String(500), nullable=True)
    description_to = Column(String(500), nullable=True)
    
    aadt = Column(Integer, nullable=False, index=True)
    year = Column(SmallInteger, nullable=False, index=True)
    
    k_factor = Column(Float, nullable=True)
    d_factor = Column(Float, nullable=True)
    t_factor = Column(Float, nullable=True)
    
    geometry = Column(Text, nullable=False)
    
    begin_post = Column(Float, nullable=True)
    end_post = Column(Float, nullable=True)
    shape_length = Column(Float, nullable=True)
    
    raw_attributes = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_traffic_roads_state_year', 'state', 'year'),
    )
