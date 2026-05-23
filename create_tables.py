from database import Base, engine
from models.user import User
from models.projects import Project

print("Creando tablas...")
Base.metadata.create_all(bind=engine)
print("Listo.")
