from fastapi import APIRouter
from typing import Dict

router = APIRouter()

@router.get("/health")
async def get_health() -> Dict[str, str]:
    """Returns the current operational status of the service."""
    return {"status": "healthy"}
