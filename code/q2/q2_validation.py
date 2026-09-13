"""Numerical acceptance tests for the final Q2 coupled solver."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

import q2_main as q2


OUTPUT = q2.VALIDATION_DIR / "q2_validation.json"
GRID_SIZES = (321, 641, 1281, 2561)
KEY_TIMES_S = np.array([1.0, 10.0, 100.0, 10800.0])


def _selected_difference(
    coarse: q2.Q2Solution,
    fine: q2.Q2Solution,
    field_name: str,
) -> dict[str, object]:
    if field_name == "temperature":
        coarse_values = coarse.temperature_output_c
        fine_values = fine.temperature_output_c
    elif field_name == "moisture":
        coarse_values = coarse.moisture_output
        fine_values = fine.moisture_output
    else:
        raise ValueError(field_name)
    difference = np.abs(coarse_values - fine_values)
    table_time_indices = np.searchsorted(q2.OUTPUT_TIMES_S, q2.TABLE_TIMES_S)
    table_radius_indices = np.searchsorted(q2.OUTPUT_RADII_M, q2.TABLE_RADII_M)
    table_difference = difference[np.ix_(table_time_indices, table_radius_indices)]
    key_time_indices = np.searchsorted(q2.OUTPUT_TIMES_S, KEY_TIMES_S)
    surface_difference = difference[key_time_indices, -1]
    final_axis_surface = difference[-1, [0, -1]]
    rounded_mismatch = np.count_nonzero(
        np.round(coarse_values, 4) != np.round(fine_values, 4)
    )
    max_index = np.unravel_index(np.argmax(difference), difference.shape)
    return {
        "max_abs_full_output": float(np.max(difference)),
        "max_location": {
            "time_s": int(q2.OUTPUT_TIMES_S[max_index[0]]),
            "radius_cm": float(q2.OUTPUT_RADII_M[max_index[1]] * 100.0),
        },
        "max_abs_table_points": float(np.max(table_difference)),
        "surface_abs_at_key_times": {
            str(int(t)): float(value)
            for t, value in zip(KEY_TIMES_S, surface_difference)
        },
        "final_axis_abs": float(final_axis_surface[0]),
        "final_surface_abs": float(final_axis_surface[1]),
        "round4_mismatch_count_full_output": int(rounded_mismatch),
        "full_output_value_count": int(difference.size),
    }


def field_difference(
    coarse: q2.Q2Solution, fine: q2.Q2Solution
) -> dict[str, object]:
    return {
        "temperature_c": _selected_difference(
            coarse, fine, "temperature"
        ),
        "moisture": _selected_difference(coarse, fine, "moisture"),
    }


def balance_metrics(solution: q2.Q2Solution) -> dict[str, object]:
    geometry_factor = 2.0 * np.pi * q2.LENGTH_M
    temperature_records = []
    moisture_records = []
    for index, time_value in enumerate(solution.snapshot_times_s):
        if time_value <= 0.0:
            continue
        temperature = solution.temperature_cells_snapshot_c[index]
        moisture = solution.moisture_cells_snapshot[index]
        state = np.r_[temperature, moisture]
        derivative, heat_flux, moisture_flux, _ = q2.rhs_and_fluxes(
            float(time_value), state, solution.grid, solution.ambient
        )
        temperature_rate = derivative[: solution.grid.cells]
        moisture_rate = derivative[solution.grid.cells :]
        temperature_storage = geometry_factor * np.sum(
            np.asarray(q2.density(moisture))
            * np.asarray(q2.heat_capacity(moisture))
            * temperature_rate
            * solution.grid.volumes_rdr_m2
        )
        temperature_boundary = (
            geometry_factor * q2.RADIUS_M * heat_flux[-1]
        )
        moisture_storage = geometry_factor * np.sum(
            moisture_rate * solution.grid.volumes_rdr_m2
        )
        moisture_boundary = (
            geometry_factor * q2.RADIUS_M * moisture_flux[-1]
        )
        temperature_scale = max(
            abs(float(temperature_storage)),
            abs(float(temperature_boundary)),
            1.0e-30,
        )
        moisture_scale = max(
            abs(float(moisture_storage)),
            abs(float(moisture_boundary)),
            1.0e-30,
        )
        temperature_records.append(
            {
                "time_s": float(time_value),
                "storage_rate_w": float(temperature_storage),
                "boundary_rate_w": float(temperature_boundary),
                "absolute_residual_w": float(
                    temperature_storage - temperature_boundary
                ),
                "relative_residual": float(
                    abs(temperature_storage - temperature_boundary)
                    / temperature_scale
                ),
            }
        )
        moisture_records.append(
            {
                "time_s": float(time_value),
                "inventory_rate": float(moisture_storage),
                "boundary_rate": float(moisture_boundary),
                "absolute_residual": float(
                    moisture_storage - moisture_boundary
                ),
                "relative_residual": float(
                    abs(moisture_storage - moisture_boundary)
                    / moisture_scale
                ),
            }
        )
    return {
        "temperature_instantaneous": {
            "max_relative_residual": float(
                max(record["relative_residual"] for record in temperature_records)
            ),
            "max_absolute_residual_w": float(
                max(
                    abs(record["absolute_residual_w"])
                    for record in temperature_records
                )
            ),
            "records": temperature_records,
        },
        "moisture_model_instantaneous": {
            "max_relative_residual": float(
                max(record["relative_residual"] for record in moisture_records)
            ),
            "max_absolute_residual": float(
                max(
                    abs(record["absolute_residual"])
                    for record in moisture_records
                )
            ),
            "records": moisture_records,
        },
    }


def cumulative_balance_metrics(solution: q2.Q2Solution) -> dict[str, object]:
    """Check cumulative balances using the formal one-second output record.

    For temperature, the storage term is the path integral of
    rho(C) cp(C) dT over all finite volumes; it is not interpreted as the
    difference of a state function.  For moisture, the inventory is the
    spatial integral of C from the finite-volume cell states.
    """
    time_s = solution.time_s
    heat_storage = solution.heat_storage_cumulative_j
    heat_boundary = solution.heat_boundary_cumulative_j
    heat_residual = heat_storage - heat_boundary

    moisture_boundary_cumulative = np.zeros_like(time_s)
    increments = 0.5 * (
        solution.moisture_boundary_rate[:-1]
        + solution.moisture_boundary_rate[1:]
    ) * np.diff(time_s)
    moisture_boundary_cumulative[1:] = np.cumsum(increments)
    moisture_inventory_change = (
        solution.moisture_inventory - solution.moisture_inventory[0]
    )
    moisture_residual = moisture_inventory_change - moisture_boundary_cumulative

    def summarize(
        storage: np.ndarray, boundary: np.ndarray, residual: np.ndarray
    ) -> dict[str, object]:
        scale = np.maximum.reduce(
            [np.abs(storage), np.abs(boundary), np.full_like(storage, 1.0e-30)]
        )
        relative = np.abs(residual) / scale
        worst_absolute_index = int(np.argmax(np.abs(residual)))
        final_scale = max(abs(float(storage[-1])), abs(float(boundary[-1])), 1.0e-30)
        return {
            "final_storage_integral": float(storage[-1]),
            "final_boundary_integral": float(boundary[-1]),
            "final_absolute_residual": float(residual[-1]),
            "final_relative_residual": float(abs(residual[-1]) / final_scale),
            "max_absolute_residual": float(np.max(np.abs(residual))),
            "max_absolute_residual_time_s": int(time_s[worst_absolute_index]),
            "max_relative_residual_after_10s": float(np.max(relative[10:])),
            "max_relative_residual_after_10s_time_s": int(
                time_s[10 + int(np.argmax(relative[10:]))]
            ),
        }

    return {
        "temperature_rate_integral": summarize(
            heat_storage, heat_boundary, heat_residual
        ),
        "moisture_model_integral": summarize(
            moisture_inventory_change,
            moisture_boundary_cumulative,
            moisture_residual,
        ),
        "note": (
            "Temperature storage is the time integral of integral(rho*cp*T_t)dV, "
            "not endpoint integral(rho*cp*T)dV. Moisture inventory is integral(C)dV."
        ),
    }


def physical_checks(solution: q2.Q2Solution) -> dict[str, object]:
    temperature = solution.temperature_output_c
    moisture = solution.moisture_output
    spatial_temperature_reverse = int(
        np.count_nonzero(np.diff(temperature, axis=1) < -1.0e-7)
    )
    spatial_moisture_reverse = int(
        np.count_nonzero(np.diff(moisture, axis=1) > 1.0e-7)
    )

    def profiles_with_multiple_turns(
        field: np.ndarray, difference_tolerance: float
    ) -> int:
        count = 0
        for profile in field:
            differences = np.diff(profile)
            signs = np.sign(
                differences[np.abs(differences) > difference_tolerance]
            )
            if signs.size > 1 and np.count_nonzero(signs[1:] != signs[:-1]) > 1:
                count += 1
        return count

    temperature_multiple_turns = profiles_with_multiple_turns(
        temperature, 1.0e-7
    )
    moisture_multiple_turns = profiles_with_multiple_turns(
        moisture, 1.0e-8
    )
    later_temperature_second_difference = np.diff(
        temperature[100:], n=2, axis=0
    )
    later_moisture_second_difference = np.diff(
        moisture[100:], n=2, axis=0
    )
    properties = q2.initial_properties()
    final_temperature = temperature[-1, [0, -1]]
    final_moisture = moisture[-1, [0, -1]]
    initial_formula_ok = (
        abs(properties["rho_kg_m3"] - 976.4) < 1.0e-9
        and 3410.0 < properties["cp_j_kg_k"] < 3420.0
        and 0.482 < properties["k_w_m_k"] < 0.484
        and 5.5e-9 < properties["D_m2_s"] < 5.8e-9
    )
    return {
        "all_finite": bool(
            np.all(np.isfinite(temperature))
            and np.all(np.isfinite(moisture))
        ),
        "minimum_temperature_c": float(np.min(temperature)),
        "maximum_temperature_c": float(np.max(temperature)),
        "minimum_moisture": float(np.min(moisture)),
        "maximum_moisture": float(np.max(moisture)),
        "nonpositive_moisture_count": int(np.count_nonzero(moisture <= 0.0)),
        "spatial_temperature_reverse_steps": spatial_temperature_reverse,
        "spatial_moisture_reverse_steps": spatial_moisture_reverse,
        "temperature_profiles_with_multiple_turns": temperature_multiple_turns,
        "moisture_profiles_with_multiple_turns": moisture_multiple_turns,
        "max_abs_temperature_second_difference_after_100s": float(
            np.max(np.abs(later_temperature_second_difference))
        ),
        "max_abs_moisture_second_difference_after_100s": float(
            np.max(np.abs(later_moisture_second_difference))
        ),
        "initial_properties": properties,
        "initial_formula_check": bool(initial_formula_ok),
        "temperature_characteristic_time_s": float(
            properties["tau_temperature_s"]
        ),
        "moisture_characteristic_time_s": float(
            properties["tau_moisture_s"]
        ),
        "final_axis_temperature_c": float(final_temperature[0]),
        "final_surface_temperature_c": float(final_temperature[1]),
        "final_axis_moisture": float(final_moisture[0]),
        "final_surface_moisture": float(final_moisture[1]),
        "first_1800s_trend_check": bool(
            temperature[1800, -1] > temperature[1800, 0]
            and moisture[1800, -1] < moisture[1800, 0]
        ),
    }


def main() -> None:
    started = time.perf_counter()
    properties = q2.print_initial_properties()
    solutions: dict[int, q2.Q2Solution] = {}
    for cells in GRID_SIZES:
        print(f"Solving Q2 baseline N={cells}", flush=True)
        solutions[cells] = q2.solve_q2(cells=cells)

    print("Solving Q2 tight-tolerance N=2561", flush=True)
    tight = q2.solve_q2(
        cells=2561,
        rtol=1.0e-10,
        atol_temperature=1.0e-12,
        atol_moisture=1.0e-13,
        max_step_s=2.0,
    )

    convergence = {}
    for coarse, fine in zip(GRID_SIZES[:-1], GRID_SIZES[1:]):
        convergence[f"N{coarse}_vs_N{fine}"] = field_difference(
            solutions[coarse], solutions[fine]
        )
    tolerance = field_difference(solutions[2561], tight)
    balance = balance_metrics(solutions[2561])
    cumulative_balance = cumulative_balance_metrics(solutions[2561])
    checks = physical_checks(solutions[2561])

    high = convergence["N1281_vs_N2561"]
    acceptance = {
        "all_four_grid_levels_computed": len(solutions) == 4,
        "initial_property_formula_check": bool(checks["initial_formula_check"]),
        "N1281_N2561_temperature_full_below_5e_5C": (
            high["temperature_c"]["max_abs_full_output"] < 5.0e-5
        ),
        "N1281_N2561_moisture_full_below_1e_4": (
            high["moisture"]["max_abs_full_output"] < 1.0e-4
        ),
        "N1281_N2561_table_temperature_below_2e_5C": (
            high["temperature_c"]["max_abs_table_points"] < 2.0e-5
        ),
        "N1281_N2561_table_moisture_below_2e_5": (
            high["moisture"]["max_abs_table_points"] < 2.0e-5
        ),
        "tight_tolerance_temperature_table_below_2e_5C": (
            tolerance["temperature_c"]["max_abs_table_points"] < 2.0e-5
        ),
        "tight_tolerance_moisture_table_below_2e_6": (
            tolerance["moisture"]["max_abs_table_points"] < 2.0e-6
        ),
        "temperature_balance_relative_below_1e_12": (
            balance["temperature_instantaneous"]["max_relative_residual"]
            < 1.0e-12
        ),
        "moisture_balance_relative_below_1e_12": (
            balance["moisture_model_instantaneous"]["max_relative_residual"]
            < 1.0e-12
        ),
        "temperature_cumulative_balance_relative_below_1e_4": (
            cumulative_balance["temperature_rate_integral"][
                "final_relative_residual"
            ]
            < 1.0e-4
        ),
        "moisture_cumulative_balance_relative_below_1e_4": (
            cumulative_balance["moisture_model_integral"][
                "final_relative_residual"
            ]
            < 1.0e-4
        ),
        "all_values_finite": bool(checks["all_finite"]),
        "all_moisture_positive": checks["nonpositive_moisture_count"] == 0,
        "no_obvious_temperature_spatial_sawtooth": (
            checks["max_abs_temperature_second_difference_after_100s"]
            < 1.0e-3
        ),
        "no_obvious_moisture_spatial_sawtooth": (
            checks["max_abs_moisture_second_difference_after_100s"]
            < 1.0e-4
        ),
        "first_1800s_physical_trend": bool(
            checks["first_1800s_trend_check"]
        ),
    }
    report = {
        "overall_pass": bool(all(acceptance.values())),
        "formal_grid_cells": 2561,
        "formal_solver": {
            "method": "BDF",
            "rtol": 1.0e-8,
            "atol_temperature": 1.0e-10,
            "atol_moisture": 1.0e-11,
            "max_step_s": 10.0,
        },
        "initial_properties": properties,
        "acceptance": acceptance,
        "baseline_solver": {
            str(cells): {
                "runtime_s": solutions[cells].runtime_s,
                "nfev": solutions[cells].nfev,
                "njev": solutions[cells].njev,
                "nlu": solutions[cells].nlu,
                "tolerances": solutions[cells].tolerances,
            }
            for cells in GRID_SIZES
        },
        "tight_solver": {
            "runtime_s": tight.runtime_s,
            "nfev": tight.nfev,
            "njev": tight.njev,
            "nlu": tight.nlu,
            "tolerances": tight.tolerances,
        },
        "convergence": convergence,
        "tolerance_sensitivity_N2561": tolerance,
        "balance_N2561": balance,
        "cumulative_balance_N2561": cumulative_balance,
        "physical_and_numerical_checks_N2561": checks,
        "total_validation_runtime_s": time.perf_counter() - started,
    }
    q2.VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary_path = q2.RESULTS_DIR / "q2_run_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["validation_file"] = OUTPUT.relative_to(q2.Q2_ROOT).as_posix()
        summary["validation_overall_pass"] = report["overall_pass"]
        summary["all_checks_successfully_completed"] = report["overall_pass"]
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if not report["overall_pass"]:
        raise SystemExit("Q2 validation failed; inspect q2_validation.json")


if __name__ == "__main__":
    main()
