from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get(
    "/health",
    summary="健康检查",
    description="用于快速确认 FastAPI 后端服务是否正常运行。",
)
def health_check():
    return {
        "status": "ok",
        "message": "后端服务运行正常",
    }
