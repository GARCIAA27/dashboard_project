from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="documents")
