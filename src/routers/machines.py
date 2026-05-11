from fastapi import APIRouter, Path

from src.services.machine_service import (
    get_machine_by_id,
    get_machine_list,
    get_machine_realtime_data,
)

router = APIRouter(prefix="/api/machines", tags=["设备钻机"])


@router.get(
    "/",
    summary="获取钻机设备列表",
    description="返回当前工程中的钻机设备假数据列表，包括设备状态和经纬度。",
)
def get_machines():
    return get_machine_list()


@router.get(
    "/{machine_id}",
    summary="获取钻机设备详情",
    description="根据设备编号返回单台钻机的详情假数据。",
)
def get_machine_detail(
    machine_id: str = Path(..., description="钻机设备编号，例如 M001"),
):
    return get_machine_by_id(machine_id)


@router.get(
    "/{machine_id}/realtime",
    summary="获取钻机实时施工数据",
    description="根据设备编号返回单台钻机的实时施工参数假数据。",
)
def get_machine_realtime(
    machine_id: str = Path(..., description="钻机设备编号，例如 M001"),
):
    return get_machine_realtime_data(machine_id)
