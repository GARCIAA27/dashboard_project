from fastapi import FastAPI
from routes import auth, login, projects

app = FastAPI()
app.include_router(auth.router)
app.include_router(login.router)
app.include_router(projects.router)