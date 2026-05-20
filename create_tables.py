# create_tables.py
from database import Base, engine
from models.user import User  # importa tus modelos

print("Creando tablas en la base de datos...")
Base.metadata.create_all(bind=engine)
print("Listo.")
