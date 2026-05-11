from fastapi import APIRouter

from src.db import test_connection

router = APIRouter(prefix="/api", tags=["database"])


@router.get(
    "/db-test",
    summary="测试数据库连接",
    description="返回当前连接的 PostgreSQL 数据库名和数据库用户。",
)
def db_test():
    return test_connection()
