"""审计低湿边界下离散表面方程的根数量。

脚本仅对冻结结果中的外层控制体快照做代数诊断，不续算低湿情景，
不选择折叠后的特殊根分支，也不报告低湿情景的烘干结束时间。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
Q3_DIR = SCRIPT_DIR.parent
REPO_ROOT = Q3_DIR.parents[1]
DATA_PATH = REPO_ROOT / "results" / "q3" / "q3_solution.npz"
OUTPUT_PATH = REPO_ROOT / "results" / "q3" / "diagnostics" / "q3_low_ca_diagnostic.json"

H = 25.0
HM = 8.0e-7
RADIUS_M = 0.02
LOW_CA = 0.03


def bisect_root(function, lower: float, upper: float) -> float:
    """对已有符号变化区间作确定性二分，不引入求解器外部依赖。"""
    f_lower = float(function(lower))
    f_upper = float(function(upper))
    if f_lower == 0.0:
        return lower
    if f_upper == 0.0:
        return upper
    if f_lower * f_upper > 0.0:
        raise ValueError("区间未括住根")
    for _ in range(100):
        middle = 0.5 * (lower + upper)
        f_middle = float(function(middle))
        if f_middle == 0.0 or upper - lower <= 1.0e-13:
            return middle
        if f_lower * f_middle <= 0.0:
            upper = middle
            f_upper = f_middle
        else:
            lower = middle
            f_lower = f_middle
    return 0.5 * (lower + upper)


def k_value(concentration: np.ndarray | float):
    return 0.21 + 0.38 * concentration / (concentration + 1.0)


def d_value(concentration: np.ndarray | float, temperature_c: np.ndarray | float):
    return (
        2.4e-3
        * np.exp(-0.45 / concentration)
        * np.exp(-3850.0 / (temperature_c + 273.15))
    )


def roots_for_state(
    cell_temperature_c: float,
    cell_concentration: float,
    ambient_temperature_c: float,
    dr_m: float,
    sample_count: int = 8193,
) -> list[float]:
    half_width = 0.5 * dr_m
    k_cell = float(k_value(cell_concentration))
    d_cell = float(d_value(cell_concentration, cell_temperature_c))

    def residual(surface_concentration: np.ndarray | float):
        k_surface = k_value(surface_concentration)
        k_face = 2.0 * k_cell * k_surface / (k_cell + k_surface)
        conductance = k_face / half_width
        surface_temperature = (
            conductance * cell_temperature_c + H * ambient_temperature_c
        ) / (conductance + H)
        d_surface = d_value(surface_concentration, surface_temperature)
        d_face = 2.0 * d_cell * d_surface / (d_cell + d_surface)
        return (
            d_face * (surface_concentration - cell_concentration) / half_width
            + HM * (surface_concentration - LOW_CA)
        )

    samples = np.linspace(cell_concentration, LOW_CA, sample_count)
    values = np.asarray(residual(samples), dtype=float)
    crossings = np.flatnonzero(values[:-1] * values[1:] <= 0.0)
    roots: list[float] = []
    for index in crossings:
        lower, upper = sorted((float(samples[index]), float(samples[index + 1])))
        root = float(bisect_root(residual, lower, upper))
        if not roots or abs(root - roots[-1]) > 1.0e-10:
            roots.append(root)
    return roots


def main() -> None:
    with np.load(DATA_PATH) as data:
        snapshot_times_s = np.asarray(data["snapshot_times_s"], dtype=float)
        temperature_cells = np.asarray(data["temperature_cells_snapshot_c"], dtype=float)
        moisture_cells = np.asarray(data["moisture_cells_snapshot"], dtype=float)
        ambient_temperature = np.asarray(data["ambient_temperature_c"], dtype=float)
        time_s = np.asarray(data["time_s"], dtype=float)
        cell_count = int(np.asarray(data["cell_centers_m"]).size)
    dr_m = RADIUS_M / cell_count
    records = []
    for index, snapshot_time in enumerate(snapshot_times_s):
        if snapshot_time < 4.0 * 3600.0:
            continue
        ambient_index = int(np.argmin(np.abs(time_s - snapshot_time)))
        roots = roots_for_state(
            float(temperature_cells[index, -1]),
            float(moisture_cells[index, -1]),
            float(ambient_temperature[ambient_index]),
            dr_m,
        )
        records.append(
            {
                "time_s": float(snapshot_time),
                "outer_cell_temperature_c": float(temperature_cells[index, -1]),
                "outer_cell_moisture_kg_kg": float(moisture_cells[index, -1]),
                "root_count": len(roots),
                "surface_roots_kg_kg": roots,
            }
        )
    report = {
        "purpose": "低湿情景离散非线性表面方程根数量诊断",
        "source": "q3_solution.npz 的冻结外层控制体快照",
        "post_14400_Ca_kg_kg": LOW_CA,
        "grid_cells": cell_count,
        "reported_end_time": None,
        "included_in_formal_validation": False,
        "records": records,
        "limitation": (
            "该脚本只审计离散表面方程，不构成低湿情景的长程求解；"
            "根数量与折叠位置可能随网格和状态变化，因此不报告精确烘干时间。"
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
