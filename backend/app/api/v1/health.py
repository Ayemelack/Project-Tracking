from fastapi import APIRouter
from app.schemas.schemas import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="healthy", version="1.0.0")
