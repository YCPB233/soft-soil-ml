"""工程项目假数据服务。

当前阶段还没有连接 PostgreSQL，所以这里先集中维护工程项目的假数据。
后续接入数据库时，可以保持路由路径不变，只替换本文件中的查询逻辑。
"""


def get_project_list():
    """返回工程项目列表假数据。"""
    return [
        {
            "id": "P001",
            "name": "宁波大学西区学生公寓项目",
            "location": "宁波市",
            "status": "施工中",
        },
        {
            "id": "P002",
            "name": "示范工程项目",
            "location": "宁波市",
            "status": "演示",
        },
    ]


def get_project_by_id(project_id: str):
    """根据项目编号返回工程项目详情假数据。"""
    return {
        "id": project_id,
        "name": "宁波大学西区学生公寓项目",
        "location": "宁波市",
        "description": "用于软土地基施工监测与智能分析的示范项目",
    }
