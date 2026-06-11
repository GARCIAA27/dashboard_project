from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from routes import auth, document, login, project, projects

app = FastAPI()
app.include_router(auth.router)
app.include_router(login.router)
app.include_router(projects.router)
app.include_router(project.router)
app.include_router(document.router)
app.title = "Project Dashboard API"

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Dashboard API",
        version="1.0.0",
        description="API con JWT",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
