# 文件名：q1_validation.py
# 用途：该代码负责第一问数值模型的网格收敛性、积分精度、守恒性及数值可靠性检验。

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy.integrate import cumulative_trapezoid

import q1_main as q1


OUTPUT = q1.VALIDATION_DIR / "q1_validation.json"


def field_difference(coarse: q1.Q1Solution, fine: q1.Q1Solution, field: str) -> dict[str, float]:
    if field == "temperature":
        left = coarse.temperature_output_c
        right = fine.temperature_output_c
    elif field == "moisture":
        left = coarse.moisture_output
        right = fine.moisture_output
    else:
        raise ValueError(field)
    difference = left - right
    time_indices = np.searchsorted(coarse.time_s, q1.TABLE_TIMES_S)
    radius_indices = np.searchsorted(q1.OUTPUT_RADII_M, q1.TABLE_RADII_M)
    table_difference = difference[np.ix_(time_indices, radius_indices)]
    return {
        "max_abs_full_output": float(np.max(np.abs(difference))),
        "rms_full_output": float(np.sqrt(np.mean(difference**2))),
        "max_abs_table_points": float(np.max(np.abs(table_difference))),
        "max_abs_final_profile": float(np.max(np.abs(difference[-1]))),
        "surface_abs_at_1800": float(abs(difference[-1, -1])),
        "axis_abs_at_1800": float(abs(difference[-1, 0])),
    }


def balance_metrics(solution: q1.Q1Solution) -> dict[str, dict[str, float]]:
    grid = solution.grid
    times = solution.time_s
    factor = 2.0 * np.pi * q1.LENGTH_M
    temperature_function = q1.temperature_rhs(grid, solution.ambient)
    moisture_function = q1.moisture_rhs(grid, solution.ambient)
    temperature_storage_rate = np.empty(times.size)
    moisture_storage_rate = np.empty(times.size)
    for index, t in enumerate(times):
        temperature_rate = temperature_function(float(t), solution.temperature_cells_c[index])
        moisture_rate = moisture_function(float(t), solution.moisture_cells[index])
        temperature_storage_rate[index] = (
            factor * q1.RHO * q1.CP * np.dot(grid.volumes_rdr_m2, temperature_rate)
        )
        moisture_storage_rate[index] = factor * np.dot(grid.volumes_rdr_m2, moisture_rate)

    ambient_temperature = np.asarray(solution.ambient.temperature(times))
    ambient_moisture = np.asarray(solution.ambient.concentration(times))
    temperature_boundary_flux = -q1.H * (solution.temperature_surface_c - ambient_temperature)
    moisture_boundary_flux = -q1.HM * (solution.moisture_surface - ambient_moisture)
    temperature_boundary_rate = factor * q1.RADIUS_M * temperature_boundary_flux
    moisture_boundary_rate = factor * q1.RADIUS_M * moisture_boundary_flux

    temperature_inventory = (
        factor
        * q1.RHO
        * q1.CP
        * (solution.temperature_cells_c @ grid.volumes_rdr_m2)
    )
    moisture_inventory = factor * (solution.moisture_cells @ grid.volumes_rdr_m2)

    def summarize(storage_rate, boundary_rate, inventory):
        differential = storage_rate - boundary_rate
        boundary_integral = cumulative_trapezoid(boundary_rate, times, initial=0.0)
        cumulative = (inventory - inventory[0]) - boundary_integral
        differential_scale = max(float(np.max(np.abs(boundary_rate))), 1.0e-30)
        cumulative_scale = max(
            float(np.max(np.abs(inventory - inventory[0]))),
            float(np.max(np.abs(boundary_integral))),
            1.0e-30,
        )
        return {
            "differential_max_abs": float(np.max(np.abs(differential))),
            "differential_max_relative": float(np.max(np.abs(differential)) / differential_scale),
            "cumulative_max_abs": float(np.max(np.abs(cumulative))),
            "cumulative_max_relative": float(np.max(np.abs(cumulative)) / cumulative_scale),
            "cumulative_final_abs": float(abs(cumulative[-1])),
            "inventory_change_final": float(inventory[-1] - inventory[0]),
            "integrated_boundary_flux_final": float(boundary_integral[-1]),
        }

    return {
        "temperature_energy": summarize(
            temperature_storage_rate, temperature_boundary_rate, temperature_inventory
        ),
        "moisture_model_inventory": summarize(
            moisture_storage_rate, moisture_boundary_rate, moisture_inventory
        ),
    }


def physical_and_numerical_checks(solution: q1.Q1Solution) -> dict[str, float | int | bool]:
    temperature = solution.temperature_output_c
    moisture = solution.moisture_output
    ambient_temperature = np.asarray(solution.ambient.temperature(solution.time_s))
    ambient_moisture = np.asarray(solution.ambient.concentration(solution.time_s))
    spatial_temperature_reverse = int(np.count_nonzero(np.diff(temperature, axis=1) < -1.0e-7))
    spatial_moisture_reverse = int(np.count_nonzero(np.diff(moisture, axis=1) > 1.0e-8))
    temporal_temperature_reverse = int(np.count_nonzero(np.diff(temperature, axis=0) < -1.0e-7))
    temporal_moisture_reverse = int(np.count_nonzero(np.diff(moisture, axis=0) > 1.0e-8))
    temperature_lower = min(q1.T_INITIAL_C, float(np.min(ambient_temperature)))
    temperature_upper = max(q1.T_INITIAL_C, float(np.max(ambient_temperature)))
    moisture_lower = min(q1.C_INITIAL, float(np.min(ambient_moisture)))
    moisture_upper = max(q1.C_INITIAL, float(np.max(ambient_moisture)))
    return {
        "all_finite": bool(np.all(np.isfinite(temperature)) and np.all(np.isfinite(moisture))),
        "minimum_temperature_c": float(np.min(temperature)),
        "maximum_temperature_c": float(np.max(temperature)),
        "minimum_moisture": float(np.min(moisture)),
        "maximum_moisture": float(np.max(moisture)),
        "negative_moisture_count": int(np.count_nonzero(moisture < 0.0)),
        "spatial_temperature_reverse_steps": spatial_temperature_reverse,
        "spatial_moisture_reverse_steps": spatial_moisture_reverse,
        "temporal_temperature_reverse_steps": temporal_temperature_reverse,
        "temporal_moisture_reverse_steps": temporal_moisture_reverse,
        "temperature_within_input_extrema": bool(
            np.min(temperature) >= temperature_lower - 1.0e-8
            and np.max(temperature) <= temperature_upper + 1.0e-8
        ),
        "moisture_within_input_extrema": bool(
            np.min(moisture) >= moisture_lower - 1.0e-8
            and np.max(moisture) <= moisture_upper + 1.0e-8
        ),
    }


def main() -> None:
    started = time.perf_counter()
    solutions = {}
    grid_sizes = (41, 81, 161, 321, 641, 1281, 2561)
    for cells in grid_sizes:
        print(f"Solving baseline N={cells}", flush=True)
        solutions[cells] = q1.solve_q1(cells=cells)
    print("Solving tight-tolerance N=2561", flush=True)
    tight = q1.solve_q1(
        cells=2561,
        rtol=1.0e-10,
        atol_temperature=1.0e-12,
        atol_moisture=1.0e-13,
        max_step_s=2.0,
    )

    convergence = {}
    grid_pairs = tuple(zip(grid_sizes[:-1], grid_sizes[1:]))
    for coarse, fine in grid_pairs:
        key = f"N{coarse}_vs_N{fine}"
        convergence[key] = {
            "temperature_c": field_difference(solutions[coarse], solutions[fine], "temperature"),
            "moisture": field_difference(solutions[coarse], solutions[fine], "moisture"),
        }
    tolerance = {
        "temperature_c": field_difference(solutions[2561], tight, "temperature"),
        "moisture": field_difference(solutions[2561], tight, "moisture"),
    }
    balance = balance_metrics(solutions[2561])
    checks = physical_and_numerical_checks(solutions[2561])

    coarse_t = convergence["N41_vs_N81"]["temperature_c"]["max_abs_full_output"]
    fine_t = convergence["N81_vs_N161"]["temperature_c"]["max_abs_full_output"]
    coarse_c = convergence["N41_vs_N81"]["moisture"]["max_abs_full_output"]
    fine_c = convergence["N81_vs_N161"]["moisture"]["max_abs_full_output"]
    high_t = convergence["N1281_vs_N2561"]["temperature_c"]["max_abs_full_output"]
    high_c = convergence["N1281_vs_N2561"]["moisture"]["max_abs_full_output"]
    convergence_decreases_t = all(
        convergence[f"N{a}_vs_N{b}"]["temperature_c"]["max_abs_full_output"]
        > convergence[f"N{b}_vs_N{c}"]["temperature_c"]["max_abs_full_output"]
        for a, b, c in zip(grid_sizes[:-2], grid_sizes[1:-1], grid_sizes[2:])
    )
    convergence_decreases_c = all(
        convergence[f"N{a}_vs_N{b}"]["moisture"]["max_abs_full_output"]
        > convergence[f"N{b}_vs_N{c}"]["moisture"]["max_abs_full_output"]
        for a, b, c in zip(grid_sizes[:-2], grid_sizes[1:-1], grid_sizes[2:])
    )
    acceptance = {
        "all_seven_grid_levels_computed": len(solutions) == 7,
        "grid_difference_decreases_temperature_at_every_refinement": convergence_decreases_t,
        "grid_difference_decreases_moisture_at_every_refinement": convergence_decreases_c,
        "N1281_N2561_temperature_max_below_2e_5C": high_t < 2.0e-5,
        "N1281_N2561_moisture_max_below_1e_4": high_c < 1.0e-4,
        "tight_tolerance_temperature_max_below_1e_4C": tolerance["temperature_c"]["max_abs_full_output"] < 1.0e-4,
        "tight_tolerance_moisture_max_below_1e_5": tolerance["moisture"]["max_abs_full_output"] < 1.0e-5,
        "differential_energy_balance_relative_below_1e_12": balance["temperature_energy"]["differential_max_relative"] < 1.0e-12,
        "differential_moisture_balance_relative_below_1e_12": balance["moisture_model_inventory"]["differential_max_relative"] < 1.0e-12,
        "cumulative_energy_balance_relative_below_5e_4": balance["temperature_energy"]["cumulative_max_relative"] < 5.0e-4,
        "cumulative_moisture_balance_relative_below_5e_4": balance["moisture_model_inventory"]["cumulative_max_relative"] < 5.0e-4,
        "all_values_finite": bool(checks["all_finite"]),
        "no_negative_moisture": checks["negative_moisture_count"] == 0,
        "temperature_respects_input_extrema": bool(checks["temperature_within_input_extrema"]),
        "moisture_respects_input_extrema": bool(checks["moisture_within_input_extrema"]),
        "no_observed_spatial_or_temporal_reversal": (
            checks["spatial_temperature_reverse_steps"] == 0
            and checks["spatial_moisture_reverse_steps"] == 0
            and checks["temporal_temperature_reverse_steps"] == 0
            and checks["temporal_moisture_reverse_steps"] == 0
        ),
    }
    overall_pass = all(acceptance.values())
    report = {
        "overall_pass": overall_pass,
        "acceptance": acceptance,
        "baseline_solver": {
            str(cells): {
                "runtime_s": solutions[cells].runtime_s,
                "temperature_nfev": solutions[cells].temperature_nfev,
                "moisture_nfev": solutions[cells].moisture_nfev,
                "tolerances": solutions[cells].tolerances,
            }
            for cells in grid_sizes
        },
        "tight_solver": {
            "runtime_s": tight.runtime_s,
            "temperature_nfev": tight.temperature_nfev,
            "moisture_nfev": tight.moisture_nfev,
            "tolerances": tight.tolerances,
        },
        "convergence": convergence,
        "tolerance_sensitivity_N2561": tolerance,
        "balance_N2561": balance,
        "physical_and_numerical_checks_N2561": checks,
        "total_validation_runtime_s": time.perf_counter() - started,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if not overall_pass:
        raise SystemExit("Q1 validation failed; inspect q1_validation.json")


if __name__ == "__main__":
    main()
