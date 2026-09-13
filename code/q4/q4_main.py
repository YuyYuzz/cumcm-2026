"""2026 数模国赛 A 题问题四：移动半径材料坐标耦合求解器。

所有写入默认只发生在脚本所在目录。脚本可在隔离工作区直接运行；人工入库后，
仍可通过相对仓库根目录读取原始附件，但不会修改原始文件。
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import numpy as np
from openpyxl import load_workbook
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
from scipy.sparse import bmat, diags


SCRIPT_DIR = Path(__file__).resolve().parent
IN_REPOSITORY_LAYOUT = (
    SCRIPT_DIR.name.casefold() == "q4" and SCRIPT_DIR.parent.name.casefold() == "code"
)
PROJECT_ROOT = SCRIPT_DIR.parents[1] if IN_REPOSITORY_LAYOUT else SCRIPT_DIR.parent
OUTPUT_DIR = (
    PROJECT_ROOT / "results" / "q4" if IN_REPOSITORY_LAYOUT else SCRIPT_DIR
)
TABLES_DIR = PROJECT_ROOT / "tables" / "q4" if IN_REPOSITORY_LAYOUT else SCRIPT_DIR


def _problem_root_candidates() -> list[Path]:
    """Return portable, read-only candidate roots for official problem files."""
    if IN_REPOSITORY_LAYOUT:
        return [PROJECT_ROOT / "data" / "raw" / "problems"]
    return [
        PROJECT_ROOT / "CUMCM2026Problems",
        PROJECT_ROOT.parent / "cumcm-2026" / "data" / "raw" / "problems",
    ]


def _find_input(relative: Path) -> Path:
    found = [root / relative for root in _problem_root_candidates() if (root / relative).exists()]
    if not found:
        raise FileNotFoundError(f"无法定位正式输入 {relative.as_posix()}")
    if len(found) > 1:
        contents = [path.read_bytes() for path in found]
        if any(blob != contents[0] for blob in contents[1:]):
            raise RuntimeError(f"多个正式输入副本内容不一致：{found}")
    return found[0]


ATTACHMENT_1 = _find_input(Path("A题") / "附件" / "附件1.xlsx")
ATTACHMENT_2 = _find_input(Path("A题") / "附件" / "附件2.xlsx")
OFFICIAL_TEMPLATE = _find_input(Path("A题") / "附件" / "附件3" / "result4.xlsx")

LENGTH_M = 0.25
FIXED_RADIUS_M = 0.02
H = 25.0
HM = 8.0e-7
T_INITIAL_C = 28.0
C_INITIAL = 2.55
THRESHOLD = 0.15
AMBIENT_DATA_END_S = 14400.0
POST_TEMPERATURE_C = 50.165
POST_MOISTURE = 0.04986
INTEGRATION_UPPER_S = 160.0 * 3600.0
OUTPUT_INTERVAL_S = 60.0
FIXED_OUTPUT_RADII_M = np.arange(0.0, 0.020, 0.001)  # 0,0.1,...,1.9 cm
TABLE_FIXED_RADII_M = np.array([0.0, 0.005, 0.010, 0.015])
REPORT_HOURS = np.arange(6.0, 160.0, 6.0)
ROOT_AUDIT_BASE_S = np.array([1, 4, 6, 12, 24, 36, 48], dtype=float) * 3600.0
PROFILE_BASE_S = np.array([6, 12, 18, 30, 42], dtype=float) * 3600.0

PropertySet = Literal["appendix3", "appendix4"]
GeometryMode = Literal["fixed", "moving"]
RadiusInterpolation = Literal["pchip", "linear"]


def record_path(path: Path) -> str:
    """Record a portable path relative to the current project/work root."""
    resolved = path.resolve()
    for root in (PROJECT_ROOT.resolve(), PROJECT_ROOT.parent.resolve()):
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            continue
    return path.name


@dataclass(frozen=True)
class AmbientData:
    time_s: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray

    @staticmethod
    def _return(values: np.ndarray, original):
        return float(values) if np.asarray(original).ndim == 0 else values

    def temperature(self, t):
        x = np.asarray(t, dtype=float)
        if np.any(x < -1.0e-9):
            raise ValueError("环境时间不得小于0")
        y = np.interp(np.minimum(x, AMBIENT_DATA_END_S), self.time_s, self.temperature_c)
        y = np.where(x > AMBIENT_DATA_END_S, POST_TEMPERATURE_C, y)
        return self._return(np.asarray(y), t)

    def concentration(self, t):
        x = np.asarray(t, dtype=float)
        if np.any(x < -1.0e-9):
            raise ValueError("环境时间不得小于0")
        y = np.interp(np.minimum(x, AMBIENT_DATA_END_S), self.time_s, self.moisture)
        y = np.where(x > AMBIENT_DATA_END_S, POST_MOISTURE, y)
        return self._return(np.asarray(y), t)


@dataclass(frozen=True)
class RadiusData:
    time_s: np.ndarray
    radius_m: np.ndarray
    mode: GeometryMode
    interpolation: RadiusInterpolation
    _pchip: PchipInterpolator | None

    @classmethod
    def build(
        cls,
        time_s: np.ndarray,
        radius_m: np.ndarray,
        mode: GeometryMode,
        interpolation: RadiusInterpolation,
    ) -> "RadiusData":
        pchip = PchipInterpolator(time_s, radius_m, extrapolate=False) if interpolation == "pchip" else None
        return cls(time_s, radius_m, mode, interpolation, pchip)

    @staticmethod
    def _return(values: np.ndarray, original):
        return float(values) if np.asarray(original).ndim == 0 else values

    def radius(self, t):
        x = np.asarray(t, dtype=float)
        if np.any(x < -1.0e-9):
            raise ValueError("半径时间不得小于0")
        if self.mode == "fixed":
            y = np.full_like(x, FIXED_RADIUS_M, dtype=float)
        else:
            clipped = np.minimum(x, self.time_s[-1])
            if self.interpolation == "pchip":
                y = np.asarray(self._pchip(clipped), dtype=float)
            else:
                y = np.interp(clipped, self.time_s, self.radius_m)
            y = np.where(x > self.time_s[-1], self.radius_m[-1], y)
        return self._return(np.asarray(y), t)


@dataclass(frozen=True)
class XiGrid:
    cells: int
    faces: np.ndarray
    centers: np.ndarray
    volumes_xidxi: np.ndarray
    dxi: float


@dataclass
class Q4Solution:
    grid: XiGrid
    property_set: PropertySet
    geometry: GeometryMode
    radius_interpolation: RadiusInterpolation
    ambient: AmbientData
    radius_data: RadiusData
    time_s: np.ndarray
    radius_m: np.ndarray
    temperature_fixed_c: np.ndarray
    moisture_fixed: np.ndarray
    temperature_surface_c: np.ndarray
    moisture_surface: np.ndarray
    temperature_axis_c: np.ndarray
    moisture_axis: np.ndarray
    ambient_temperature_c: np.ndarray
    ambient_moisture: np.ndarray
    moisture_inventory: np.ndarray
    moisture_boundary_rate: np.ndarray
    cmax: np.ndarray
    cmax_radius_m: np.ndarray
    snapshot_times_s: np.ndarray
    temperature_cells_snapshot_c: np.ndarray
    moisture_cells_snapshot: np.ndarray
    terminal_xi: np.ndarray
    terminal_moisture: np.ndarray
    end_time_s: float
    end_max_moisture: float
    end_max_radius_m: float
    nfev: int
    njev: int
    nlu: int
    runtime_s: float
    tolerances: dict[str, float]


def _load_numeric_sheet(path: Path, expected_columns: int) -> np.ndarray:
    workbook = load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook.active
    rows = list(worksheet.iter_rows(values_only=True))
    workbook.close()
    values = np.asarray(
        [row[:expected_columns] for row in rows[1:] if row[0] is not None], dtype=float
    )
    if values.ndim != 2 or values.shape[1] != expected_columns or not np.all(np.isfinite(values)):
        raise ValueError(f"输入文件结构或数值异常：{path.name}")
    return values


def load_ambient(path: Path = ATTACHMENT_1) -> AmbientData:
    values = _load_numeric_sheet(path, 3)
    expected = np.arange(0.0, AMBIENT_DATA_END_S + 60.0, 60.0)
    if values.shape != (241, 3) or not np.array_equal(values[:, 0], expected):
        raise ValueError("附件1必须为0,60,...,14400 s共241条记录")
    if abs(values[-1, 1] - POST_TEMPERATURE_C) > 1.0e-12 or abs(values[-1, 2] - POST_MOISTURE) > 1.0e-12:
        raise ValueError("附件1末值与冻结环境端点不一致")
    return AmbientData(values[:, 0], values[:, 1], values[:, 2])


def load_radius_data(
    path: Path = ATTACHMENT_2,
    mode: GeometryMode = "moving",
    interpolation: RadiusInterpolation = "pchip",
) -> RadiusData:
    values = _load_numeric_sheet(path, 2)
    expected = np.arange(0.0, 259200.0 + 1800.0, 1800.0)
    radius_m = values[:, 1] * 0.01
    if values.shape != (145, 2) or not np.array_equal(values[:, 0], expected):
        raise ValueError("附件2必须为0,1800,...,259200 s共145条记录")
    if np.any(np.diff(radius_m) > 1.0e-14):
        raise ValueError("附件2半径不是整体非增")
    if abs(radius_m[0] - FIXED_RADIUS_M) > 1.0e-14 or abs(radius_m[-1] - 0.01198) > 1.0e-14:
        raise ValueError("附件2首末半径与题面核验值不一致")
    return RadiusData.build(values[:, 0], radius_m, mode, interpolation)


def radius_audit(radius_data: RadiusData) -> dict[str, object]:
    node_error = float(np.max(np.abs(radius_data.radius(radius_data.time_s) - (
        np.full_like(radius_data.radius_m, FIXED_RADIUS_M)
        if radius_data.mode == "fixed" else radius_data.radius_m
    ))))
    hours = np.array([0, 6, 12, 24, 36, 48], dtype=float)
    return {
        "input_file": record_path(ATTACHMENT_2),
        "records": int(radius_data.time_s.size),
        "time_range_s": [float(radius_data.time_s[0]), float(radius_data.time_s[-1])],
        "input_monotone_nonincreasing": bool(np.all(np.diff(radius_data.radius_m) <= 0.0)),
        "interpolation": radius_data.interpolation,
        "mode": radius_data.mode,
        "node_max_abs_error_m": node_error,
        "audit_hours": hours.tolist(),
        "audit_radius_m": np.asarray(radius_data.radius(hours * 3600.0)).tolist(),
        "attachment_last_radius_m": float(radius_data.radius_m[-1]),
        "post_attachment_rule": "hold last radius constant",
    }


def make_grid(cells: int) -> XiGrid:
    if cells < 3:
        raise ValueError("至少需要3个控制体")
    faces = np.linspace(0.0, 1.0, cells + 1)
    centers = 0.5 * (faces[:-1] + faces[1:])
    volumes = 0.5 * (faces[1:] ** 2 - faces[:-1] ** 2)
    return XiGrid(cells, faces, centers, volumes, 1.0 / cells)


def _return_like(result: np.ndarray, original):
    return float(result) if np.asarray(original).ndim == 0 else result


def density(concentration, property_set: PropertySet = "appendix4"):
    c = np.asarray(concentration, dtype=float)
    if np.any(c <= 0.0) or not np.all(np.isfinite(c)):
        raise FloatingPointError("水分浓度必须保持有限且为正")
    y = 650.0 + 128.0 * c if property_set == "appendix3" else 760.0 + 90.0 * c
    return _return_like(y, concentration)


def heat_capacity(concentration, property_set: PropertySet = "appendix4"):
    c = np.asarray(concentration, dtype=float)
    if np.any(c <= 0.0) or not np.all(np.isfinite(c)):
        raise FloatingPointError("水分浓度必须保持有限且为正")
    y = (1450.0 + 2736.0 * c / (c + 1.0)) if property_set == "appendix3" else (1850.0 + 2150.0 * c / (c + 1.0))
    return _return_like(y, concentration)


def thermal_conductivity(concentration, property_set: PropertySet = "appendix4"):
    c = np.asarray(concentration, dtype=float)
    if np.any(c <= 0.0) or not np.all(np.isfinite(c)):
        raise FloatingPointError("水分浓度必须保持有限且为正")
    y = (0.21 + 0.38 * c / (c + 1.0)) if property_set == "appendix3" else (0.12 + 0.20 * c / (c + 1.0))
    return _return_like(y, concentration)


def diffusion_coefficient(concentration, temperature_c, property_set: PropertySet = "appendix4"):
    c = np.asarray(concentration, dtype=float)
    t = np.asarray(temperature_c, dtype=float)
    tk = t + 273.15
    if np.any(c <= 0.0) or np.any(tk <= 0.0) or not np.all(np.isfinite(c)) or not np.all(np.isfinite(t)):
        raise FloatingPointError("D公式输入必须保持有限、C>0、T_K>0")
    if property_set == "appendix3":
        y = 2.4e-3 * np.exp(-0.45 / c) * np.exp(-3850.0 / tk)
    else:
        y = 4.2e-4 * np.exp(-0.30 / c) * np.exp(-3850.0 / tk)
    return float(y) if c.ndim == 0 and t.ndim == 0 else y


def initial_properties(property_set: PropertySet = "appendix4") -> dict[str, float]:
    rho = float(density(C_INITIAL, property_set))
    cp = float(heat_capacity(C_INITIAL, property_set))
    k = float(thermal_conductivity(C_INITIAL, property_set))
    d = float(diffusion_coefficient(C_INITIAL, T_INITIAL_C, property_set))
    alpha = k / (rho * cp)
    return {
        "rho_kg_m3": rho,
        "cp_j_kg_k": cp,
        "k_w_m_k": k,
        "D_m2_s": d,
        "alpha_m2_s": alpha,
        "tau_temperature_s_at_R0": FIXED_RADIUS_M**2 / alpha,
        "tau_moisture_s_at_R0": FIXED_RADIUS_M**2 / d,
    }


def harmonic_mean(left, right):
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    y = 2.0 * a * b / (a + b)
    return float(y) if a.ndim == 0 and b.ndim == 0 else y


def _surface_residual_components(
    cell_temperature_c: float,
    cell_concentration: float,
    ambient_temperature_c: float,
    ambient_concentration: float,
    radius_m: float,
    dxi: float,
    property_set: PropertySet,
):
    half_width_m = radius_m * dxi * 0.5
    k_cell = float(thermal_conductivity(cell_concentration, property_set))
    d_cell = float(diffusion_coefficient(cell_concentration, cell_temperature_c, property_set))

    def temperature_for_c(surface_concentration: float) -> float:
        k_surface = float(thermal_conductivity(surface_concentration, property_set))
        conductance = float(harmonic_mean(k_cell, k_surface)) / half_width_m
        return float((conductance * cell_temperature_c + H * ambient_temperature_c) / (conductance + H))

    def residual(surface_concentration: float) -> float:
        surface_temperature = temperature_for_c(surface_concentration)
        d_surface = float(diffusion_coefficient(surface_concentration, surface_temperature, property_set))
        d_face = float(harmonic_mean(d_cell, d_surface))
        return d_face * (surface_concentration - cell_concentration) / half_width_m + HM * (surface_concentration - ambient_concentration)

    return temperature_for_c, residual


def scan_surface_roots(
    cell_temperature_c: float,
    cell_concentration: float,
    ambient_temperature_c: float,
    ambient_concentration: float,
    radius_m: float,
    dxi: float,
    property_set: PropertySet,
    points: int = 4097,
) -> list[float]:
    _, residual = _surface_residual_components(
        cell_temperature_c, cell_concentration, ambient_temperature_c,
        ambient_concentration, radius_m, dxi, property_set,
    )
    if abs(cell_concentration - ambient_concentration) <= 1.0e-14:
        return [float(cell_concentration)]
    samples = np.linspace(cell_concentration, ambient_concentration, points)
    values = np.asarray([residual(float(x)) for x in samples])
    roots: list[float] = []
    for i in range(points - 1):
        if values[i] == 0.0:
            root = float(samples[i])
        elif values[i] * values[i + 1] < 0.0:
            lo, hi = sorted((float(samples[i]), float(samples[i + 1])))
            root = float(brentq(residual, lo, hi, xtol=1.0e-13, rtol=1.0e-13))
        else:
            continue
        if not roots or abs(root - roots[-1]) > 1.0e-10:
            roots.append(root)
    if values[-1] == 0.0 and (not roots or abs(float(samples[-1]) - roots[-1]) > 1.0e-10):
        roots.append(float(samples[-1]))
    return roots


def surface_states(
    cell_temperature_c: float,
    cell_concentration: float,
    ambient_temperature_c: float,
    ambient_concentration: float,
    radius_m: float,
    dxi: float,
    property_set: PropertySet,
) -> tuple[float, float, float, float]:
    """Return T_s, C_s and xi-coordinate fluxes k*T_xi, D*C_xi."""
    temperature_for_c, residual = _surface_residual_components(
        cell_temperature_c, cell_concentration, ambient_temperature_c,
        ambient_concentration, radius_m, dxi, property_set,
    )
    if abs(cell_concentration - ambient_concentration) <= 1.0e-14:
        cs = float(cell_concentration)
    else:
        samples = np.linspace(cell_concentration, ambient_concentration, 129)
        half_width_m = radius_m * dxi * 0.5
        k_cell = float(thermal_conductivity(cell_concentration, property_set))
        d_cell = float(diffusion_coefficient(cell_concentration, cell_temperature_c, property_set))
        k_surface = np.asarray(thermal_conductivity(samples, property_set))
        conductance = harmonic_mean(k_cell, k_surface) / half_width_m
        sample_temperature = (
            conductance * cell_temperature_c + H * ambient_temperature_c
        ) / (conductance + H)
        d_surface = np.asarray(diffusion_coefficient(samples, sample_temperature, property_set))
        residual_values = (
            harmonic_mean(d_cell, d_surface)
            * (samples - cell_concentration)
            / half_width_m
            + HM * (samples - ambient_concentration)
        )
        crossings = np.flatnonzero(
            (residual_values[:-1] == 0.0)
            | (residual_values[:-1] * residual_values[1:] <= 0.0)
        )
        bracket = None if crossings.size == 0 else (
            float(samples[int(crossings[0])]),
            float(samples[int(crossings[0]) + 1]),
        )
        if bracket is None:
            raise RuntimeError("无法括住连续的表面水分物理解")
        if bracket[0] == bracket[1]:
            cs = bracket[0]
        else:
            lo, hi = sorted(bracket)
            cs = float(brentq(residual, lo, hi, xtol=1.0e-13, rtol=1.0e-13))
    ts = temperature_for_c(cs)
    heat_flux_xi = -radius_m * H * (ts - ambient_temperature_c)
    moisture_flux_xi = -radius_m * HM * (cs - ambient_concentration)
    return ts, cs, float(heat_flux_xi), float(moisture_flux_xi)


def jacobian_sparsity(cells: int):
    tri = diags(
        [np.ones(cells - 1), np.ones(cells), np.ones(cells - 1)],
        offsets=[-1, 0, 1], shape=(cells, cells), format="csr",
    )
    return bmat([[tri, tri], [tri, tri]], format="csr")


def rhs_and_fluxes(
    t: float,
    state: np.ndarray,
    grid: XiGrid,
    ambient: AmbientData,
    radius_data: RadiusData,
    property_set: PropertySet,
):
    n = grid.cells
    temperature = state[:n]
    concentration = state[n:]
    radius_m = float(radius_data.radius(t))
    rho = np.asarray(density(concentration, property_set))
    cp = np.asarray(heat_capacity(concentration, property_set))
    k_cell = np.asarray(thermal_conductivity(concentration, property_set))
    d_cell = np.asarray(diffusion_coefficient(concentration, temperature, property_set))
    heat_flux = np.zeros(n + 1)
    moisture_flux = np.zeros(n + 1)
    heat_flux[1:-1] = harmonic_mean(k_cell[:-1], k_cell[1:]) * np.diff(temperature) / grid.dxi
    moisture_flux[1:-1] = harmonic_mean(d_cell[:-1], d_cell[1:]) * np.diff(concentration) / grid.dxi
    ts, cs, heat_flux[-1], moisture_flux[-1] = surface_states(
        float(temperature[-1]), float(concentration[-1]),
        float(ambient.temperature(t)), float(ambient.concentration(t)),
        radius_m, grid.dxi, property_set,
    )
    heat_div = (grid.faces[1:] * heat_flux[1:] - grid.faces[:-1] * heat_flux[:-1]) / grid.volumes_xidxi
    moisture_div = (grid.faces[1:] * moisture_flux[1:] - grid.faces[:-1] * moisture_flux[:-1]) / grid.volumes_xidxi
    derivative = np.r_[heat_div / (radius_m**2 * rho * cp), moisture_div / radius_m**2]
    return derivative, heat_flux, moisture_flux, (ts, cs)


def coupled_rhs(grid, ambient, radius_data, property_set):
    def rhs(t: float, state: np.ndarray) -> np.ndarray:
        return rhs_and_fluxes(t, state, grid, ambient, radius_data, property_set)[0]
    return rhs


def axis_value(values: np.ndarray, grid: XiGrid) -> float:
    x0, x1 = grid.centers[0] ** 2, grid.centers[1] ** 2
    return float((values[0] * x1 - values[1] * x0) / (x1 - x0))


def reconstruct_profile(cell_values: np.ndarray, surface_value: float, grid: XiGrid, xi_query: np.ndarray) -> np.ndarray:
    axis = axis_value(cell_values, grid)
    x = np.r_[0.0, grid.centers, 1.0]
    y = np.r_[axis, cell_values, surface_value]
    return np.asarray(PchipInterpolator(x, y, extrapolate=False)(xi_query))


def cmax_and_location(t, state, grid, ambient, radius_data, property_set):
    n = grid.cells
    c = state[n:]
    _, cs, _, _ = surface_states(
        float(state[n - 1]), float(c[-1]), float(ambient.temperature(t)),
        float(ambient.concentration(t)), float(radius_data.radius(t)), grid.dxi,
        property_set,
    )
    values = np.r_[axis_value(c, grid), c, cs]
    radius_m = float(radius_data.radius(t))
    radii = np.r_[0.0, grid.centers * radius_m, radius_m]
    index = int(np.argmax(values))
    return float(values[index]), float(radii[index])


def threshold_event(grid, ambient, radius_data, property_set):
    def event(t, state):
        return cmax_and_location(t, state, grid, ambient, radius_data, property_set)[0] - THRESHOLD
    event.terminal = True
    event.direction = -1.0
    return event


def _output_times(end_time_s: float, requested: np.ndarray | None) -> np.ndarray:
    if requested is None:
        last_regular = math.floor(end_time_s / OUTPUT_INTERVAL_S) * OUTPUT_INTERVAL_S
        values = np.arange(0.0, last_regular + 0.5 * OUTPUT_INTERVAL_S, OUTPUT_INTERVAL_S)
    else:
        values = np.asarray(requested, dtype=float)
        if values.ndim != 1 or values.size == 0 or abs(values[0]) > 1.0e-12:
            raise ValueError("指定输出时间必须为以0开始的一维数组")
        values = values[values <= end_time_s + 1.0e-8]
    if abs(values[-1] - end_time_s) > 1.0e-7:
        values = np.r_[values, end_time_s]
    else:
        values[-1] = end_time_s
    return np.unique(values)


def _snapshot_times(end_time_s: float) -> np.ndarray:
    requested = np.unique(np.r_[0.0, ROOT_AUDIT_BASE_S, PROFILE_BASE_S, REPORT_HOURS * 3600.0])
    requested = requested[requested < end_time_s - 1.0e-7]
    return np.r_[requested, end_time_s]


def _reconstruct_outputs(dense, times, grid, ambient, radius_data, property_set):
    nt = len(times)
    nfix = len(FIXED_OUTPUT_RADII_M)
    t_fixed = np.full((nt, nfix), np.nan)
    c_fixed = np.full((nt, nfix), np.nan)
    t_surface = np.empty(nt)
    c_surface = np.empty(nt)
    t_axis = np.empty(nt)
    c_axis = np.empty(nt)
    inventory = np.empty(nt)
    boundary_rate = np.empty(nt)
    cmax = np.empty(nt)
    cmax_radius = np.empty(nt)
    radii = np.asarray(radius_data.radius(times))
    for start in range(0, nt, 64):
        stop = min(start + 64, nt)
        states = dense(times[start:stop]).T
        for local, (time_value, state, radius_m) in enumerate(zip(times[start:stop], states, radii[start:stop])):
            j = start + local
            n = grid.cells
            tc, cc = state[:n], state[n:]
            ts, cs, _, _ = surface_states(
                float(tc[-1]), float(cc[-1]), float(ambient.temperature(time_value)),
                float(ambient.concentration(time_value)), float(radius_m), grid.dxi,
                property_set,
            )
            t_surface[j], c_surface[j] = ts, cs
            t_axis[j], c_axis[j] = axis_value(tc, grid), axis_value(cc, grid)
            valid = FIXED_OUTPUT_RADII_M <= radius_m + 1.0e-12
            xi = FIXED_OUTPUT_RADII_M[valid] / radius_m
            t_fixed[j, valid] = reconstruct_profile(tc, ts, grid, xi)
            c_fixed[j, valid] = reconstruct_profile(cc, cs, grid, xi)
            inventory[j] = float(np.sum(cc * grid.volumes_xidxi))
            boundary_rate[j] = -HM * (cs - float(ambient.concentration(time_value))) / radius_m
            candidate_values = np.r_[c_axis[j], cc, cs]
            candidate_radii = np.r_[0.0, grid.centers * radius_m, radius_m]
            maximum_index = int(np.argmax(candidate_values))
            cmax[j] = float(candidate_values[maximum_index])
            cmax_radius[j] = float(candidate_radii[maximum_index])
    t_fixed[0, :] = T_INITIAL_C
    c_fixed[0, :] = C_INITIAL
    t_surface[0] = T_INITIAL_C
    c_surface[0] = C_INITIAL
    t_axis[0] = T_INITIAL_C
    c_axis[0] = C_INITIAL
    cmax[0] = C_INITIAL
    cmax_radius[0] = 0.0
    return t_fixed, c_fixed, t_surface, c_surface, t_axis, c_axis, inventory, boundary_rate, cmax, cmax_radius, radii


def solve_q4(
    cells: int = 2561,
    rtol: float = 1.0e-8,
    atol_temperature: float = 1.0e-10,
    atol_moisture: float = 1.0e-11,
    max_step_s: float = 60.0,
    property_set: PropertySet = "appendix4",
    geometry: GeometryMode = "moving",
    radius_interpolation: RadiusInterpolation = "pchip",
    integration_upper_s: float = INTEGRATION_UPPER_S,
    terminal_event: bool = True,
    output_times_s: np.ndarray | None = None,
    first_step_s: float | None = None,
) -> Q4Solution:
    ambient = load_ambient()
    radius_data = load_radius_data(mode=geometry, interpolation=radius_interpolation)
    grid = make_grid(cells)
    y0 = np.r_[np.full(cells, T_INITIAL_C), np.full(cells, C_INITIAL)]
    atol = np.r_[np.full(cells, atol_temperature), np.full(cells, atol_moisture)]
    started = time.perf_counter()
    integration_options = dict(
        method="BDF", rtol=rtol, atol=atol, max_step=max_step_s,
        jac_sparsity=jacobian_sparsity(cells), dense_output=True,
        events=threshold_event(grid, ambient, radius_data, property_set) if terminal_event else None,
    )
    if first_step_s is not None:
        integration_options["first_step"] = float(first_step_s)
    integration = solve_ivp(
        coupled_rhs(grid, ambient, radius_data, property_set),
        (0.0, float(integration_upper_s)), y0, **integration_options,
    )
    if not integration.success or integration.sol is None:
        raise RuntimeError(f"Q4 BDF积分失败于t={integration.t[-1]:.9g}s：{integration.message}")
    if terminal_event:
        if integration.t_events[0].size != 1:
            raise RuntimeError(f"在{integration_upper_s/3600.0:.2f}h内未检测到全域阈值事件")
        end_time_s = float(integration.t_events[0][0])
    else:
        end_time_s = float(integration_upper_s)
    times = _output_times(end_time_s, output_times_s)
    outputs = _reconstruct_outputs(
        integration.sol, times, grid, ambient, radius_data, property_set
    )
    snapshot_times = _snapshot_times(end_time_s)
    snapshot_states = integration.sol(snapshot_times).T
    terminal_state = integration.sol(end_time_s)
    radius_end = float(radius_data.radius(end_time_s))
    ts_end, cs_end, _, _ = surface_states(
        float(terminal_state[cells - 1]), float(terminal_state[-1]),
        float(ambient.temperature(end_time_s)), float(ambient.concentration(end_time_s)),
        radius_end, grid.dxi, property_set,
    )
    terminal_xi = np.linspace(0.0, 1.0, 10001)
    terminal_moisture = reconstruct_profile(terminal_state[cells:], cs_end, grid, terminal_xi)
    fine_index = int(np.argmax(terminal_moisture))
    end_max = float(terminal_moisture[fine_index])
    end_radius = float(terminal_xi[fine_index] * radius_end)
    elapsed = time.perf_counter() - started
    return Q4Solution(
        grid=grid, property_set=property_set, geometry=geometry,
        radius_interpolation=radius_interpolation, ambient=ambient, radius_data=radius_data,
        time_s=times, radius_m=outputs[10], temperature_fixed_c=outputs[0],
        moisture_fixed=outputs[1], temperature_surface_c=outputs[2],
        moisture_surface=outputs[3], temperature_axis_c=outputs[4],
        moisture_axis=outputs[5], moisture_inventory=outputs[6],
        moisture_boundary_rate=outputs[7], cmax=outputs[8], cmax_radius_m=outputs[9],
        ambient_temperature_c=np.asarray(ambient.temperature(times)),
        ambient_moisture=np.asarray(ambient.concentration(times)),
        snapshot_times_s=snapshot_times,
        temperature_cells_snapshot_c=snapshot_states[:, :cells],
        moisture_cells_snapshot=snapshot_states[:, cells:],
        terminal_xi=terminal_xi, terminal_moisture=terminal_moisture,
        end_time_s=end_time_s, end_max_moisture=end_max,
        end_max_radius_m=end_radius, nfev=int(integration.nfev),
        njev=int(integration.njev), nlu=int(integration.nlu), runtime_s=elapsed,
        tolerances={"rtol": float(rtol), "atol_temperature": float(atol_temperature),
                    "atol_moisture": float(atol_moisture), "max_step_s": float(max_step_s)},
    )


def table6(solution: Q4Solution) -> tuple[np.ndarray, list[list[float | None]]]:
    regular = REPORT_HOURS * 3600.0
    regular = regular[regular < solution.end_time_s - 1.0e-7]
    times = np.r_[regular, solution.end_time_s]
    rows: list[list[float | None]] = []
    for t in times:
        index = int(np.argmin(np.abs(solution.time_s - t)))
        if abs(solution.time_s[index] - t) > 1.0e-7:
            raise ValueError("表6请求时刻不在正式输出中")
        row: list[float | None] = []
        for r in TABLE_FIXED_RADII_M:
            if r > solution.radius_m[index] + 1.0e-12:
                row.append(None)
            else:
                column = int(round(r / 0.001))
                row.append(float(solution.moisture_fixed[index, column]))
        row.append(float(solution.moisture_surface[index]))
        rows.append(row)
    return times, rows


def surface_root_audit(solution: Q4Solution, points: int = 4097) -> dict[str, object]:
    records = []
    for t in np.unique(np.r_[ROOT_AUDIT_BASE_S[ROOT_AUDIT_BASE_S < solution.end_time_s], solution.end_time_s]):
        index = int(np.argmin(np.abs(solution.snapshot_times_s - t)))
        if abs(solution.snapshot_times_s[index] - t) > 1.0e-7:
            raise ValueError("根审计时刻缺少胞心快照")
        tc = solution.temperature_cells_snapshot_c[index]
        cc = solution.moisture_cells_snapshot[index]
        radius_m = float(solution.radius_data.radius(t))
        roots = scan_surface_roots(
            float(tc[-1]), float(cc[-1]), float(solution.ambient.temperature(t)),
            float(solution.ambient.concentration(t)), radius_m, solution.grid.dxi,
            solution.property_set, points,
        )
        adopted = surface_states(
            float(tc[-1]), float(cc[-1]), float(solution.ambient.temperature(t)),
            float(solution.ambient.concentration(t)), radius_m, solution.grid.dxi,
            solution.property_set,
        )[1]
        records.append({
            "time_s": float(t), "time_h": float(t / 3600.0), "root_count": len(roots),
            "roots": roots, "adopted_root": float(adopted),
            "adopted_is_first_from_cell": bool(roots and abs(adopted - roots[0]) < 1.0e-9),
        })
    adopted_values = np.array([r["adopted_root"] for r in records])
    return {
        "scan_points": points,
        "records": records,
        "all_single_root": bool(all(r["root_count"] == 1 for r in records)),
        "adopted_continuous_nonincreasing": bool(np.all(np.diff(adopted_values) <= 1.0e-8)),
    }


def save_solution(solution: Q4Solution, path: Path = OUTPUT_DIR / "q4_solution.npz") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        time_s=solution.time_s, radius_m=solution.radius_m,
        fixed_output_radii_m=FIXED_OUTPUT_RADII_M,
        temperature_fixed_c=solution.temperature_fixed_c,
        moisture_fixed=solution.moisture_fixed,
        temperature_surface_c=solution.temperature_surface_c,
        moisture_surface=solution.moisture_surface,
        temperature_axis_c=solution.temperature_axis_c,
        moisture_axis=solution.moisture_axis,
        ambient_temperature_c=solution.ambient_temperature_c,
        ambient_moisture=solution.ambient_moisture,
        moisture_inventory=solution.moisture_inventory,
        moisture_boundary_rate=solution.moisture_boundary_rate,
        cmax=solution.cmax, cmax_radius_m=solution.cmax_radius_m,
        snapshot_times_s=solution.snapshot_times_s,
        xi_cell_centers=solution.grid.centers,
        temperature_cells_snapshot_c=solution.temperature_cells_snapshot_c,
        moisture_cells_snapshot=solution.moisture_cells_snapshot,
        terminal_xi=solution.terminal_xi,
        terminal_moisture=solution.terminal_moisture,
        end_time_s=np.array(solution.end_time_s),
    )
    return path


def save_result_payload(
    time_s: np.ndarray,
    moisture_fixed: np.ndarray,
    moisture_surface: np.ndarray,
    path: Path = OUTPUT_DIR / "result4_payload.json",
) -> Path:
    """Prepare exact numeric payload for the template-preserving workbook builder."""
    regular = (
        (time_s >= OUTPUT_INTERVAL_S - 1.0e-8)
        & (np.abs(time_s / OUTPUT_INTERVAL_S - np.round(time_s / OUTPUT_INTERVAL_S)) < 1.0e-10)
    )
    times = time_s[regular]
    rows = []
    for t, fixed, surface in zip(times, moisture_fixed[regular], moisture_surface[regular]):
        rows.append([
            int(round(float(t))),
            *[None if not np.isfinite(value) else round(float(value), 4) for value in fixed],
            round(float(surface), 4),
        ])
    payload = {
        "headers": ["时间\\到药材中心的距离", *[float(v) for v in np.round(FIXED_OUTPUT_RADII_M * 100.0, 10)], "药材表面"],
        "rows": rows,
        "number_format": "0.0000",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def save_radius_audit(path: Path = OUTPUT_DIR / "q4_radius_audit.json") -> dict[str, object]:
    audit = radius_audit(load_radius_data())
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def save_root_audit(solution: Q4Solution, path: Path = OUTPUT_DIR / "q4_surface_root_audit.json") -> dict[str, object]:
    audit = surface_root_audit(solution)
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def save_run_summary(solution: Q4Solution, data_path: Path, root_audit: dict[str, object]) -> Path:
    times, rows = table6(solution)
    summary = {
        "model": "Q4 material-coordinate moving-radius coupled conservative radial finite volume + BDF",
        "property_set": solution.property_set,
        "geometry": solution.geometry,
        "radius_interpolation": solution.radius_interpolation,
        "grid_cells": solution.grid.cells,
        "method": "BDF", "tolerances": solution.tolerances,
        "runtime_s": solution.runtime_s, "nfev": solution.nfev,
        "njev": solution.njev, "nlu": solution.nlu,
        "input_files": {"attachment1": record_path(ATTACHMENT_1), "attachment2": record_path(ATTACHMENT_2), "template": record_path(OFFICIAL_TEMPLATE)},
        "initial_properties": initial_properties(solution.property_set),
        "initial_state": {"temperature_c": T_INITIAL_C, "moisture": C_INITIAL, "radius_m": FIXED_RADIUS_M},
        "end_time_s": solution.end_time_s,
        "end_time_h": solution.end_time_s / 3600.0,
        "end_time_d": solution.end_time_s / 86400.0,
        "end_radius_m": float(solution.radius_data.radius(solution.end_time_s)),
        "end_max_moisture": solution.end_max_moisture,
        "end_max_radius_m": solution.end_max_radius_m,
        "end_axis_moisture": float(solution.moisture_axis[-1]),
        "end_surface_moisture": float(solution.moisture_surface[-1]),
        "table6_times_s": times.tolist(),
        "table6_columns": ["0 cm", "0.5 cm", "1.0 cm", "1.5 cm", "surface"],
        "table6_moisture": rows,
        "formal_output": {"time_interval_s": 60, "last_regular_time_s": int(math.floor(solution.end_time_s / 60.0) * 60), "fixed_radius_cm": [0.0, 1.9, 0.1], "surface_column": True, "xlsx_decimals": 4},
        "surface_root_audit": {"all_single_root": root_audit["all_single_root"], "record_count": len(root_audit["records"])},
        "solution_data": record_path(data_path),
        "result_payload": record_path(OUTPUT_DIR / "result4_payload.json"),
        "main_checks_passed": bool(solution.end_max_moisture <= THRESHOLD + 5.0e-10 and np.all(np.isfinite(solution.terminal_moisture)) and np.min(solution.terminal_moisture) > 0.0),
    }
    path = OUTPUT_DIR / "q4_run_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def print_radius_audit(audit: dict[str, object]) -> None:
    print("附件2半径数据审计：")
    for h, r in zip(audit["audit_hours"], audit["audit_radius_m"]):
        print(f"R({h:g} h) = {100.0*r:.6f} cm")
    print(f"附件2末值 = {100.0*audit['attachment_last_radius_m']:.6f} cm")
    print(f"PCHIP节点最大误差 = {audit['node_max_abs_error_m']:.3e} m")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=int, default=2561)
    parser.add_argument("--rtol", type=float, default=1.0e-8)
    parser.add_argument("--atol-temperature", type=float, default=1.0e-10)
    parser.add_argument("--atol-moisture", type=float, default=1.0e-11)
    parser.add_argument("--max-step", type=float, default=60.0)
    parser.add_argument("--property-set", choices=("appendix3", "appendix4"), default="appendix4")
    parser.add_argument("--geometry", choices=("fixed", "moving"), default="moving")
    parser.add_argument("--radius-interpolation", choices=("pchip", "linear"), default="pchip")
    parser.add_argument("--first-step", type=float, default=None)
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    props = initial_properties(args.property_set)
    print(f"{args.property_set}初始物性：{json.dumps(props, ensure_ascii=False)}")
    audit = radius_audit(load_radius_data())
    if not args.no_save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "q4_radius_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print_radius_audit(audit)
    solution = solve_q4(
        cells=args.cells, rtol=args.rtol, atol_temperature=args.atol_temperature,
        atol_moisture=args.atol_moisture, max_step_s=args.max_step,
        property_set=args.property_set, geometry=args.geometry,
        radius_interpolation=args.radius_interpolation,
        first_step_s=args.first_step,
    )
    roots = surface_root_audit(solution)
    if not args.no_save:
        root_path = OUTPUT_DIR / "q4_surface_root_audit.json"
        root_path.write_text(json.dumps(roots, ensure_ascii=False, indent=2), encoding="utf-8")
    if not roots["all_single_root"]:
        raise RuntimeError("正式根审计发现多个离散根，已停止冻结；请检查q4_surface_root_audit.json")
    if not args.no_save:
        data_path = save_solution(solution)
        payload_path = save_result_payload(
            solution.time_s, solution.moisture_fixed, solution.moisture_surface
        )
        summary_path = save_run_summary(solution, data_path, roots)
        print(f"未舍入结果：{data_path}")
        print(f"工作簿数值载荷：{payload_path}")
        print(f"运行摘要：{summary_path}")
    print(f"Q4完成：N={args.cells}, t_end={solution.end_time_s:.9f}s = {solution.end_time_s/3600.0:.9f}h")
    print(f"R_end={100.0*solution.radius_data.radius(solution.end_time_s):.9f}cm, Cmax={solution.end_max_moisture:.12f}, r_argmax={100.0*solution.end_max_radius_m:.9f}cm, C_surface={solution.moisture_surface[-1]:.12f}")
    t6, v6 = table6(solution)
    print("表6时刻(h)：", t6 / 3600.0)
    print(json.dumps(v6, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
