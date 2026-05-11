# 软土工程智能监测后端服务

本项目是 `soft-soil-ml` 后端服务，用于支撑前端项目 `soft-soil-dashboard`。当前阶段已经完成 FastAPI 基础服务、中文接口文档、CORS 配置、工程项目假数据、钻机设备假数据和规则型风险预测接口。

项目当前仍处于基础后端和假数据接口阶段，但已经完成 PostgreSQL 连接配置、数据库连接测试接口、训练数据表初始化脚本、样例训练数据脚本和 pandas 训练数据读取服务。后续开发应继续保持接口路径稳定，逐步把假数据替换为数据库查询，再把规则预测替换为 scikit-learn 或 PyTorch 模型推理。

## 当前运行环境

推荐在 WSL Ubuntu 中运行：

```bash
cd ~/projects/soft-soil-ml
source ~/anaconda3/etc/profile.d/conda.sh
conda activate cu129_py314_test
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

项目已经提供启动脚本：

```bash
cd ~/projects/soft-soil-ml
./run_backend.sh
```

浏览器访问：

- 后端根接口：http://localhost:8000
- 健康检查：http://localhost:8000/health
- 中文接口文档：http://localhost:8000/docs
- 备用接口文档：http://localhost:8000/redoc

如果出现 `ERROR: [Errno 98] Address already in use`，表示 8000 端口已经有服务在运行。可以直接打开 `http://localhost:8000/docs` 查看，或用下面命令检查端口：

```bash
ss -tulpn | grep 8000
```

## 目录结构审查

```text
soft-soil-ml/
├── src/
│   ├── main.py
│   ├── db.py
│   ├── routers/
│   ├── services/
│   ├── schemas/
│   ├── models/
│   └── ml/
├── configs/
├── sql/
├── data/
├── notebooks/
├── outputs/
├── scripts/
├── tests/
├── requirements.txt
├── run_backend.sh
└── README.md
```

### `src/`

后端主代码目录。

### `src/main.py`

FastAPI 应用入口文件，负责：

- 创建 FastAPI 应用；
- 配置中文 OpenAPI 文档；
- 配置 CORS；
- 注册各个业务路由；
- 提供根接口 `GET /`。

当前 CORS 允许以下前端地址访问：

```text
http://localhost:5173
http://127.0.0.1:5173
```

### `src/routers/`

API 路由目录。路由文件只负责接收请求、调用服务层、返回结果，不直接写复杂业务逻辑。

当前文件：

- `health.py`：健康检查接口；
- `projects.py`：工程项目接口；
- `machines.py`：钻机设备接口；
- `predict.py`：施工风险预测接口；
- `__init__.py`：Python 包标记文件。

### `src/services/`

业务服务层目录。当前主要存放假数据和规则逻辑，方便以后替换为数据库查询或模型推理。

当前文件：

- `project_service.py`：集中维护工程项目假数据；
- `machine_service.py`：集中维护钻机设备和实时施工参数假数据；
- `predict_service.py`：集中维护风险预测规则；
- `__init__.py`：Python 包标记文件。

这种拆分方式可以避免把所有逻辑堆在 `src/main.py` 或路由文件里，后续维护更清楚。

### `src/schemas/`

请求体和响应数据结构目录，基于 Pydantic。

当前文件：

- `predict_schema.py`：定义 `POST /api/predict/risk` 的请求体字段；
- `__init__.py`：Python 包标记文件。

`MachineDataInput` 当前字段包括：

- `current_value`：钻机电流值；
- `torque`：钻机扭矩；
- `penetration_speed`：下贯速度；
- `grouting_pressure`：注浆压力；
- `drilling_depth`：钻进深度。

这些字段会显示在 `http://localhost:8000/docs` 的中文接口文档中。

### `src/models/`

数据库 ORM 模型目录。当前还没有正式模型文件，仅有 `__init__.py`。

后续接入 PostgreSQL 和 SQLAlchemy 后，建议逐步添加：

- `project.py`
- `machine.py`
- `borehole.py`
- `soil_layer.py`
- `prediction.py`

### `src/ml/`

机器学习和深度学习代码目录。当前只有包初始化文件和 `saved_models/` 目录。

后续建议存放：

- `train.py`：模型训练入口；
- `inference.py`：模型加载和推理逻辑；
- `saved_models/`：保存训练好的模型文件。

### `src/db.py`

数据库连接文件。当前已经改为从 `.env` 读取 `DATABASE_URL`，不再在 Python 源码中硬编码数据库账号和密码。

如果 `.env` 中没有配置 `DATABASE_URL`，该模块会抛出清晰错误，提醒维护者检查环境配置。

### `src/config.py`

统一配置文件。当前负责读取：

- `DATABASE_URL`：PostgreSQL 连接地址；
- `BACKEND_HOST`：后端监听地址，默认 `0.0.0.0`；
- `BACKEND_PORT`：后端端口，默认 `8000`；
- `MODEL_DIR`、`RISK_MODEL_PATH`、`MODEL_METADATA_PATH`：后续模型保存和加载路径。

真实数据库密码只应写在本机 `.env` 中，不要写入 Python 代码，也不要提交到 Git。

### `configs/`

配置目录。当前提供：

- `database.example.yaml`

真实数据库密码不要提交到 Git。维护者可以参考 `database.example.yaml` 或 `.env.example`，在本机创建自己的 `.env`。

### `sql/`

数据库 SQL 脚本目录。当前有：

- `01_create_tables.sql`

该脚本目前包含：

- `machine_data`
- `model_predictions`
- `model_runs`

它更偏向已有机器施工数据和模型运行记录的初版表结构。与开发指南中建议的 `projects`、`machines`、`boreholes`、`soil_layers`、`machine_realtime_data` 等表还没有完全对齐。进入数据库阶段时，建议重新整理 SQL 表结构。

### `data/`

数据目录，当前只有目录结构，没有实际数据文件。

当前子目录：

- `raw/`：原始数据；
- `interim/`：中间处理数据；
- `processed/`：清洗后的数据；
- `external/`：外部来源数据。

建议不要把大型数据文件直接提交到 Git，后续可在 README 或数据说明文件中记录数据来源和生成方式。

### `notebooks/`

Jupyter Notebook 分析目录。当前为空。

后续用于：

- 读取 PostgreSQL 施工数据；
- 使用 pandas 清洗数据；
- 分析钻机参数；
- 构建训练集；
- 训练 scikit-learn 或 PyTorch 模型。

启动命令：

```bash
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
```

### `outputs/`

实验输出目录。当前已有子目录：

- `checkpoints/`：训练过程检查点；
- `figures/`：图表输出；
- `logs/`：日志输出；
- `reports/`：分析报告输出。

当前没有实际输出文件。

### `scripts/`

脚本目录。当前包含数据库连接检查、数据库表初始化和样例训练数据脚本。

当前文件：

- `check_db_connection.py`：读取 `.env` 并测试 PostgreSQL 连接；
- `init_db.sql`：创建 `projects`、`machines`、`machine_realtime_data`、`machine_training_data`、`model_predictions`；
- `seed_sample_data.sql`：插入示例项目、设备和训练数据。

后续还可继续放数据导入、数据清洗和模型训练辅助脚本。

### `tests/`

测试目录。当前为空。

后续建议补充：

- FastAPI 路由测试；
- 服务层函数测试；
- 预测规则测试；
- 数据库连接测试。

### `.venv/`

历史创建的 Python 虚拟环境目录。当前项目实际运行环境已经切换为 conda 环境 `cu129_py314_test`，所以 `.venv/` 不作为推荐运行环境。

如果后续使用 Git，建议把 `.venv/` 加入 `.gitignore`。

### `__pycache__/`

Python 运行后自动生成的字节码缓存目录。它们不是手写代码，也不需要人工维护。

如果后续使用 Git，建议把 `__pycache__/` 加入 `.gitignore`。

## 当前接口清单

### `GET /`

后端根接口，用于确认服务是否启动。

返回示例：

```json
{
  "message": "软土工程智能监测后端服务正在运行",
  "docs": "http://localhost:8000/docs"
}
```

### `GET /health`

健康检查接口。

返回示例：

```json
{
  "status": "ok",
  "message": "后端服务运行正常"
}
```

### `GET /api/projects/`

获取工程项目列表。当前返回假数据。

### `GET /api/projects/{project_id}`

根据工程项目编号获取项目详情。当前返回假数据。

示例：

```text
http://localhost:8000/api/projects/P001
```

### `GET /api/machines/`

获取钻机设备列表。当前返回假数据。

### `GET /api/machines/{machine_id}`

根据钻机编号获取设备详情。当前返回假数据。

示例：

```text
http://localhost:8000/api/machines/M001
```

### `GET /api/machines/{machine_id}/realtime`

获取钻机实时施工参数。当前返回假数据。

示例：

```text
http://localhost:8000/api/machines/M001/realtime
```

### `POST /api/predict/risk`

施工风险预测接口。当前使用规则打分，不使用真实机器学习模型。

测试输入：

```json
{
  "current_value": 160,
  "torque": 55,
  "penetration_speed": 1.2,
  "grouting_pressure": 2.2,
  "drilling_depth": 12.4
}
```

返回示例：

```json
{
  "risk_level": "high",
  "risk_text": "高风险",
  "score": 3,
  "reason": "判定为高风险，主要原因：电流值偏高、扭矩偏高、注浆压力偏高。",
  "input": {
    "current_value": 160.0,
    "torque": 55.0,
    "penetration_speed": 1.2,
    "grouting_pressure": 2.2,
    "drilling_depth": 12.4
  }
}
```

### `GET /api/db-test`

数据库连接测试接口。该接口会通过 `.env` 中的 `DATABASE_URL` 连接 PostgreSQL，并返回当前数据库名和数据库用户。

返回示例：

```json
{
  "current_database": "soft_soil_db",
  "current_user": "postgres"
}
```

## 浏览器测试方式

启动后端后，在 Windows 浏览器中打开：

```text
http://localhost:8000/docs
```

在页面中可以看到中文分组：

- 健康检查
- 工程项目
- 设备钻机
- 模型预测

测试 `POST /api/predict/risk`：

1. 打开 `http://localhost:8000/docs`；
2. 找到“模型预测”；
3. 展开 `POST /api/predict/risk`；
4. 点击 `Try it out`；
5. 填入测试 JSON；
6. 点击 `Execute`。

## 命令行测试方式

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/projects/
curl http://127.0.0.1:8000/api/machines/
curl http://127.0.0.1:8000/api/machines/M001/realtime
```

预测接口测试：

```bash
curl -X POST http://127.0.0.1:8000/api/predict/risk \
  -H "Content-Type: application/json" \
  -d '{"current_value":160,"torque":55,"penetration_speed":1.2,"grouting_pressure":2.2,"drilling_depth":12.4}'
```

## 当前完成阶段

已完成：

- Phase 1：FastAPI 基础后端；
- Phase 2：工程项目、钻机设备、风险预测假数据接口；
- 中文 Swagger 文档；
- CORS 配置；
- conda 启动脚本；
- 服务层和 schema 初步拆分。
- `.env` 方式管理 PostgreSQL 连接；
- SQLAlchemy 数据库连接模块；
- `GET /api/db-test` 数据库连接测试接口；
- `scripts/check_db_connection.py` 命令行数据库连接测试；
- `scripts/init_db.sql` 基础表结构初始化；
- `scripts/seed_sample_data.sql` 样例训练数据插入；
- `src/services/training_data_service.py` 使用 pandas 读取训练数据。

尚未完成：

- ORM 模型；
- 数据库查询替换假数据接口；
- Jupyter 数据分析；
- 真实机器学习模型训练；
- 模型加载和推理服务；
- 自动化测试。

## PostgreSQL 与训练数据当前状态

当前后端已经可以通过 `.env` 中的 `DATABASE_URL` 连接 PostgreSQL。连接测试已经验证通过，数据库为 `soft_soil_db`，用户为 `postgres`。

命令行测试：

```bash
cd ~/projects/soft-soil-ml
source ~/anaconda3/etc/profile.d/conda.sh
conda activate cu129_py314_test
python scripts/check_db_connection.py
```

初始化数据库表：

```bash
cd ~/projects/soft-soil-ml
psql -U postgres -d soft_soil_db -f scripts/init_db.sql
```

插入样例训练数据：

```bash
psql -U postgres -d soft_soil_db -f scripts/seed_sample_data.sql
```

如果 WSL 中暂时不方便使用 `psql`，也可以将 `scripts/init_db.sql` 和 `scripts/seed_sample_data.sql` 的内容复制到 pgAdmin 中执行。

读取训练数据：

```bash
python -c "from src.services.training_data_service import load_training_data; print(load_training_data().head())"
```

当前训练数据来自 PostgreSQL 表 `machine_training_data`，字段包括：

- `current_value`
- `torque`
- `penetration_speed`
- `grouting_pressure`
- `drilling_depth`
- `risk_level`

这些字段已经可以作为后续 scikit-learn 或 PyTorch 风险分类模型的第一版输入数据。

## 是否可以开始录入数据和写训练代码

可以开始录入数据。推荐先向 PostgreSQL 的 `machine_training_data` 表录入训练样本。每条样本至少需要包含：

- `current_value`
- `torque`
- `penetration_speed`
- `grouting_pressure`
- `drilling_depth`
- `risk_level`

其中 `risk_level` 建议先使用：

- `low`
- `medium`
- `high`

也可以开始在 Jupyter 中写训练代码。推荐顺序是：

1. 先在 Notebook 中调用 `load_training_data()` 读取 PostgreSQL 数据；
2. 检查空值、异常值和标签分布；
3. 先训练一个 scikit-learn 基准模型，例如 RandomForestClassifier；
4. 确认数据链路、标签质量和保存路径都稳定后，再写 PyTorch 深度学习模型。

不建议一上来直接写复杂深度学习模型。当前样例数据只有少量记录，适合验证链路，不适合训练真正可靠的深度学习模型。深度学习训练需要更多真实施工数据，否则模型只会记住样例，无法泛化。

## 当前风险和整改建议

1. 数据库连接已经改为通过 `.env` 读取，上传 Git 前不要提交真实 `.env`。

   建议：只提交 `.env.example`，每台机器自己维护本地 `.env`。

2. `configs/database.yaml` 已加入 `.gitignore`，避免误传真实密码。

   建议：只提交 `configs/database.example.yaml` 作为示例。

3. `.venv/` 与当前 conda 环境并存。

   建议：统一使用 `cu129_py314_test`，并在 Git 中忽略 `.venv/`。

4. `__pycache__/` 已生成。

   建议：加入 `.gitignore`，不提交缓存文件。

5. `requirements.txt` 目前只有最小依赖。

   当前内容适合基础 FastAPI 阶段。后续接入数据库和机器学习后，需要补充：

   - `sqlalchemy`
   - `psycopg2-binary`
   - `python-dotenv`
   - `pandas`
   - `numpy`
   - `scikit-learn`
   - `matplotlib`
   - `jupyter`
   - `torch`

6. SQL 表结构与开发指南还没有完全一致。

   建议：数据库阶段重新设计 `projects`、`machines`、`boreholes`、`soil_layers`、`machine_realtime_data`、`model_predictions`。

## 后续开发路线

建议按以下顺序继续：

1. 在 `notebooks/` 中创建训练数据读取和分析 Notebook；
2. 建立 scikit-learn 风险分类基准模型训练脚本；
3. 将训练模型保存到 `src/ml/saved_models/`；
4. 创建模型加载和推理模块；
5. 将 `predict_service.py` 中的规则预测升级为“模型优先、规则兜底”；
6. 将预测结果写入 `model_predictions`；
7. 将 `/api/projects`、`/api/machines` 等假数据接口逐步替换为数据库查询；
8. 在 `tests/` 中补充接口测试和服务层测试；
9. 数据量足够后，再引入 PyTorch 深度学习训练脚本。

## 一句话总结

当前项目已经具备“前端可访问的中文 FastAPI 假数据后端 + PostgreSQL 训练数据读取基础链路”能力。下一阶段重点是在不改变前端接口路径的前提下，先完成数据分析和 scikit-learn 基准模型，再逐步把规则预测升级为真实模型推理。
