from fastapi import APIRouter
from app.api.v1 import estimates, health, funds, allocations, expenses, resources, schedule, auth, assistant

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(estimates.router, prefix="/estimates", tags=["Estimates"])
router.include_router(funds.router, prefix="/funds", tags=["Funds"])
router.include_router(allocations.router, prefix="/allocations", tags=["Allocations"])
router.include_router(expenses.router, prefix="/expenses", tags=["Expenses"])
router.include_router(resources.router, prefix="/resources", tags=["Resources"])
router.include_router(schedule.router, prefix="/schedule", tags=["Schedule"])
router.include_router(assistant.router, prefix="/assistant", tags=["Assistant"])
