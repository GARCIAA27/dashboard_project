from database import Base, engine

print("Creando tablas...")
Base.metadata.create_all(bind=engine)
print("Tablas creadas.")
