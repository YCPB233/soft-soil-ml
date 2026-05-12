# %%
"""单台钻机土层变化检测实验。

目标：
不是直接判断当前属于哪一种土层，而是基于钻机 1Hz 时序响应判断
“钻机是否进入不同土层/是否接近土层变化边界”。

数据来源：
- PostgreSQL: machine_realtime_data
- PostgreSQL: soil_layers

输出：
- 钻机信号变化强度 change_score
- 无监督检测到的疑似土层变化深度 detected_boundaries_df
- 与地勘报告边界的偏差 comparison_df
- 可选：使用地勘边界生成弱标签，训练 RandomForest / Attention-LSTM 二分类模型
"""

# %%
import os
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset


SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.db import get_engine  # noqa: E402


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
device

# %%
# 1. 从数据库读取钻机数据和地层报告数据
engine = get_engine()

machine_code = "RIG-001"

rig_df = pd.read_sql(
    """
    SELECT
        id AS machine_realtime_data_id,
        timestamp,
        machine_code,
        project_code,
        drilling_depth,
        current_value,
        torque,
        penetration_speed,
        grouting_pressure,
        latitude,
        longitude
    FROM machine_realtime_data
    WHERE machine_code = %(machine_code)s
    ORDER BY timestamp
    """,
    engine,
    params={"machine_code": machine_code},
)

soil_df = pd.read_sql(
    """
    SELECT
        stratum_order,
        layer_id_raw,
        layer_code,
        layer_name,
        top_depth_representative_m,
        bottom_depth_representative_m,
        engineering_group,
        description_for_modeling
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
]

required_cols = ["timestamp", "drilling_depth", *feature_cols]
missing = [col for col in required_cols if col not in rig_df.columns]
if missing:
    raise ValueError(f"缺少必要字段：{missing}")

work_df = rig_df.copy()
work_df["timestamp"] = pd.to_datetime(work_df["timestamp"])
work_df = work_df.dropna(subset=["drilling_depth"]).copy()

for col in feature_cols:
    work_df[col] = pd.to_numeric(work_df[col], errors="coerce")
    work_df[col] = work_df[col].interpolate().ffill().bfill()

work_df = work_df.sort_values("drilling_depth").reset_index(drop=True)

print("清洗后数据规模:", work_df.shape)
print("深度范围:", work_df["drilling_depth"].min(), work_df["drilling_depth"].max())
display(work_df[["timestamp", "drilling_depth", *feature_cols]].head())

# %%
# 3. 计算 DRI 钻进阻抗指数
# DRI 只是工程启发特征，不是真实物理量；权重后续可按现场经验调整。
dri_cols = ["current_value", "torque", "grouting_pressure", "penetration_speed"]

dri_scaler = StandardScaler()
dri_scaled = dri_scaler.fit_transform(work_df[dri_cols])

work_df["current_z"] = dri_scaled[:, 0]
work_df["torque_z"] = dri_scaled[:, 1]
work_df["pressure_z"] = dri_scaled[:, 2]
work_df["speed_z"] = dri_scaled[:, 3]

work_df["DRI"] = (
    0.30 * work_df["current_z"]
    + 0.30 * work_df["torque_z"]
    + 0.25 * work_df["pressure_z"]
    - 0.15 * work_df["speed_z"]
)

display(
    work_df[
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
# 4. 按深度重采样，降低 1Hz 时间序列重复深度/停钻对识别的影响
depth_bin_m = 0.05

depth_source = work_df.copy()

# 过滤明显停钻/接杆段。阈值可按现场数据调整。
depth_source = depth_source[depth_source["penetration_speed"].fillna(0) > 0.001].copy()
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
            "DRI": "median",
        }
    )
    .rename(columns={"depth_bin": "drilling_depth"})
    .sort_values("drilling_depth")
    .reset_index(drop=True)
)

print("按深度重采样后:", depth_df.shape)
display(depth_df.head())

# %%
# 5. 鲁棒标准化和平滑
signal_cols = ["current_value", "torque", "penetration_speed", "grouting_pressure", "DRI"]

X = depth_df[signal_cols].copy()
median = X.median()
iqr = X.quantile(0.75) - X.quantile(0.25)
iqr = iqr.replace(0, 1)

Z = (X - median) / iqr
Z_smooth = Z.rolling(window=5, center=True, min_periods=1).median()

for col in signal_cols:
    depth_df[f"{col}_z"] = Z_smooth[col]

display(depth_df[[f"{col}_z" for col in signal_cols]].head())

# %%
# 6. 左右窗口差异检测：判断某深度左右两侧的钻机响应是否发生分布变化
left_right_window_m = 1.0
window_bins = max(3, int(left_right_window_m / depth_bin_m))

Z_values = Z_smooth.values
scores = []

for i in range(len(depth_df)):
    left_start = max(0, i - window_bins)
    left_end = i
    right_start = i + 1
    right_end = min(len(depth_df), i + 1 + window_bins)

    if left_end - left_start < window_bins // 2 or right_end - right_start < window_bins // 2:
        scores.append(0.0)
        continue

    left_mean = Z_values[left_start:left_end].mean(axis=0)
    right_mean = Z_values[right_start:right_end].mean(axis=0)
    score = np.linalg.norm(right_mean - left_mean)
    scores.append(score)

depth_df["change_score"] = scores
depth_df["change_score_smooth"] = (
    depth_df["change_score"].rolling(window=5, center=True, min_periods=1).mean()
)

display(depth_df[["drilling_depth", "change_score_smooth"]].head())

# %%
# 7. 无监督检测疑似进入不同土层的位置
score_quantile = 0.97
min_gap_m = 1.2

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
    detected_boundaries_df = detected_boundaries_df[
        ["drilling_depth", "change_score_smooth"]
    ].rename(columns={"drilling_depth": "boundary_depth"})

print("threshold:", threshold)
display(detected_boundaries_df)

# %%
# 8. 可视化：变化强度与检测边界
plt.figure(figsize=(14, 5))
plt.plot(depth_df["drilling_depth"], depth_df["change_score_smooth"], label="change score")

if not detected_boundaries_df.empty:
    for _, row in detected_boundaries_df.iterrows():
        plt.axvline(row["boundary_depth"], color="red", linestyle="--", alpha=0.7)

plt.xlabel("drilling_depth (m)")
plt.ylabel("change score")
plt.title("Detected Possible Soil Change Boundaries")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()

# %%
# 9. 可视化：钻机信号与检测边界
plot_cols = ["current_value", "torque", "grouting_pressure", "DRI"]

plt.figure(figsize=(14, 6))
for col in plot_cols:
    y = depth_df[col]
    y_plot = (y - y.min()) / (y.max() - y.min() + 1e-9)
    plt.plot(depth_df["drilling_depth"], y_plot, label=f"{col} normalized")

if not detected_boundaries_df.empty:
    for _, row in detected_boundaries_df.iterrows():
        plt.axvline(row["boundary_depth"], color="red", linestyle="--", alpha=0.7)

plt.xlabel("drilling_depth (m)")
plt.ylabel("normalized signal")
plt.title("Rig Signals with Detected Soil Change Boundaries")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()

# %%
# 10. 与地勘报告边界对比。这里只用于校核，不作为绝对真值。
soil_boundaries = (
    soil_df["bottom_depth_representative_m"]
    .dropna()
    .astype(float)
    .sort_values()
    .tolist()
)

comparison_rows = []
if not detected_boundaries_df.empty:
    for detected in detected_boundaries_df["boundary_depth"]:
        nearest = min(soil_boundaries, key=lambda x: abs(x - detected))
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
plt.figure(figsize=(14, 5))
plt.plot(depth_df["drilling_depth"], depth_df["change_score_smooth"], label="rig change score")

if not detected_boundaries_df.empty:
    for idx, row in detected_boundaries_df.iterrows():
        plt.axvline(
            row["boundary_depth"],
            color="red",
            linestyle="--",
            alpha=0.7,
            label="detected boundary" if idx == detected_boundaries_df.index[0] else None,
        )

for idx, boundary in enumerate(soil_boundaries):
    plt.axvline(
        boundary,
        color="blue",
        linestyle=":",
        alpha=0.35,
        label="report boundary" if idx == 0 else None,
    )

plt.xlabel("drilling_depth (m)")
plt.ylabel("change score")
plt.title("Rig-Detected Boundaries vs Geotech Report Boundaries")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()

# %%
# 11. 可选：生成“是否接近地层变化边界”的弱标签
# near_boundary=1: 距离地勘边界很近，认为接近进入不同土层
# near_boundary=0: 离所有边界较远，认为稳定处于同一土层
# ambiguous: 中间区域不用于监督训练
positive_margin_m = 0.35
negative_margin_m = 1.20


def distance_to_nearest_boundary(depth, boundaries):
    return min(abs(depth - boundary) for boundary in boundaries)


depth_df["distance_to_report_boundary_m"] = depth_df["drilling_depth"].apply(
    lambda d: distance_to_nearest_boundary(d, soil_boundaries)
)

depth_df["boundary_label"] = np.nan
depth_df.loc[depth_df["distance_to_report_boundary_m"] <= positive_margin_m, "boundary_label"] = 1
depth_df.loc[depth_df["distance_to_report_boundary_m"] >= negative_margin_m, "boundary_label"] = 0

display(depth_df["boundary_label"].value_counts(dropna=False))

# %%
# 12. RandomForest 二分类基线：判断一个深度点是否接近进入不同土层
rf_feature_cols = [
    "current_value",
    "torque",
    "penetration_speed",
    "grouting_pressure",
    "DRI",
    "change_score_smooth",
]

rf_df = depth_df.dropna(subset=["boundary_label"]).copy()
X_rf = rf_df[rf_feature_cols]
y_rf = rf_df["boundary_label"].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X_rf,
    y_rf,
    test_size=0.2,
    random_state=SEED,
    stratify=y_rf,
)

rf_model = RandomForestClassifier(
    n_estimators=300,
    random_state=SEED,
    class_weight="balanced",
    n_jobs=-1,
)
rf_model.fit(X_train, y_train)
y_pred = rf_model.predict(X_test)

print("RandomForest Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred, target_names=["stable", "near_boundary"]))

cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(cm, display_labels=["stable", "near_boundary"])
disp.plot()
plt.title("RandomForest Boundary Detection Confusion Matrix")
plt.show()

importance_df = pd.DataFrame(
    {"feature": rf_feature_cols, "importance": rf_model.feature_importances_}
).sort_values("importance", ascending=False)
display(importance_df)

# %%
# 13. 可选：Attention-LSTM 二分类序列模型
sequence_features = [
    "current_value",
    "torque",
    "penetration_speed",
    "grouting_pressure",
    "DRI",
    "change_score_smooth",
]

seq_source = depth_df.dropna(subset=["boundary_label"]).copy().reset_index(drop=True)
seq_scaler = StandardScaler()
seq_source[sequence_features] = seq_scaler.fit_transform(seq_source[sequence_features])


def create_sequence_dataset(df, feature_cols, label_col, window_size=30, step_size=5):
    X_seq = []
    y_seq = []

    for start in range(0, len(df) - window_size + 1, step_size):
        end = start + window_size
        window = df.iloc[start:end]
        label = int(window[label_col].mode().iloc[0])
        X_seq.append(window[feature_cols].values.astype(np.float32))
        y_seq.append(label)

    return np.array(X_seq, dtype=np.float32), np.array(y_seq, dtype=np.int64)


X_seq, y_seq = create_sequence_dataset(
    seq_source,
    sequence_features,
    "boundary_label",
    window_size=30,
    step_size=5,
)

print("X_seq:", X_seq.shape)
print("y_seq:", y_seq.shape)
print(pd.Series(y_seq).value_counts())

# %%
X_train_seq, X_temp_seq, y_train_seq, y_temp_seq = train_test_split(
    X_seq,
    y_seq,
    test_size=0.4,
    random_state=SEED,
    stratify=y_seq,
)

X_val_seq, X_test_seq, y_val_seq, y_test_seq = train_test_split(
    X_temp_seq,
    y_temp_seq,
    test_size=0.5,
    random_state=SEED,
    stratify=y_temp_seq,
)


class RigSequenceDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


batch_size = 64
train_loader = DataLoader(
    RigSequenceDataset(X_train_seq, y_train_seq),
    batch_size=batch_size,
    shuffle=True,
)
val_loader = DataLoader(
    RigSequenceDataset(X_val_seq, y_val_seq),
    batch_size=batch_size,
    shuffle=False,
)
test_loader = DataLoader(
    RigSequenceDataset(X_test_seq, y_test_seq),
    batch_size=batch_size,
    shuffle=False,
)


class AttentionLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_classes=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=1,
            batch_first=True,
        )
        self.attention_fc = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attention_scores = self.attention_fc(lstm_out)
        attention_weights = torch.softmax(attention_scores, dim=1)
        context = torch.sum(attention_weights * lstm_out, dim=1)
        logits = self.classifier(self.dropout(context))
        return logits, attention_weights


model = AttentionLSTM(
    input_dim=X_seq.shape[2],
    hidden_dim=64,
    num_classes=2,
    dropout=0.2,
).to(device)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
model

# %%
def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    all_preds = []
    all_labels = []

    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)

        optimizer.zero_grad()
        logits, _ = model(X_batch)
        loss = criterion(logits, y_batch)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * X_batch.size(0)
        all_preds.extend(torch.argmax(logits, dim=1).detach().cpu().numpy())
        all_labels.extend(y_batch.detach().cpu().numpy())

    return total_loss / len(loader.dataset), accuracy_score(all_labels, all_preds)


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            logits, _ = model(X_batch)
            loss = criterion(logits, y_batch)

            total_loss += loss.item() * X_batch.size(0)
            all_preds.extend(torch.argmax(logits, dim=1).detach().cpu().numpy())
            all_labels.extend(y_batch.detach().cpu().numpy())

    return (
        total_loss / len(loader.dataset),
        accuracy_score(all_labels, all_preds),
        np.array(all_labels),
        np.array(all_preds),
    )


num_epochs = 30
best_val_acc = 0.0
best_model_path = PROJECT_ROOT / "src/ml/saved_models/best_attention_lstm_boundary.pt"
best_model_path.parent.mkdir(parents=True, exist_ok=True)

history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

for epoch in range(1, num_epochs + 1):
    train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
    val_loss, val_acc, _, _ = evaluate(model, val_loader, criterion, device)

    history["train_loss"].append(train_loss)
    history["train_acc"].append(train_acc)
    history["val_loss"].append(val_loss)
    history["val_acc"].append(val_acc)

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), best_model_path)

    print(
        f"Epoch {epoch:03d} | "
        f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} | "
        f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}"
    )

# %%
plt.figure(figsize=(10, 4))
plt.plot(history["train_loss"], label="train loss")
plt.plot(history["val_loss"], label="val loss")
plt.xlabel("epoch")
plt.ylabel("loss")
plt.title("Attention-LSTM Boundary Detection Loss")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()

plt.figure(figsize=(10, 4))
plt.plot(history["train_acc"], label="train acc")
plt.plot(history["val_acc"], label="val acc")
plt.xlabel("epoch")
plt.ylabel("accuracy")
plt.title("Attention-LSTM Boundary Detection Accuracy")
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()

# %%
model.load_state_dict(torch.load(best_model_path, map_location=device))
test_loss, test_acc, y_true, y_pred = evaluate(model, test_loader, criterion, device)

print("Test loss:", test_loss)
print("Test accuracy:", test_acc)
print(classification_report(y_true, y_pred, target_names=["stable", "near_boundary"]))

cm = confusion_matrix(y_true, y_pred)
disp = ConfusionMatrixDisplay(cm, display_labels=["stable", "near_boundary"])
disp.plot()
plt.title("Attention-LSTM Boundary Detection Confusion Matrix")
plt.show()

# %%
# 14. 保存实验结果到 outputs，便于论文整理
output_dir = PROJECT_ROOT / "outputs/soil_change_detection"
output_dir.mkdir(parents=True, exist_ok=True)

depth_df.to_csv(output_dir / "depth_change_score.csv", index=False, encoding="utf-8-sig")
detected_boundaries_df.to_csv(
    output_dir / "detected_boundaries.csv",
    index=False,
    encoding="utf-8-sig",
)
comparison_df.to_csv(
    output_dir / "detected_vs_report_boundaries.csv",
    index=False,
    encoding="utf-8-sig",
)

output_dir
