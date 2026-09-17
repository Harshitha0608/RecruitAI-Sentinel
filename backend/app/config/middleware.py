from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config.settings import settings

def setup_middleware(app: FastAPI) -> None:
    """Registers standard middlewares, including CORS filters."""
    origins = [
        "http://localhost:3000",      # Default Next.js dev port
        "http://127.0.0.1:3000",
    ]
    
    # In local/testing mode, we can allow broader origins
    if settings.ENVIRONMENT == "local":
        origins = ["*"]
        
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True if origins != ["*"] else False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
