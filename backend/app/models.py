from sqlalchemy import Column, DateTime, Integer, String, Text
from .database import Base

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    id = Column(String(36), primary_key=True, index=True)
    status = Column(String(20), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    audio_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    progress = Column(Integer, nullable=False, default=0)
    result_json = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    error_code = Column(String(80), nullable=True)
    error_message = Column(Text, nullable=True)
