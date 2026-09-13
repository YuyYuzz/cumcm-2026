"""基于冻结 Q3 结果检查后期平均含水率的指数衰减特征。

本脚本只读取 q3_solution.npz，不修改主模型、扩散系数或终止时间。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
Q3_DIR = SCRIPT_DIR.parent
REPO_ROOT = Q3_DIR.parents[1]
DATA_PATH = REPO_ROOT / "results" / "q3" / "q3_solution.npz"
OUTPUT_PATH = REPO_ROOT / "results" / "q3" / "diagnostics" / "q3_long_time_decay_check.json"

RADIUS_M = 0.02
LENGTH_M = 0.25
C_EQ = 0.04986
BETA_1 = 2.404825557695773


def diffusion_coefficient(concentration: float, temperature_c: float) -> float:
    return float(
        2.4e-3
        * np.exp(-0.45 / concentration)
        * np.exp(-3850.0 / (temperature_c + 273.15))
    )


def fit_interval(
    time_s: np.ndarray,
    ln_mr: np.ndarray,
    average_c: np.ndarray,
    average_temperature_c: np.ndarray,
    start_h: float,
    end_h: float,
) -> dict[str, float | list[float]]:
    mask = (time_s >= start_h * 3600.0) & (time_s <= end_h * 3600.0)
    x = time_s[mask]
    y = ln_mr[mask]
    if x.size < 3 or not np.all(np.isfinite(y)):
        raise ValueError(f"{start_h:g}--{end_h:g} h 区间无法稳定拟合")
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 1.0
    representative_c = float(np.mean(average_c[mask]))
    representative_temperature_c = float(np.mean(average_temperature_c[mask]))
    d_local = diffusion_coefficient(representative_c, representative_temperature_c)
    d_equivalent = float(-slope * RADIUS_M**2 / BETA_1**2)
    return {
        "interval_h": [start_h, end_h],
        "sample_count": int(x.size),
        "slope_per_s": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_squared),
        "equivalent_diffusivity_m2_s": d_equivalent,
        "representative_average_moisture_kg_kg": representative_c,
        "representative_average_temperature_c": representative_temperature_c,
        "appendix3_diffusivity_at_representative_state_m2_s": d_local,
        "equivalent_to_local_diffusivity_ratio": float(d_equivalent / d_local),
    }


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"冻结结果不存在：{DATA_PATH}")
    with np.load(DATA_PATH) as data:
        time_s = np.asarray(data["time_s"], dtype=float)
        inventory = np.asarray(data["moisture_inventory"], dtype=float)
        temperature = np.asarray(data["temperature_output_c"], dtype=float)
        radii = np.asarray(data["output_radii_m"], dtype=float)
        end_time_s = float(data["end_time_s"])

    volume_m3 = np.pi * RADIUS_M**2 * LENGTH_M
    average_c = inventory / volume_m3
    # 输出点上的面积权重积分仅用于得到与 Cbar 同尺度的代表温度。
    radial_weight = radii
    average_temperature_c = (
        2.0 / RADIUS_M**2 * np.trapezoid(temperature * radial_weight, radii, axis=1)
    )
    reference_index = int(np.argmin(np.abs(time_s - 4.0 * 3600.0)))
    denominator = average_c[reference_index] - C_EQ
    if denominator <= 0.0:
        raise ValueError("4 h 平均含水率不高于环境参考值，无法定义 MR")
    mr = (average_c - C_EQ) / denominator
    if np.any(mr[time_s >= 12.0 * 3600.0] <= 0.0):
        raise ValueError("拟合区间出现非正 MR")
    ln_mr = np.log(mr)

    middle = fit_interval(
        time_s, ln_mr, average_c, average_temperature_c, 12.0, 30.0
    )
    low = fit_interval(
        time_s, ln_mr, average_c, average_temperature_c, 36.0, end_time_s / 3600.0
    )
    supported = bool(middle["r_squared"] >= 0.95 and low["r_squared"] >= 0.98)
    report = {
        "purpose": "长期衰减行为合理性检查；不改变主模型与正式结果",
        "source": "q3_solution.npz",
        "moisture_ratio_definition": (
            "MR=(Cbar-Ceq)/(Cbar_at_4h-Ceq), Cbar=moisture_inventory/(pi*R^2*L)"
        ),
        "equilibrium_reference_kg_kg": C_EQ,
        "cylinder_first_mode_beta": BETA_1,
        "equivalent_diffusivity_relation": "D_eff=-slope*R^2/beta_1^2",
        "middle_moisture_interval": middle,
        "low_moisture_interval": low,
        "end_average_moisture_kg_kg": float(average_c[-1]),
        "end_appendix3_diffusivity_m2_s": diffusion_coefficient(
            float(average_c[-1]), float(average_temperature_c[-1])
        ),
        "supports_near_exponential_late_decay": supported,
        "interpretation": (
            "后期 ln(MR)-t 近似线性，且低湿段斜率绝对值与等效扩散系数均降低；"
            "该结果仅作扩散控制的数量级检查，不用于反向修正附录3公式。"
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
