from alembic.config import Config
from alembic import command

print("Running Alembic migrations...")
config = Config("alembic.ini")
command.upgrade(config, "head")
print("Migrations applied.")
