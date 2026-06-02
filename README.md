FastAPI + PostgreSQL CRUD

This project implements a CRUD API using FastAPI, PostgreSQL and Docker Compose. The API includes user registration, login, project management and document upload functionality.

Requirements

- Docker and Docker Compose installed
- PostgreSQL image available through Docker
- Python 3.12 image available (used by Dockerfile)

Project files

- docker-compose.yml: defines API and DB services
- Dockerfile: builds the API image
- requirements.txt: Python dependencies
- create_tables.py: initializes database tables manually
- models/: contains SQLAlchemy models
- routes/: contains FastAPI routers for auth, login, projects, projects, project and documents
- utils/: helper functions and database session management
- validation_schemas/: Pydantic schemas for requests/responses
- .env.example: environment variables template

Environment variables

Copy `.env.example` to `.env` and set the values for your environment.

At minimum, set:

- `SECRET_KEY`
- `ALGORITHM`
- `DATABASE_URL`
- AWS variables if you use the document upload endpoint

Setup

1. Build and start the containers:

   docker compose up --build -d

2. Create the database tables manually:

   docker compose exec api python create_tables.py

3. Verify tables in PostgreSQL:

   docker compose exec db psql -U postgres -d projectdb -c "\dt"

Important: This manual table creation only needs to be done the first time the database is initialized.

API Endpoints

- `POST /auth` - register a new user
- `POST /login` - authenticate and receive a JWT token
- `POST /projects` - create a new project (requires auth)
- `GET /projects` - list user projects (requires auth)
- `GET /project/{project_id}/info` - get project details (requires auth)
- `DELETE /project/{project_id}` - delete a project (requires auth)
- `POST /project/{project_id}/invite` - invite a user to a project (requires auth)
- `PUT /project/{project_id}/info` - update project details (requires auth)
- `POST /project/{project_id}/documents` - upload a document to a project (requires auth)
- `GET /project/{project_id}/documents` - list project documents (requires auth)
- `GET /document/{document_id}` - get a document record
- `PUT /document/{document_id}` - update a document record
- `DELETE /document/{document_id}` - delete a document record

Authentication

Most routes require a Bearer JWT token in the `Authorization` header. Obtain it with `POST /login`.

Test the API

Open Swagger UI: http://localhost:8000/docs

Useful commands

- Stop services:

  docker compose down

- View logs:

  docker compose logs api
  docker compose logs db

Notes

- `.env` should not be committed; only `.env.example` should be tracked.
- `create_tables.py` imports all models and creates the database schema.
- The project uses JWT auth and FastAPI dependencies to protect routes.

Work in progress
- GitHub Actions are under research