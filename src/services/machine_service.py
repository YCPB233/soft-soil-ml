"""钻机设备假数据服务。

当前阶段接口先返回固定假数据，方便前端页面调试。
后续接入 PostgreSQL 时，可在这里替换为数据库查询。
"""


def get_machine_list():
    """返回钻机设备列表假数据。"""
    return [
        {
            "id": "M001",
            "name": "钻机 1 号",
            "project_id": "P001",
            "status": "working",
            "latitude": 29.818,
            "longitude": 121.558,
        },
        {
            "id": "M002",
            "name": "钻机 2 号",
            "project_id": "P001",
            "status": "idle",
            "latitude": 29.819,
            "longitude": 121.559,
        },
    ]


def get_machine_by_id(machine_id: str):
    """根据设备编号返回单台钻机详情假数据。"""
    return {
        "id": machine_id,
        "name": f"钻机 {machine_id}",
        "status": "working",
        "current_value": 120.5,
        "torque": 35.2,
        "penetration_speed": 0.8,
        "grouting_pressure": 1.6,
        "drilling_depth": 12.4,
    }


def get_machine_realtime_data(machine_id: str):
    """根据设备编号返回实时施工参数假数据。"""
    return {
        "machine_id": machine_id,
        "timestamp": "2026-05-11 10:30:00",
        "current_value": 120.5,
        "torque": 35.2,
        "penetration_speed": 0.8,
        "grouting_pressure": 1.6,
        "drilling_depth": 12.4,
        "latitude": 29.818,
        "longitude": 121.558,
        "risk_level": "medium",
    }
