from fastapi import APIRouter, Path

from src.services.project_service import get_project_by_id, get_project_list

router = APIRouter(prefix="/api/projects", tags=["工程项目"])


@router.get(
    "/",
    summary="获取工程项目列表",
    description="返回当前系统中的工程项目假数据列表，后续可替换为数据库查询结果。",
)
def get_projects():
    return get_project_list()


@router.get(
    "/{project_id}",
    summary="获取工程项目详情",
    description="根据项目编号返回单个工程项目的详情假数据。",
)
def get_project_detail(
    project_id: str = Path(..., description="工程项目编号，例如 P001"),
):
    return get_project_by_id(project_id)
