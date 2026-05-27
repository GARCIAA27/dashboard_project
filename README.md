FastAPI + PostgreSQL CRUD

This project implements a CRUD API using FastAPI and PostgreSQL. Containers are orchestrated with Docker Compose, but database table creation is done manually.

-Requirements

Docker and Docker Compose installed

PostgreSQL image available

Python 3.12 image available

-Project Files

docker-compose.yml: defines API and DB services

Dockerfile: builds the API image

requirements.txt: Python dependencies

create_tables.py: initializes database tables

models/: contains SQLAlchemy models

.env.example: environment variables template

-Environment Variables

Copy .env.example to .env and set all values

Steps for getting the container up:

▶️ Step 1: Start Services with Compose

docker-compose up --build -d

This command builds the API image and starts both API and DB containers in detached mode.

▶️ Step 2: Create Tables Manually

Run the script inside the API container:

docker-compose exec api python create_tables.py

Verify tables in PostgreSQL:

docker-compose exec db psql -U postgres -d projectdb
\dt

IMPORTANT!
You just need to do this step the first time you're building/starting the container

🌐 Test the API

Open Swagger UI: http://localhost:8000/docs


🛠️ Useful Commands

Stop services:

docker-compose down

View logs:

docker-compose logs api
docker-compose logs db

📌 Notes

.env should not be committed, only .env.example.

Always import all models in create_tables.py.

With these steps, you can run PostgreSQL and FastAPI with Docker Compose, then manually initialize tables before testing the CRUD API.

⚠️ Work in progress
- AWS environment variables are defined, but code for that is still in progress
- Documents endpoint is the only endpoint using AWS S3 and Lambda
- Github actions in research too