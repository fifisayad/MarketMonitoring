from fastapi import FastAPI
from src.api.routes import subscription

app = FastAPI()

app.include_router(subscription.router)
