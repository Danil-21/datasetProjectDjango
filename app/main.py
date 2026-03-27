from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routes import projects, tasks, annotations

# Создаём таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Dataset Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для демо можно так
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(annotations.router, tags=["Annotations"])


@app.get("/")
def root():
    return {"message": "API is working"}