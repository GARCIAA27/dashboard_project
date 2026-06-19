from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base

class RoleEnum(str, PyEnum):
    admin = "admin"
    user = "user"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", backref="projects")
    documents = relationship("Document", back_populates="project")
    total_size = Column(BigInteger, nullable=False, default=0)

class ProjectAccess(Base):
    __tablename__ = "project_access"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(Enum(RoleEnum, name="role_enum"), nullable=False)

    project = relationship("Project", backref="access_list")
    user = relationship("User", backref="project_access")
