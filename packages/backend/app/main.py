from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(title="PRANELY API")

app.include_router(health_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "PRANELY API"}