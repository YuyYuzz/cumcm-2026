"""Q4 正式主程序的结构、收敛、时间积分与守恒验收。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("q4_main_validation", HERE / "q4_main.py")
if SPEC is None or SPEC.loader is None:
    raise ImportError("无法加载q4_main.py")
q4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = q4
SPEC.loader.exec_module(q4)

DATA_DIR = q4.OUTPUT_DIR
CACHE_PATH = (
    DATA_DIR / "q4_validation_cache.json"
    if q4.IN_REPOSITORY_LAYOUT
    else HERE / "diagnostics" / "q4_validation_cache.json"
)
SAMPLE_HOURS = np.array([6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0, 48.0])
TARGET_OUTPUT_TIMES = np.r_[0.0, SAMPLE_HOURS * 3600.0]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _solution_record(solution) -> dict[str, object]:
    records = []
    for hour in SAMPLE_HOURS:
        t = hour * 3600.0
        if t >= solution.end_time_s:
            continue
        index = int(np.argmin(np.abs(solution.time_s - t)))
        values = []
        for radius_m in q4.TABLE_FIXED_RADII_M:
            if radius_m > solution.radius_m[index] + 1.0e-12:
                values.append(None)
            else:
                values.append(float(solution.moisture_fixed[index, int(round(radius_m / 0.001))]))
        records.append({
            "time_h": float(hour),
            "fixed_C": values,
            "surface_C": float(solution.moisture_surface[index]),
            "axis_C": float(solution.moisture_axis[index]),
            "radius_cm": float(solution.radius_m[index] * 100.0),
        })
    root_audit = q4.surface_root_audit(solution)
    return {
        "cells": solution.grid.cells,
        "rtol": solution.tolerances["rtol"],
        "max_step_s": solution.tolerances["max_step_s"],
        "radius_interpolation": solution.radius_interpolation,
        "end_time_s": float(solution.end_time_s),
        "end_time_h": float(solution.end_time_s / 3600.0),
        "end_surface_C": float(solution.moisture_surface[-1]),
        "end_axis_C": float(solution.moisture_axis[-1]),
        "end_max_C": float(solution.end_max_moisture),
        "end_argmax_cm": float(solution.end_max_radius_m * 100.0),
        "end_radius_cm": float(solution.radius_data.radius(solution.end_time_s) * 100.0),
        "records": records,
        "root_audit": root_audit,
        "runtime_s": float(solution.runtime_s),
        "nfev": solution.nfev,
    }


def _formal_record() -> dict[str, object]:
    summary = _load_json(DATA_DIR / "q4_run_summary.json")
    root = _load_json(DATA_DIR / "q4_surface_root_audit.json")
    records = []
    with np.load(DATA_DIR / "q4_solution.npz") as data:
        for hour in SAMPLE_HOURS:
            t = hour * 3600.0
            if t >= summary["end_time_s"]:
                continue
            index = int(np.argmin(np.abs(data["time_s"] - t)))
            fixed_values = []
            for radius_m in q4.TABLE_FIXED_RADII_M:
                if radius_m > data["radius_m"][index] + 1.0e-12:
                    fixed_values.append(None)
                else:
                    fixed_values.append(float(data["moisture_fixed"][index, int(round(radius_m / 0.001))]))
            records.append({
                "time_h": float(hour), "fixed_C": fixed_values,
                "surface_C": float(data["moisture_surface"][index]),
                "axis_C": float(data["moisture_axis"][index]),
                "radius_cm": float(data["radius_m"][index] * 100.0),
            })
    return {
        "cells": summary["grid_cells"], "rtol": summary["tolerances"]["rtol"],
        "max_step_s": summary["tolerances"]["max_step_s"],
        "radius_interpolation": summary["radius_interpolation"],
        "end_time_s": summary["end_time_s"], "end_time_h": summary["end_time_h"],
        "end_surface_C": summary["end_surface_moisture"],
        "end_axis_C": summary["end_axis_moisture"],
        "end_max_C": summary["end_max_moisture"],
        "end_argmax_cm": 100.0 * summary["end_max_radius_m"],
        "end_radius_cm": 100.0 * summary["end_radius_m"],
        "records": records, "root_audit": root,
        "runtime_s": summary["runtime_s"], "nfev": summary["nfev"],
    }


def _compare(left: dict, right: dict) -> dict[str, object]:
    differences: list[tuple[float, dict[str, float | str]]] = []
    right_by_hour = {row["time_h"]: row for row in right["records"]}
    for lrow in left["records"]:
        rrow = right_by_hour.get(lrow["time_h"])
        if rrow is None:
            continue
        for index, (lv, rv) in enumerate(zip(lrow["fixed_C"], rrow["fixed_C"])):
            if lv is not None and rv is not None:
                differences.append((abs(lv - rv), {"time_h": lrow["time_h"], "location": f"fixed_{q4.TABLE_FIXED_RADII_M[index]*100:g}_cm"}))
        differences.append((abs(lrow["surface_C"] - rrow["surface_C"]), {"time_h": lrow["time_h"], "location": "surface"}))
    worst = max(differences, key=lambda item: item[0]) if differences else (0.0, {})
    left_roots = {round(row["time_h"], 9): row for row in left["root_audit"]["records"]}
    root_differences = []
    for row in right["root_audit"]["records"]:
        other = left_roots.get(round(row["time_h"], 9))
        if other is not None:
            root_differences.append((abs(other["adopted_root"] - row["adopted_root"]), row["time_h"]))
    worst_root = max(root_differences, default=(0.0, None))
    return {
        "end_time_signed_right_minus_left_s": right["end_time_s"] - left["end_time_s"],
        "end_time_abs_difference_s": abs(right["end_time_s"] - left["end_time_s"]),
        "max_abs_regular_table_C_difference": worst[0],
        "worst_regular_table_location": worst[1],
        "end_surface_abs_difference": abs(right["end_surface_C"] - left["end_surface_C"]),
        "max_abs_adopted_root_difference": worst_root[0],
        "worst_root_time_h": worst_root[1],
    }


def _run_case(**kwargs) -> dict[str, object]:
    solution = q4.solve_q4(output_times_s=TARGET_OUTPUT_TIMES, **kwargs)
    return _solution_record(solution)


def run_grid(cache: dict) -> dict:
    cache.setdefault("formal", _formal_record())
    for cells in (641, 1281, 5121):
        key = f"grid_N{cells}"
        if key not in cache:
            print(f"运行网格N={cells}", flush=True)
            cache[key] = _run_case(
                cells=cells,
                first_step_s=1.0e-4 if cells >= 5121 else None,
            )
            _write_json(CACHE_PATH, cache)
    return cache


def _instantaneous_and_cumulative_balance() -> dict[str, object]:
    ambient = q4.load_ambient()
    radius_data = q4.load_radius_data()
    with np.load(DATA_DIR / "q4_solution.npz") as data:
        grid = q4.make_grid(len(data["xi_cell_centers"]))
        records = []
        max_t_rel = 0.0
        max_t_abs_near_zero = 0.0
        max_c_rel = 0.0
        for t, temperature, concentration in zip(
            data["snapshot_times_s"], data["temperature_cells_snapshot_c"], data["moisture_cells_snapshot"]
        ):
            state = np.r_[temperature, concentration]
            derivative, heat_flux, moisture_flux, surface = q4.rhs_and_fluxes(
                float(t), state, grid, ambient, radius_data, "appendix4"
            )
            radius_m = float(radius_data.radius(t))
            rho = np.asarray(q4.density(concentration, "appendix4"))
            cp = np.asarray(q4.heat_capacity(concentration, "appendix4"))
            heat_lhs = float(np.sum(rho * cp * derivative[:grid.cells] * grid.volumes_xidxi))
            heat_rhs = float(heat_flux[-1] / radius_m**2)
            moisture_lhs = float(np.sum(derivative[grid.cells:] * grid.volumes_xidxi))
            moisture_rhs = float(moisture_flux[-1] / radius_m**2)
            t_scale = max(abs(heat_lhs), abs(heat_rhs), 1.0e-30)
            c_scale = max(abs(moisture_lhs), abs(moisture_rhs), 1.0e-30)
            heat_absolute = abs(heat_lhs - heat_rhs)
            t_rel = heat_absolute / t_scale
            c_rel = abs(moisture_lhs - moisture_rhs) / c_scale
            if t_scale > 1.0e-12:
                max_t_rel = max(max_t_rel, t_rel)
            else:
                max_t_abs_near_zero = max(max_t_abs_near_zero, heat_absolute)
            max_c_rel = max(max_c_rel, c_rel)
            records.append({"time_s": float(t), "temperature_relative_residual": t_rel, "moisture_relative_residual": c_rel, "surface_C": float(surface[1])})

        times = data["time_s"]
        inventory = data["moisture_inventory"]
        rate = data["moisture_boundary_rate"]
        cumulative = np.zeros_like(times)
        cumulative[1:] = np.cumsum(0.5 * (rate[:-1] + rate[1:]) * np.diff(times))
        storage = inventory - inventory[0]
        residual = storage - cumulative
        final_scale = max(abs(storage[-1]), abs(cumulative[-1]), 1.0e-30)
        relative = np.abs(residual) / np.maximum(np.maximum(np.abs(storage), np.abs(cumulative)), 1.0e-30)
        cumulative_report = {
            "final_storage_change": float(storage[-1]),
            "final_boundary_integral": float(cumulative[-1]),
            "final_absolute_residual": float(residual[-1]),
            "final_relative_residual": float(abs(residual[-1]) / final_scale),
            "max_absolute_residual": float(np.max(np.abs(residual))),
            "max_absolute_residual_time_s": float(times[int(np.argmax(np.abs(residual)))]),
            "max_relative_residual_after_60s": float(np.max(relative[1:])),
            "sampling_interval_s": 60,
        }
    return {
        "instantaneous": {
            "temperature_nonzero_scale_threshold": 1.0e-12,
            "temperature_max_relative_residual_nonzero_scale": max_t_rel,
            "temperature_max_absolute_residual_near_zero_scale": max_t_abs_near_zero,
            "moisture_max_relative_residual": max_c_rel,
            "records": records,
        },
        "cumulative_inventory_60s": cumulative_report,
    }


def _surface_robin_check() -> dict[str, object]:
    ambient = q4.load_ambient()
    radius_data = q4.load_radius_data()
    maximum_heat = 0.0
    maximum_moisture = 0.0
    with np.load(DATA_DIR / "q4_solution.npz") as data:
        grid = q4.make_grid(len(data["xi_cell_centers"]))
        records = []
        for t, temperature, concentration in zip(data["snapshot_times_s"], data["temperature_cells_snapshot_c"], data["moisture_cells_snapshot"]):
            radius_m = float(radius_data.radius(t))
            ts, cs, q_t, q_c = q4.surface_states(
                float(temperature[-1]), float(concentration[-1]), float(ambient.temperature(t)),
                float(ambient.concentration(t)), radius_m, grid.dxi, "appendix4"
            )
            half = radius_m * grid.dxi * 0.5
            k_face = q4.harmonic_mean(q4.thermal_conductivity(concentration[-1]), q4.thermal_conductivity(cs))
            d_face = q4.harmonic_mean(q4.diffusion_coefficient(concentration[-1], temperature[-1]), q4.diffusion_coefficient(cs, ts))
            heat_residual = float(k_face * (ts - temperature[-1]) / half + q4.H * (ts - ambient.temperature(t)))
            moisture_residual = float(d_face * (cs - concentration[-1]) / half + q4.HM * (cs - ambient.concentration(t)))
            maximum_heat = max(maximum_heat, abs(heat_residual))
            maximum_moisture = max(maximum_moisture, abs(moisture_residual))
            records.append({"time_s": float(t), "heat_residual_w_m2": heat_residual, "moisture_residual_m_s": moisture_residual, "xi_heat_flux": q_t, "xi_moisture_flux": q_c})
    return {"max_abs_heat_robin_residual_w_m2": maximum_heat, "max_abs_moisture_robin_residual_m_s": maximum_moisture, "records": records}


def run_full(cache: dict) -> dict:
    cache = run_grid(cache)
    cases = {
        "rtol_1e-7": {"cells": 2561, "rtol": 1.0e-7},
        "max_step_30s": {"cells": 2561, "max_step_s": 30.0},
        "radius_linear": {"cells": 2561, "radius_interpolation": "linear"},
    }
    for key, options in cases.items():
        if key not in cache:
            print(f"运行敏感性{key}", flush=True)
            cache[key] = _run_case(**options)
            _write_json(CACHE_PATH, cache)
    formal = cache["formal"]
    grid = {
        "N641_to_N1281": _compare(cache["grid_N641"], cache["grid_N1281"]),
        "N1281_to_N2561": _compare(cache["grid_N1281"], formal),
        "N2561_to_N5121": _compare(formal, cache["grid_N5121"]),
    }
    zero = _load_json(DATA_DIR / "q4_zero_diffusion_test.json")
    balance = _instantaneous_and_cumulative_balance()
    robin = _surface_robin_check()
    effect = _load_json(DATA_DIR / "q4_effect_decomposition.json")
    q3_repro = effect["q3_fixed_appendix3_reproduction"]
    with np.load(DATA_DIR / "q4_solution.npz") as data:
        finite = bool(all(np.all(np.isfinite(data[name])) for name in ("moisture_axis", "moisture_surface", "cmax", "terminal_moisture")))
        positive = bool(min(float(np.min(data["moisture_axis"])), float(np.min(data["moisture_surface"])), float(np.min(data["terminal_moisture"]))) > 0.0)
        terminal_ok = bool(float(np.max(data["terminal_moisture"])) <= q4.THRESHOLD + 5.0e-10)
        terminal_argmax = int(np.argmax(data["terminal_moisture"]))
        terminal_argmax_xi = float(data["terminal_xi"][terminal_argmax])
    validations = {
        "model_initial_properties_appendix4": q4.initial_properties("appendix4"),
        "q3_fixed_appendix3_reproduction": q3_repro,
        "zero_diffusion_material_coordinate_test": zero,
        "surface_robin": robin,
        "grid_convergence": grid,
        "rtol_sensitivity": _compare(cache["rtol_1e-7"], formal),
        "max_step_sensitivity": _compare(formal, cache["max_step_30s"]),
        "radius_interpolation_sensitivity": _compare(formal, cache["radius_linear"]),
        "integral_balance": balance,
        "surface_root_audit": formal["root_audit"],
        "surface_root_grid_stability": {
            "N1281_to_N2561_max_abs_adopted_root_difference": grid["N1281_to_N2561"]["max_abs_adopted_root_difference"],
            "N2561_to_N5121_max_abs_adopted_root_difference": grid["N2561_to_N5121"]["max_abs_adopted_root_difference"],
        },
        "physical_and_terminal_checks": {"finite": finite, "positive": positive, "terminal_all_below_threshold": terminal_ok, "terminal_high_resolution_argmax_xi": terminal_argmax_xi},
    }
    checks = {
        "q3_reproduction_below_0_01s": abs(q3_repro["difference_s"]) < 0.01,
        "zero_diffusion_below_1e-10": zero["pass"],
        "surface_robin_heat_below_1e-8": robin["max_abs_heat_robin_residual_w_m2"] < 1.0e-8,
        "surface_robin_moisture_below_1e-14": robin["max_abs_moisture_robin_residual_m_s"] < 1.0e-14,
        "instantaneous_temperature_balance": (
            balance["instantaneous"]["temperature_max_relative_residual_nonzero_scale"] < 1.0e-10
            and balance["instantaneous"]["temperature_max_absolute_residual_near_zero_scale"] < 1.0e-20
        ),
        "instantaneous_moisture_balance_below_1e-12": balance["instantaneous"]["moisture_max_relative_residual"] < 1.0e-12,
        "formal_root_audit_single_root": formal["root_audit"]["all_single_root"],
        "formal_grid_convergence_stable": (
            grid["N2561_to_N5121"]["end_time_abs_difference_s"] < 2.0
            and grid["N2561_to_N5121"]["max_abs_regular_table_C_difference"] < 1.0e-5
            and grid["N2561_to_N5121"]["max_abs_adopted_root_difference"] < 1.0e-5
        ),
        "finite_positive_terminal": finite and positive and terminal_ok and terminal_argmax_xi == 0.0,
        "rtol_end_time_difference_below_1s": validations["rtol_sensitivity"]["end_time_abs_difference_s"] < 1.0,
        "max_step_end_time_difference_below_1s": validations["max_step_sensitivity"]["end_time_abs_difference_s"] < 1.0,
        "cumulative_inventory_balance_below_1e-3": balance["cumulative_inventory_60s"]["final_relative_residual"] < 1.0e-3,
    }
    validations["acceptance"] = checks
    validations["overall_pass"] = bool(all(checks.values()))
    validations["validation_runtime_note"] = "网格与敏感性工况的单次运行时间见diagnostics缓存记录。"
    _write_json(DATA_DIR / "q4_validation.json", validations)
    summary_path = DATA_DIR / "q4_run_summary.json"
    summary = _load_json(summary_path)
    summary["validation_file"] = q4.record_path(DATA_DIR / "q4_validation.json")
    summary["effect_decomposition_file"] = q4.record_path(DATA_DIR / "q4_effect_decomposition.json")
    summary["result_payload"] = q4.record_path(DATA_DIR / "result4_payload.json")
    summary["validation_overall_pass"] = validations["overall_pass"]
    summary["main_checks_passed"] = bool(
        summary.get("main_checks_passed", False) and validations["overall_pass"]
    )
    _write_json(summary_path, summary)
    return validations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid-only", action="store_true")
    parser.add_argument("--clear-cache", action="store_true")
    args = parser.parse_args()
    if args.clear_cache and CACHE_PATH.exists():
        CACHE_PATH.unlink()
    cache = _load_json(CACHE_PATH) if CACHE_PATH.exists() else {}
    started = time.perf_counter()
    if args.grid_only:
        cache = run_grid(cache)
        formal = cache["formal"]
        report = {
            "N641_to_N1281": _compare(cache["grid_N641"], cache["grid_N1281"]),
            "N1281_to_N2561": _compare(cache["grid_N1281"], formal),
            "N2561_to_N5121": _compare(formal, cache["grid_N5121"]),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        report = run_full(cache)
        print(json.dumps({"overall_pass": report["overall_pass"], "acceptance": report["acceptance"]}, ensure_ascii=False, indent=2))
    print(f"validation wall time = {time.perf_counter()-started:.3f} s")


if __name__ == "__main__":
    main()
