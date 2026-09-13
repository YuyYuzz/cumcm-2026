"""Q4 的 2×2 物性/收缩效应分解。"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
Q4_DIR = HERE.parent
SPEC = importlib.util.spec_from_file_location("q4_main_for_effects", Q4_DIR / "q4_main.py")
if SPEC is None or SPEC.loader is None:
    raise ImportError("无法加载q4_main.py")
q4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = q4
SPEC.loader.exec_module(q4)
OUTPUT_DIR = q4.OUTPUT_DIR

SAMPLE_HOURS = np.array([6.0, 12.0, 24.0, 36.0, 48.0])
SAMPLE_TIMES = np.r_[0.0, SAMPLE_HOURS * 3600.0]


def summarize(label: str, solution) -> dict[str, object]:
    records = []
    for hour in SAMPLE_HOURS:
        t = hour * 3600.0
        if t >= solution.end_time_s:
            continue
        index = int(np.argmin(np.abs(solution.time_s - t)))
        records.append({
            "time_h": float(hour),
            "axis_C": float(solution.moisture_axis[index]),
            "surface_C": float(solution.moisture_surface[index]),
            "radius_cm": float(solution.radius_m[index] * 100.0),
        })
    return {
        "label": label,
        "property_set": solution.property_set,
        "geometry": solution.geometry,
        "end_time_s": float(solution.end_time_s),
        "end_time_h": float(solution.end_time_s / 3600.0),
        "end_time_d": float(solution.end_time_s / 86400.0),
        "end_radius_cm": float(solution.radius_data.radius(solution.end_time_s) * 100.0),
        "end_max_moisture": float(solution.end_max_moisture),
        "end_max_radius_cm": float(solution.end_max_radius_m * 100.0),
        "end_axis_C": float(solution.moisture_axis[-1]),
        "end_surface_C": float(solution.moisture_surface[-1]),
        "sample_records": records,
        "runtime_s": float(solution.runtime_s),
        "nfev": solution.nfev,
    }


def run(cells: int = 2561) -> dict[str, object]:
    cases = {
        "C": ("appendix3", "fixed"),
        "D": ("appendix3", "moving"),
        "A": ("appendix4", "fixed"),
    }
    output: dict[str, object] = {}
    for label, (properties, geometry) in cases.items():
        print(f"运行工况{label}: {properties}+{geometry}", flush=True)
        solution = q4.solve_q4(
            cells=cells,
            property_set=properties,
            geometry=geometry,
            output_times_s=SAMPLE_TIMES,
        )
        output[label] = summarize(label, solution)
        print(f"工况{label}: {solution.end_time_s/3600.0:.9f} h", flush=True)

    b_summary = json.loads((OUTPUT_DIR / "q4_run_summary.json").read_text(encoding="utf-8"))
    output["B"] = {
        "label": "B",
        "property_set": "appendix4",
        "geometry": "moving",
        "end_time_s": b_summary["end_time_s"],
        "end_time_h": b_summary["end_time_h"],
        "end_time_d": b_summary["end_time_d"],
        "end_radius_cm": 100.0 * b_summary["end_radius_m"],
        "end_max_moisture": b_summary["end_max_moisture"],
        "end_max_radius_cm": 100.0 * b_summary["end_max_radius_m"],
        "end_axis_C": b_summary["end_axis_moisture"],
        "end_surface_C": b_summary["end_surface_moisture"],
        "sample_records": [],
        "runtime_s": b_summary["runtime_s"],
    }
    with np.load(OUTPUT_DIR / "q4_solution.npz") as data:
        times = data["time_s"]
        for hour in SAMPLE_HOURS:
            t = hour * 3600.0
            if t >= output["B"]["end_time_s"]:
                continue
            index = int(np.argmin(np.abs(times - t)))
            output["B"]["sample_records"].append({
                "time_h": float(hour),
                "axis_C": float(data["moisture_axis"][index]),
                "surface_C": float(data["moisture_surface"][index]),
                "radius_cm": float(data["radius_m"][index] * 100.0),
            })

    t_c, t_d, t_a, t_b = (output[k]["end_time_s"] for k in ("C", "D", "A", "B"))
    effects = {
        "property_main_A_minus_C_s": t_a - t_c,
        "property_main_A_minus_C_h": (t_a - t_c) / 3600.0,
        "shrink_at_appendix4_B_minus_A_s": t_b - t_a,
        "shrink_at_appendix4_B_minus_A_h": (t_b - t_a) / 3600.0,
        "shrink_at_appendix3_D_minus_C_s": t_d - t_c,
        "shrink_at_appendix3_D_minus_C_h": (t_d - t_c) / 3600.0,
        "interaction_I_s": t_b - t_a - t_d + t_c,
        "interaction_I_h": (t_b - t_a - t_d + t_c) / 3600.0,
    }
    q3_reference_path = (
        q4.PROJECT_ROOT / "results" / "q3" / "q3_run_summary.json"
        if q4.IN_REPOSITORY_LAYOUT
        else q4.PROJECT_ROOT / "Q3" / "q3_run_summary.json"
    )
    q3_reference = json.loads(q3_reference_path.read_text(encoding="utf-8"))
    report = {
        "grid_cells": cells,
        "common_bdf": {"rtol": 1.0e-8, "atol_T": 1.0e-10, "atol_C": 1.0e-11, "max_step_s": 60.0},
        "cases": output,
        "effects": effects,
        "q3_fixed_appendix3_reproduction": {
            "q4_skeleton_end_time_s": t_c,
            "frozen_q3_end_time_s": q3_reference["end_time_s"],
            "difference_s": t_c - q3_reference["end_time_s"],
            "difference_abs_s": abs(t_c - q3_reference["end_time_s"]),
        },
    }
    path = OUTPUT_DIR / "q4_effect_decomposition.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["effects"], ensure_ascii=False, indent=2))
