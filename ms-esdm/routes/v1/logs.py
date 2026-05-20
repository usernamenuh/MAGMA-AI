from fastapi import APIRouter, Query, Depends

from services.auth_service import require_api_key
from services.logger import load_logs

router = APIRouter()

@router.get("/")
async def get_logs(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100), api_key: str = Depends(require_api_key)):
    logs = await load_logs()
    logs_sorted = sorted(logs, key=lambda x: x["date"], reverse=True)

    start = (page - 1) * limit
    end = start + limit

    return {
        "page": page,
        "limit": limit,
        "total": len(logs_sorted),
        "data": logs_sorted[start:end]
    }
