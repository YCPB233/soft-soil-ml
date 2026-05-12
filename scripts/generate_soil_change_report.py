import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.db import get_engine  # noqa: E402


MACHINE_CODE = "RIG-001"
DEPTH_BIN_M = 0.05
LEFT_RIGHT_WINDOW_M = 1.0
SCORE_QUANTILE = 0.97
MIN_GAP_M = 1.2


def main():
    engine = get_engine()
    output_dir = PROJECT_ROOT / "outputs/soil_change_detection"
    output_dir.mkdir(parents=True, exist_ok=True)

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
        params={"machine_code": MACHINE_CODE},
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

    feature_cols = [
        "current_value",
        "torque",
        "penetration_speed",
        "grouting_pressure",
    ]

    work_df = rig_df.copy()
    work_df["timestamp"] = pd.to_datetime(work_df["timestamp"])
    work_df = work_df.dropna(subset=["drilling_depth"]).copy()

    for col in feature_cols:
        work_df[col] = pd.to_numeric(work_df[col], errors="coerce")
        work_df[col] = work_df[col].interpolate().ffill().bfill()

    work_df = work_df.sort_values("drilling_depth").reset_index(drop=True)

    dri_cols = ["current_value", "torque", "grouting_pressure", "penetration_speed"]
    dri_values = work_df[dri_cols]
    dri_z = (dri_values - dri_values.mean()) / dri_values.std(ddof=0).replace(0, 1)
    work_df["DRI"] = (
        0.30 * dri_z["current_value"]
        + 0.30 * dri_z["torque"]
        + 0.25 * dri_z["grouting_pressure"]
        - 0.15 * dri_z["penetration_speed"]
    )

    depth_source = work_df[work_df["penetration_speed"].fillna(0) > 0.001].copy()
    depth_source["depth_bin"] = (
        (depth_source["drilling_depth"] / DEPTH_BIN_M).round() * DEPTH_BIN_M
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

    signal_cols = [
        "current_value",
        "torque",
        "penetration_speed",
        "grouting_pressure",
        "DRI",
    ]

    x = depth_df[signal_cols].copy()
    median = x.median()
    iqr = (x.quantile(0.75) - x.quantile(0.25)).replace(0, 1)
    z = (x - median) / iqr
    z_smooth = z.rolling(window=5, center=True, min_periods=1).median()

    window_bins = max(3, int(LEFT_RIGHT_WINDOW_M / DEPTH_BIN_M))
    z_values = z_smooth.values
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

        left_mean = z_values[left_start:left_end].mean(axis=0)
        right_mean = z_values[right_start:right_end].mean(axis=0)
        scores.append(float(np.linalg.norm(right_mean - left_mean)))

    depth_df["change_score"] = scores
    depth_df["change_score_smooth"] = (
        depth_df["change_score"].rolling(window=5, center=True, min_periods=1).mean()
    )

    threshold = float(depth_df["change_score_smooth"].quantile(SCORE_QUANTILE))
    candidate_df = depth_df[depth_df["change_score_smooth"] >= threshold].copy()

    boundary_rows = []
    for _, row in candidate_df.sort_values("drilling_depth").iterrows():
        depth = row["drilling_depth"]
        if not boundary_rows:
            boundary_rows.append(row)
            continue

        last_depth = boundary_rows[-1]["drilling_depth"]
        if depth - last_depth < MIN_GAP_M:
            if row["change_score_smooth"] > boundary_rows[-1]["change_score_smooth"]:
                boundary_rows[-1] = row
        else:
            boundary_rows.append(row)

    detected_boundaries_df = pd.DataFrame(boundary_rows)
    if not detected_boundaries_df.empty:
        detected_boundaries_df = detected_boundaries_df[
            ["drilling_depth", "change_score_smooth"]
        ].rename(columns={"drilling_depth": "boundary_depth"})
    else:
        detected_boundaries_df = pd.DataFrame(
            columns=["boundary_depth", "change_score_smooth"]
        )

    soil_boundaries = (
        soil_df["bottom_depth_representative_m"].dropna().astype(float).sort_values().tolist()
    )

    comparison_rows = []
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

    summary = {
        "machine_code": MACHINE_CODE,
        "raw_rows": int(len(rig_df)),
        "depth_rows": int(len(depth_df)),
        "min_depth_m": float(work_df["drilling_depth"].min()),
        "max_depth_m": float(work_df["drilling_depth"].max()),
        "score_quantile": SCORE_QUANTILE,
        "score_threshold": threshold,
        "detected_boundary_count": int(len(detected_boundaries_df)),
        "mean_abs_offset_m": (
            float(comparison_df["abs_offset_m"].mean()) if not comparison_df.empty else None
        ),
        "median_abs_offset_m": (
            float(comparison_df["abs_offset_m"].median()) if not comparison_df.empty else None
        ),
    }

    depth_df.to_csv(output_dir / "depth_change_score.csv", index=False, encoding="utf-8-sig")
    detected_boundaries_df.to_csv(
        output_dir / "detected_boundaries.csv", index=False, encoding="utf-8-sig"
    )
    comparison_df.to_csv(
        output_dir / "detected_vs_report_boundaries.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame([summary]).to_csv(
        output_dir / "summary.csv", index=False, encoding="utf-8-sig"
    )

    plt.figure(figsize=(14, 5))
    plt.plot(depth_df["drilling_depth"], depth_df["change_score_smooth"], label="change score")
    for _, row in detected_boundaries_df.iterrows():
        plt.axvline(row["boundary_depth"], color="red", linestyle="--", alpha=0.7)
    plt.xlabel("drilling_depth (m)")
    plt.ylabel("change score")
    plt.title("Detected Possible Soil Change Boundaries")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "change_score_boundaries.png", dpi=180)
    plt.close()

    plt.figure(figsize=(14, 6))
    for col in ["current_value", "torque", "grouting_pressure", "DRI"]:
        y = depth_df[col]
        y_plot = (y - y.min()) / (y.max() - y.min() + 1e-9)
        plt.plot(depth_df["drilling_depth"], y_plot, label=f"{col} normalized")
    for _, row in detected_boundaries_df.iterrows():
        plt.axvline(row["boundary_depth"], color="red", linestyle="--", alpha=0.7)
    plt.xlabel("drilling_depth (m)")
    plt.ylabel("normalized signal")
    plt.title("Rig Signals with Detected Soil Change Boundaries")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "rig_signals_detected_boundaries.png", dpi=180)
    plt.close()

    plt.figure(figsize=(14, 5))
    plt.plot(depth_df["drilling_depth"], depth_df["change_score_smooth"], label="rig change score")
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
    plt.tight_layout()
    plt.savefig(output_dir / "detected_vs_report_boundaries.png", dpi=180)
    plt.close()

    print("Summary")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print()
    print("Detected boundaries")
    print(detected_boundaries_df.to_string(index=False))
    print()
    print("Detected vs report boundaries")
    print(comparison_df.to_string(index=False))
    print()
    print(f"Outputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
