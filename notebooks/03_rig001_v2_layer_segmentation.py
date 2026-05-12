# %%
"""RIG-001 v2 数据土层划分实验。

目标：
基于新导入的 NBU-WEST-DEMO / BH-001 钻机数据，判断钻机响应在深度方向上
是否进入不同土层，并输出钻机响应意义下的分段 L1, L2, ...

说明：
这不是直接分类“杂填土/粉质黏土”等地层名称，而是先用钻机数据识别
施工响应变化边界，再与地勘报告边界进行对比校核。
"""

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv

try:
    from IPython.display import display
except ImportError:
    def display(obj):
        print(obj)

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.db import get_engine  # noqa: E402

engine = get_engine()
PROJECT_ROOT

# %%
# 1. 读取新钻机数据和地层报告数据
machine_code = "RIG-001"
project_code = "NBU-WEST-DEMO"
borehole_code = "BH-001"

rig_df = pd.read_sql(
    """
    SELECT
        timestamp,
        machine_code,
        project_code,
        borehole_code,
        drilling_depth,
        current_value,
        torque,
        penetration_speed,
        grouting_pressure,
        rotation_speed_rpm,
        mud_density_g_cm3,
        pump_flow_l_min,
        verticality_deg,
        latitude,
        longitude
    FROM machine_realtime_data
    WHERE machine_code = %(machine_code)s
      AND project_code = %(project_code)s
      AND borehole_code = %(borehole_code)s
    ORDER BY timestamp
    """,
    engine,
    params={
        "machine_code": machine_code,
        "project_code": project_code,
        "borehole_code": borehole_code,
    },
)

soil_df = pd.read_sql(
    """
    SELECT
        stratum_order,
        layer_code,
        layer_name,
        top_depth_representative_m,
        bottom_depth_representative_m,
        engineering_group
    FROM soil_layers
    ORDER BY stratum_order
    """,
    engine,
)

print("rig_df:", rig_df.shape)
print("soil_df:", soil_df.shape)
display(rig_df.head())
display(soil_df.head())

# %%
# 2. 基础清洗
feature_cols = [
    "current_value",
    "torque",
    "penetration_speed",
    "grouting_pressure",
    "rotation_speed_rpm",
    "mud_density_g_cm3",
    "pump_flow_l_min",
    "verticality_deg",
]

df = rig_df.copy()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.dropna(subset=["timestamp", "drilling_depth"]).copy()

for col in feature_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df[col] = df[col].interpolate().ffill().bfill()

df = df.sort_values("timestamp").reset_index(drop=True)
df["dt_s"] = df["timestamp"].diff().dt.total_seconds().fillna(1)
df["depth_diff"] = df["drilling_depth"].diff().fillna(0)

print("清洗后数据规模:", df.shape)
print("深度范围:", df["drilling_depth"].min(), df["drilling_depth"].max())
display(df.head())

# %%
# 3. 计算 DRI 钻进阻抗指数
# DRI 只作为工程启发特征，后续可以按现场经验调整权重。
dri_cols = [
    "current_value",
    "torque",
    "grouting_pressure",
    "penetration_speed",
]

dri_values = df[dri_cols]
dri_z = (dri_values - dri_values.mean()) / dri_values.std(ddof=0).replace(0, 1)

df["DRI"] = (
    0.30 * dri_z["current_value"]
    + 0.30 * dri_z["torque"]
    + 0.25 * dri_z["grouting_pressure"]
    - 0.15 * dri_z["penetration_speed"]
)

display(
    df[
        [
            "drilling_depth",
            "current_value",
            "torque",
            "penetration_speed",
            "grouting_pressure",
            "DRI",
        ]
    ].head()
)

# %%
# 4. 按深度重采样
# 新数据为 drilling_only，仍然保留速度过滤，避免异常静止点影响分段。
depth_bin_m = 0.05
speed_threshold = 0.001

depth_source = df[df["penetration_speed"].fillna(0) > speed_threshold].copy()
depth_source["depth_bin"] = (
    (depth_source["drilling_depth"] / depth_bin_m).round() * depth_bin_m
)

depth_df = (
    depth_source.groupby("depth_bin", as_index=False)
    .agg(
        {
            "current_value": "median",
            "torque": "median",
            "penetration_speed": "median",
            "grouting_pressure": "median",
            "rotation_speed_rpm": "median",
            "mud_density_g_cm3": "median",
            "pump_flow_l_min": "median",
            "verticality_deg": "median",
            "DRI": "median",
        }
    )
    .rename(columns={"depth_bin": "drilling_depth"})
    .sort_values("drilling_depth")
    .reset_index(drop=True)
)

print("重采样后数据规模:", depth_df.shape)
display(depth_df.head())

# %%
# 5. 鲁棒标准化和平滑
signal_cols = [
    "current_value",
    "torque",
    "penetration_speed",
    "grouting_pressure",
    "rotation_speed_rpm",
    "mud_density_g_cm3",
    "pump_flow_l_min",
    "verticality_deg",
    "DRI",
]

X = depth_df[signal_cols].copy()
median = X.median()
iqr = (X.quantile(0.75) - X.quantile(0.25)).replace(0, 1)

Z = (X - median) / iqr
Z_smooth = Z.rolling(window=5, center=True, min_periods=1).median()

display(Z_smooth.head())

# %%
# 6. 左右窗口变化检测
# 参数可以调：
# - left_right_window_m 越小，越容易识别薄层；
# - score_quantile 越低，边界越多；
# - min_gap_m 越小，相邻边界越不容易被合并。
left_right_window_m = 0.5
score_quantile = 0.88
min_gap_m = 0.45

window_bins = max(3, int(left_right_window_m / depth_bin_m))
Z_values = Z_smooth.values
scores = []

for i in range(len(depth_df)):
    left_start = max(0, i - window_bins)
    left_end = i
    right_start = i + 1
    right_end = min(len(depth_df), i + 1 + window_bins)

    if (
        left_end - left_start < window_bins // 2
        or right_end - right_start < window_bins // 2
    ):
        scores.append(0.0)
        continue

    left_mean = Z_values[left_start:left_end].mean(axis=0)
    right_mean = Z_values[right_start:right_end].mean(axis=0)
    scores.append(float(np.linalg.norm(right_mean - left_mean)))

depth_df["change_score"] = scores
depth_df["change_score_smooth"] = (
    depth_df["change_score"].rolling(window=3, center=True, min_periods=1).mean()
)

threshold = depth_df["change_score_smooth"].quantile(score_quantile)
candidate_df = depth_df[depth_df["change_score_smooth"] >= threshold].copy()

boundary_rows = []
for _, row in candidate_df.sort_values("drilling_depth").iterrows():
    depth = row["drilling_depth"]

    if not boundary_rows:
        boundary_rows.append(row)
        continue

    last_depth = boundary_rows[-1]["drilling_depth"]
    if depth - last_depth < min_gap_m:
        if row["change_score_smooth"] > boundary_rows[-1]["change_score_smooth"]:
            boundary_rows[-1] = row
    else:
        boundary_rows.append(row)

detected_boundaries_df = pd.DataFrame(boundary_rows)
if not detected_boundaries_df.empty:
    detected_boundaries_df = (
        detected_boundaries_df[["drilling_depth", "change_score_smooth"]]
        .rename(columns={"drilling_depth": "boundary_depth"})
        .reset_index(drop=True)
    )

print("变化阈值:", threshold)
print("检测边界数量:", len(detected_boundaries_df))
display(detected_boundaries_df)

# %%
# 7. 给边界分强弱等级
q90 = depth_df["change_score_smooth"].quantile(0.90)
q95 = depth_df["change_score_smooth"].quantile(0.95)
q98 = depth_df["change_score_smooth"].quantile(0.98)


def boundary_strength(score):
    if score >= q98:
        return "strong"
    if score >= q95:
        return "medium"
    if score >= q90:
        return "weak"
    return "candidate"


detected_boundaries_df["strength"] = detected_boundaries_df[
    "change_score_smooth"
].apply(boundary_strength)

display(detected_boundaries_df)

# %%
# 8. 根据边界划分钻机响应土层段 L1, L2, ...
boundaries = (
    detected_boundaries_df["boundary_depth"].dropna().sort_values().tolist()
)

min_depth = depth_df["drilling_depth"].min()
max_depth = depth_df["drilling_depth"].max()
layer_edges = [min_depth] + boundaries + [max_depth]

detected_segments = []

for i in range(len(layer_edges) - 1):
    start_depth = layer_edges[i]
    end_depth = layer_edges[i + 1]

    if i == 0:
        mask = (
            (depth_df["drilling_depth"] >= start_depth)
            & (depth_df["drilling_depth"] <= end_depth)
        )
    else:
        mask = (
            (depth_df["drilling_depth"] > start_depth)
            & (depth_df["drilling_depth"] <= end_depth)
        )

    seg = depth_df[mask]

    detected_segments.append(
        {
            "detected_layer_index": i + 1,
            "start_depth": start_depth,
            "end_depth": end_depth,
            "thickness": end_depth - start_depth,
            "sample_count": len(seg),
            "current_mean": seg["current_value"].mean(),
            "torque_mean": seg["torque"].mean(),
            "penetration_speed_mean": seg["penetration_speed"].mean(),
            "grouting_pressure_mean": seg["grouting_pressure"].mean(),
            "rotation_speed_mean": seg["rotation_speed_rpm"].mean(),
            "mud_density_mean": seg["mud_density_g_cm3"].mean(),
            "pump_flow_mean": seg["pump_flow_l_min"].mean(),
            "verticality_mean": seg["verticality_deg"].mean(),
            "DRI_mean": seg["DRI"].mean(),
            "change_score_mean": seg["change_score_smooth"].mean(),
        }
    )

detected_segments_df = pd.DataFrame(detected_segments)
display(detected_segments_df)

# %%
# 9. 与地勘报告边界对比
report_boundaries = (
    soil_df["bottom_depth_representative_m"]
    .dropna()
    .astype(float)
    .sort_values()
    .tolist()
)

comparison_rows = []
for detected in boundaries:
    nearest = min(report_boundaries, key=lambda x: abs(x - detected))
    comparison_rows.append(
        {
            "detected_boundary_depth": detected,
            "nearest_report_boundary_depth": nearest,
            "offset_m": detected - nearest,
            "abs_offset_m": abs(detected - nearest),
        }
    )

comparison_df = pd.DataFrame(comparison_rows)
display(comparison_df)

# %%
# 10. 图 1：变化强度曲线
plt.figure(figsize=(14, 5))
plt.plot(depth_df["drilling_depth"], depth_df["change_score_smooth"], label="change score")

for _, row in detected_boundaries_df.iterrows():
    plt.axvline(row["boundary_depth"], color="red", linestyle="--", alpha=0.65)

for idx, depth in enumerate(report_boundaries):
    plt.axvline(
        depth,
        color="blue",
        linestyle=":",
        alpha=0.25,
        label="report boundary" if idx == 0 else None,
    )

plt.xlabel("drilling_depth (m)")
plt.ylabel("change score")
plt.title("Detected Boundaries vs Geotech Report Boundaries")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()

# %%
# 11. 图 2：钻机响应分段
plot_cols = [
    "current_value",
    "torque",
    "grouting_pressure",
    "rotation_speed_rpm",
    "pump_flow_l_min",
    "DRI",
]

color_map = {"strong": "red", "medium": "orange", "weak": "gray", "candidate": "lightgray"}

plt.figure(figsize=(14, 6))

for col in plot_cols:
    y = depth_df[col]
    y_norm = (y - y.min()) / (y.max() - y.min() + 1e-9)
    plt.plot(depth_df["drilling_depth"], y_norm, label=col)

for _, row in detected_boundaries_df.iterrows():
    plt.axvline(
        row["boundary_depth"],
        color=color_map[row["strength"]],
        linestyle="--",
        alpha=0.8,
    )

for _, row in detected_segments_df.iterrows():
    mid = (row["start_depth"] + row["end_depth"]) / 2
    plt.text(
        mid,
        1.03,
        f"L{int(row['detected_layer_index'])}",
        ha="center",
        va="bottom",
    )

plt.xlabel("drilling_depth (m)")
plt.ylabel("normalized signal")
plt.title("Rig-Detected Layer Segments")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()

# %%
# 12. 查看最终结果
display(detected_boundaries_df)
display(detected_segments_df)
display(comparison_df)
