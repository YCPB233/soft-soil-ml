from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import health, machines, predict, projects

tags_metadata = [
    {
        "name": "健康检查",
        "description": "用于确认后端服务是否正常运行。",
    },
    {
        "name": "工程项目",
        "description": "提供工程项目列表和项目详情的假数据接口。",
    },
    {
        "name": "设备钻机",
        "description": "提供钻机设备列表、设备详情和实时施工数据的假数据接口。",
    },
    {
        "name": "模型预测",
        "description": "提供基于规则的风险等级预测示例接口，当前不连接真实模型。",
    },
]

app = FastAPI(
    title="软土工程智能监测后端服务",
    description=(
        "Soft Soil ML Backend 基础版。当前阶段仅提供 FastAPI 基础结构、"
        "CORS 配置和假数据接口，暂不连接 PostgreSQL 数据库。"
    ),
    version="0.1.0",
    openapi_tags=tags_metadata,
)

# 允许本地 React / Vite 前端在开发阶段访问后端接口。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(machines.router)
app.include_router(predict.router)


@app.get(
    "/",
    summary="后端根接口",
    description="返回后端服务运行状态和接口文档地址。",
)
def root():
    return {
        "message": "软土工程智能监测后端服务正在运行",
        "docs": "http://localhost:8000/docs",
    }
