"""Q3正式求解器的网格、容差、步长、积分平衡和敏感性验收。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "code" / "q3"))
import q3_main as q3


OUTPUT = REPO_ROOT / "results" / "q3" / "q3_validation.json"
FORMAL_DATA = REPO_ROOT / "results" / "q3" / "q3_solution.npz"
FORMAL_SUMMARY = REPO_ROOT / "results" / "q3" / "q3_run_summary.json"


CASES = {
    "grid_513": dict(cells=513),
    "grid_1025": dict(cells=1025),
    "loose_rtol_1e-7": dict(cells=2561, rtol=1.0e-7),
    "max_step_10s": dict(cells=2561, max_step_s=10.0),
    "post_Ca_0.03": dict(
        cells=2561,
        post_moisture=0.03,
        terminal_event=False,
        integration_upper_s=q3.INTEGRATION_UPPER_S,
    ),
    "post_Ca_0.07": dict(cells=2561, post_moisture=0.07),
}


def _run_case(item: tuple[str, dict]) -> tuple[str, dict[str, object]]:
    name, options = item
    requested = np.r_[0.0, q3.TABLE_TIMES_S]
    solution = q3.solve_q3(output_times_s=requested, **options)
    times, values = q3.table5(solution)
    return name, {
        "options": options,
        "runtime_s": solution.runtime_s,
        "nfev": solution.nfev,
        "njev": solution.njev,
        "nlu": solution.nlu,
        "end_time_s": solution.end_time_s,
        "end_time_h": solution.end_time_s / 3600.0,
        "end_max_moisture": solution.end_max_moisture,
        "end_max_radius_m": solution.end_max_radius_m,
        "end_axis_moisture": float(solution.moisture_output[-1, 0]),
        "end_surface_moisture": float(solution.moisture_surface[-1]),
        "table5_times_s": times.tolist(),
        "table5_moisture": values.tolist(),
        "threshold_reached": bool(
            options.get("terminal_event", True)
            and solution.end_max_moisture <= q3.THRESHOLD + 5.0e-10
        ),
    }


def _formal_record() -> dict[str, object]:
    summary = json.loads(FORMAL_SUMMARY.read_text(encoding="utf-8"))
    return {
        "options": {
            "cells": summary["grid_cells"],
            "rtol": summary["tolerances"]["rtol"],
            "max_step_s": summary["tolerances"]["max_step_s"],
        },
        "runtime_s": summary["runtime_s"],
        "nfev": summary["nfev"],
        "njev": summary["njev"],
        "nlu": summary["nlu"],
        "end_time_s": summary["end_time_s"],
        "end_time_h": summary["end_time_h"],
        "end_max_moisture": summary["end_max_moisture"],
        "end_max_radius_m": summary["end_max_radius_m"],
        "end_axis_moisture": summary["end_axis_moisture"],
        "end_surface_moisture": summary["end_surface_moisture"],
        "table5_times_s": summary["table5_times_s"],
        "table5_moisture": summary["table5_moisture"],
    }


def _comparison(left: dict, right: dict) -> dict[str, object]:
    left_table = np.asarray(left["table5_moisture"], dtype=float)[:-1]
    right_table = np.asarray(right["table5_moisture"], dtype=float)[:-1]
    difference = np.abs(left_table - right_table)
    index = np.unravel_index(int(np.argmax(difference)), difference.shape)
    return {
        "end_time_difference_s": float(abs(left["end_time_s"] - right["end_time_s"])),
        "end_time_signed_right_minus_left_s": float(right["end_time_s"] - left["end_time_s"]),
        "max_abs_table5_regular_times": float(difference[index]),
        "worst_table5_location": {
            "time_h": float(q3.TABLE_TIMES_S[index[0]] / 3600.0),
            "radius_cm": float(q3.TABLE_RADII_M[index[1]] * 100.0),
        },
        "end_axis_difference": float(abs(left["end_axis_moisture"] - right["end_axis_moisture"])),
        "end_surface_difference": float(abs(left["end_surface_moisture"] - right["end_surface_moisture"])),
        "end_max_difference": float(abs(left["end_max_moisture"] - right["end_max_moisture"])),
    }


def instantaneous_balance(data) -> dict[str, object]:
    grid = q3.q2.make_grid(data["cell_centers_m"].size)
    ambient = q3.load_q3_ambient()
    factor = 2.0 * np.pi * q3.LENGTH_M
    temperature_records = []
    moisture_records = []
    for time_value, temperature, moisture in zip(
        data["snapshot_times_s"],
        data["temperature_cells_snapshot_c"],
        data["moisture_cells_snapshot"],
    ):
        if time_value <= 0.0:
            continue
        derivative, heat_flux, moisture_flux, _ = q3.rhs_and_fluxes(
            float(time_value), np.r_[temperature, moisture], grid, ambient
        )
        temperature_storage = factor * np.sum(
            np.asarray(q3.q2.density(moisture))
            * np.asarray(q3.q2.heat_capacity(moisture))
            * derivative[: grid.cells]
            * grid.volumes_rdr_m2
        )
        temperature_boundary = factor * q3.RADIUS_M * heat_flux[-1]
        moisture_storage = factor * np.sum(
            derivative[grid.cells :] * grid.volumes_rdr_m2
        )
        moisture_boundary = factor * q3.RADIUS_M * moisture_flux[-1]
        temperature_scale = max(abs(temperature_storage), abs(temperature_boundary))
        temperature_records.append(
            {
                "time_s": float(time_value),
                "balance_scale_w": float(temperature_scale),
                "absolute_residual_w": float(temperature_storage - temperature_boundary),
                "relative_residual": float(
                    abs(temperature_storage - temperature_boundary)
                    / max(temperature_scale, 1.0e-30)
                ),
            }
        )
        moisture_records.append(
            {
                "time_s": float(time_value),
                "absolute_residual": float(moisture_storage - moisture_boundary),
                "relative_residual": float(
                    abs(moisture_storage - moisture_boundary)
                    / max(abs(moisture_storage), abs(moisture_boundary), 1.0e-30)
                ),
            }
        )
    # 温度趋于环境平台后，储存率与边界热流均会接近机器零；此时二者的
    # 相对误差不再具有数值意义。对可分辨的非零热流检查相对残差，对
    # 近零热流检查绝对残差，并同时保留全部逐时刻记录供追溯。
    temperature_nonzero_scale_w = 1.0e-12
    temperature_active_records = [
        record
        for record in temperature_records
        if record["balance_scale_w"] >= temperature_nonzero_scale_w
    ]
    temperature_near_zero_records = [
        record
        for record in temperature_records
        if record["balance_scale_w"] < temperature_nonzero_scale_w
    ]
    return {
        "temperature": {
            "max_relative_residual": max(x["relative_residual"] for x in temperature_records),
            "nonzero_scale_threshold_w": temperature_nonzero_scale_w,
            "nonzero_scale_record_count": len(temperature_active_records),
            "near_zero_scale_record_count": len(temperature_near_zero_records),
            "max_relative_residual_nonzero_scale": max(
                x["relative_residual"] for x in temperature_active_records
            ),
            "max_absolute_residual_near_zero_scale_w": max(
                abs(x["absolute_residual_w"]) for x in temperature_near_zero_records
            ),
            "max_absolute_residual_w": max(abs(x["absolute_residual_w"]) for x in temperature_records),
            "records": temperature_records,
        },
        "moisture": {
            "max_relative_residual": max(x["relative_residual"] for x in moisture_records),
            "max_absolute_residual": max(abs(x["absolute_residual"]) for x in moisture_records),
            "records": moisture_records,
        },
    }


def cumulative_balance(data) -> dict[str, object]:
    time_s = data["time_s"]
    heat_storage = data["heat_storage_cumulative_j"]
    heat_boundary = data["heat_boundary_cumulative_j"]
    heat_residual = heat_storage - heat_boundary
    moisture_boundary_cumulative = np.zeros_like(time_s)
    moisture_boundary_cumulative[1:] = np.cumsum(
        0.5
        * (data["moisture_boundary_rate"][:-1] + data["moisture_boundary_rate"][1:])
        * np.diff(time_s)
    )
    moisture_storage = data["moisture_inventory"] - data["moisture_inventory"][0]
    moisture_residual = moisture_storage - moisture_boundary_cumulative

    def summary(storage, boundary, residual):
        scale = np.maximum.reduce(
            [np.abs(storage), np.abs(boundary), np.full_like(storage, 1.0e-30)]
        )
        relative = np.abs(residual) / scale
        index = int(np.argmax(np.abs(residual)))
        return {
            "final_storage_integral": float(storage[-1]),
            "final_boundary_integral": float(boundary[-1]),
            "final_absolute_residual": float(residual[-1]),
            "final_relative_residual": float(relative[-1]),
            "max_absolute_residual": float(np.max(np.abs(residual))),
            "max_absolute_residual_time_s": float(time_s[index]),
            "max_relative_residual_after_60s": float(np.max(relative[1:])),
            "max_relative_residual_after_60s_time_s": float(
                time_s[1 + int(np.argmax(relative[1:]))]
            ),
        }

    return {
        "temperature_rate_integral": summary(heat_storage, heat_boundary, heat_residual),
        "moisture_model_integral": summary(
            moisture_storage, moisture_boundary_cumulative, moisture_residual
        ),
    }


def root_branch_checks(data) -> dict[str, object]:
    grid = q3.q2.make_grid(data["cell_centers_m"].size)
    ambient = q3.load_q3_ambient()
    records = []
    maximum_crossings = 0
    for time_value, last_t, last_c in zip(
        data["snapshot_times_s"],
        data["temperature_cells_snapshot_c"][:, -1],
        data["moisture_cells_snapshot"][:, -1],
    ):
        ca = float(ambient.concentration(float(time_value)))
        ta = float(ambient.temperature(float(time_value)))
        samples = np.linspace(float(last_c), ca, 4097)
        half = 0.5 * grid.dr_m
        k_cell = float(q3.q2.thermal_conductivity(float(last_c)))
        d_cell = float(q3.q2.diffusion_coefficient(float(last_c), float(last_t)))
        ks = 0.21 + 0.38 * samples / (samples + 1.0)
        kf = 2.0 * k_cell * ks / (k_cell + ks)
        ts = (kf / half * last_t + q3.H * ta) / (kf / half + q3.H)
        ds = 2.4e-3 * np.exp(-0.45 / samples) * np.exp(-3850.0 / (ts + 273.15))
        df = 2.0 * d_cell * ds / (d_cell + ds)
        residual = df * (samples - last_c) / half + q3.HM * (samples - ca)
        crossings = int(
            np.count_nonzero(
                (residual[:-1] == 0.0) | (residual[:-1] * residual[1:] <= 0.0)
            )
        )
        maximum_crossings = max(maximum_crossings, crossings)
        records.append({"time_s": float(time_value), "sign_change_count": crossings})
    return {
        "all_saved_states_have_at_least_one_bracket": all(
            x["sign_change_count"] >= 1 for x in records
        ),
        "maximum_sign_change_count": maximum_crossings,
        "records": records,
        "note": "4097点扫描用于核验正式129点扫描选择的首个连续物理解。",
    }


def physical_checks(data) -> dict[str, object]:
    temperature = data["temperature_output_c"]
    moisture = data["moisture_output"]
    cmax = data["cmax"]
    terminal = data["terminal_moisture"]
    maximum_index = int(np.argmax(terminal))
    return {
        "all_finite": bool(
            np.all(np.isfinite(temperature))
            and np.all(np.isfinite(moisture))
            and np.all(np.isfinite(terminal))
        ),
        "minimum_moisture": float(np.min(moisture)),
        "nonpositive_moisture_count": int(np.count_nonzero(moisture <= 0.0)),
        "cmax_upward_steps_above_1e-9": int(np.count_nonzero(np.diff(cmax) > 1.0e-9)),
        "cmax_location_not_axis_count": int(np.count_nonzero(data["cmax_radius_m"] > 1.0e-12)),
        "terminal_high_resolution_max": float(terminal[maximum_index]),
        "terminal_high_resolution_max_radius_m": float(data["terminal_radii_m"][maximum_index]),
        "terminal_all_below_threshold": bool(np.max(terminal) <= q3.THRESHOLD + 5.0e-10),
        "maximum_abs_spatial_second_difference_moisture": float(
            np.max(np.abs(np.diff(moisture, n=2, axis=1)))
        ),
        "maximum_abs_temporal_second_difference_moisture": float(
            np.max(np.abs(np.diff(moisture, n=2, axis=0)))
        ),
        "final_axis_temperature_c": float(temperature[-1, 0]),
        "final_surface_temperature_c": float(data["temperature_surface_c"][-1]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if not FORMAL_DATA.exists() or not FORMAL_SUMMARY.exists():
        raise FileNotFoundError("请先从仓库根目录运行 python code/q3/q3_main.py")
    started = time.perf_counter()
    formal = _formal_record()
    case_results: dict[str, dict[str, object]] = {}
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(_run_case, item): item[0] for item in CASES.items()}
        for future in as_completed(futures):
            name, record = future.result()
            case_results[name] = record
            print(f"完成验证算例：{name}, t_end={record['end_time_h']:.9f} h", flush=True)

    convergence = {
        "N513_to_N1025": _comparison(case_results["grid_513"], case_results["grid_1025"]),
        "N1025_to_N2561": _comparison(case_results["grid_1025"], formal),
    }
    tolerance = _comparison(case_results["loose_rtol_1e-7"], formal)
    max_step = _comparison(case_results["max_step_10s"], formal)
    with np.load(FORMAL_DATA) as data:
        balance = instantaneous_balance(data)
        cumulative = cumulative_balance(data)
        physical = physical_checks(data)
        roots = root_branch_checks(data)
    sensitivity = {
        "post_14400_Ca": {
            "0.03": {
                "threshold_reached_within_96h": case_results["post_Ca_0.03"]["threshold_reached"],
                "Cmax_at_96h": case_results["post_Ca_0.03"]["end_max_moisture"],
                "reported_end_time": None,
                "diagnostic_only": True,
                "status": "离散Robin表面方程根分支折叠；不作为正式终止时间预测",
            },
            "0.04986": formal["end_time_s"],
            "0.07": case_results["post_Ca_0.07"]["end_time_s"],
        },
        "post_14400_Ca_end_time_h": {
            "0.03": "未报告（离散非线性表面方程出现根分支折叠）",
            "0.04986": formal["end_time_h"],
            "0.07": case_results["post_Ca_0.07"]["end_time_h"],
        },
    }
    acceptance = {
        "q2_alignment_passed": bool(
            json.loads((q3.RESULTS_DIR / "q3_q2_alignment.json").read_text(encoding="utf-8"))["overall_pass"]
        ),
        "all_values_finite": physical["all_finite"],
        "all_moisture_positive": physical["nonpositive_moisture_count"] == 0,
        "terminal_all_space_below_threshold": physical["terminal_all_below_threshold"],
        "instantaneous_temperature_balance_passed": bool(
            balance["temperature"]["max_relative_residual_nonzero_scale"] < 1.0e-12
            and balance["temperature"]["max_absolute_residual_near_zero_scale_w"] < 1.0e-12
        ),
        "instantaneous_moisture_balance_below_1e-12": balance["moisture"]["max_relative_residual"] < 1.0e-12,
        "max_step_end_time_below_0.1s": max_step["end_time_difference_s"] < 0.1,
        "max_step_table_below_2e-6": max_step["max_abs_table5_regular_times"] < 2.0e-6,
        "tolerance_end_time_below_0.1s": tolerance["end_time_difference_s"] < 0.1,
        "tolerance_table_below_2e-6": tolerance["max_abs_table5_regular_times"] < 2.0e-6,
        "surface_root_bracket_found": roots["all_saved_states_have_at_least_one_bracket"],
        # 以下 5 项判据由既有输出派生，不引入新的重算。
        "terminal_maximum_at_axis": abs(physical["terminal_high_resolution_max_radius_m"]) <= 1.0e-12,
        "grid_end_time_change_below_60s": (
            convergence["N1025_to_N2561"]["end_time_difference_s"] < 60.0
        ),
        "grid_table_change_below_5e-5": (
            convergence["N1025_to_N2561"]["max_abs_table5_regular_times"] < 5.0e-5
        ),
        "cumulative_temperature_final_below_1e-4": (
            cumulative["temperature_rate_integral"]["final_relative_residual"] < 1.0e-4
        ),
        "cumulative_moisture_final_below_1e-3": (
            cumulative["moisture_model_integral"]["final_relative_residual"] < 1.0e-3
        ),
    }
    report = {
        "overall_pass": bool(all(acceptance.values())),
        "formal": formal,
        "acceptance": acceptance,
        "cases": case_results,
        "grid_convergence": convergence,
        "rtol_sensitivity": tolerance,
        "max_step_sensitivity": max_step,
        "instantaneous_balance": balance,
        "cumulative_balance_60s_output": cumulative,
        "physical_checks": physical,
        "surface_root_branch_check": roots,
        "ambient_sensitivity": sensitivity,
        "pending_decision": (
            "Ca=0.03情景的离散非线性Robin表面方程出现多根及根分支折叠，"
            "且折叠位置随界面平均方式和空间网格变化；因此不报告唯一精确t_end，"
            "仅将该情景作为边界与离散敏感性局限。"
        ),
        "total_validation_runtime_s": time.perf_counter() - started,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = json.loads(FORMAL_SUMMARY.read_text(encoding="utf-8"))
    summary["validation_file"] = OUTPUT.relative_to(REPO_ROOT).as_posix()
    summary["validation_overall_pass"] = report["overall_pass"]
    summary["all_checks_successfully_completed"] = report["overall_pass"]
    FORMAL_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if not report["overall_pass"]:
        raise SystemExit("Q3验证未全部通过，请检查q3_validation.json")


if __name__ == "__main__":
    main()
