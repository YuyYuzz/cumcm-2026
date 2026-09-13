# 文件名：plot_q4.py
# 用途：第四问移动边界、径向水分剖面、时空场及效应对照图绘图程序。

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_PATH = SCRIPT_DIR / "q4_solution.npz"
EFFECT_PATH = SCRIPT_DIR / "q4_effect_decomposition.json"
OUTPUT_DIR = SCRIPT_DIR / "figures"

COLOR_MAIN = "#1A6FC4"
COLOR_BASELINE_DARK = "#4D4D4D"
NEUTRAL_LIGHT = "#D8D8D8"
NEUTRAL_DARK = "#606060"
COLOR_INK = "#333333"
FS_TITLE = 10.5
FS_LABEL = 9.5
FS_TICK = 8.5
FS_LEGEND = 8.5
AX_LINEW = 0.7
TICK_LEN = 3.2
TICK_PAD = 3.0
GRID_LINESTYLE = (0, (4, 3))


def font_stack() -> list[str]:
    """Choose installed Latin and Chinese fonts with a portable fallback."""
    installed = {item.name for item in font_manager.fontManager.ttflist}
    stack = [
        name
        for name in ("Arial", "Helvetica", "Liberation Sans")
        if name in installed
    ]
    chinese = next(
        (
            name
            for name in (
                "Microsoft YaHei",
                "SimHei",
                "Noto Sans CJK SC",
                "WenQuanYi Micro Hei",
            )
            if name in installed
        ),
        None,
    )
    if chinese is None:
        warnings.warn("未找到中文字体，图中的中文可能无法正确显示。")
    return stack + ["DejaVu Sans"] + ([chinese] if chinese else [])


plt.rcParams.update(
    {
        "font.family": font_stack(),
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "figure.dpi": 100,
        "savefig.dpi": 300,
        "savefig.facecolor": "white",
        "font.size": FS_LABEL,
        "axes.titlesize": FS_TITLE,
        "axes.titleweight": "bold",
        "axes.titlecolor": COLOR_INK,
        "axes.titlepad": 10,
        "axes.labelsize": FS_LABEL,
        "axes.linewidth": AX_LINEW,
        "axes.axisbelow": True,
        "axes.edgecolor": NEUTRAL_DARK,
        "axes.labelcolor": COLOR_INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.labelsize": FS_TICK,
        "ytick.labelsize": FS_TICK,
        "xtick.color": COLOR_INK,
        "ytick.color": COLOR_INK,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": TICK_LEN,
        "ytick.major.size": TICK_LEN,
        "legend.fontsize": FS_LEGEND,
        "legend.frameon": False,
        "legend.handlelength": 1.8,
        "legend.borderaxespad": 0.4,
        "figure.frameon": False,
        "lines.markersize": 4.5,
        "patch.linewidth": 0.8,
    }
)


def style_axes(ax, grid: str | None = "y"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(AX_LINEW)
        ax.spines[side].set_color(NEUTRAL_DARK)
    ax.tick_params(
        axis="both",
        which="both",
        direction="out",
        length=TICK_LEN,
        width=AX_LINEW,
        color=NEUTRAL_DARK,
        colors=COLOR_INK,
        labelsize=FS_TICK,
        pad=TICK_PAD,
    )
    for axis in (ax.xaxis, ax.yaxis):
        axis.label.set_fontsize(FS_LABEL)
        axis.label.set_color(COLOR_INK)
    if grid in ("x", "y", "both"):
        ax.grid(
            axis=grid,
            color=NEUTRAL_LIGHT,
            linewidth=0.6,
            linestyle=GRID_LINESTYLE,
        )
        ax.set_axisbelow(True)
    return ax


def save_figure(fig: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUTPUT_DIR / stem
    fig.savefig(
        base.with_suffix(".png"),
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.1,
        pil_kwargs={"optimize": True},
    )
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.1)
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)


def validate_solution(data) -> None:
    required = {
        "time_s",
        "radius_m",
        "end_time_s",
        "snapshot_times_s",
        "xi_cell_centers",
        "moisture_cells_snapshot",
        "moisture_axis",
        "moisture_surface",
        "fixed_output_radii_m",
        "moisture_fixed",
    }
    missing = sorted(required.difference(data.files))
    if missing:
        raise ValueError(f"q4_solution.npz缺少字段：{missing}")

    time_s = np.asarray(data["time_s"], dtype=float)
    radius_m = np.asarray(data["radius_m"], dtype=float)
    moisture_axis = np.asarray(data["moisture_axis"], dtype=float)
    moisture_surface = np.asarray(data["moisture_surface"], dtype=float)
    fixed_radii_m = np.asarray(data["fixed_output_radii_m"], dtype=float)
    moisture_fixed = np.asarray(data["moisture_fixed"], dtype=float)
    if not (
        time_s.ndim == radius_m.ndim == moisture_axis.ndim == moisture_surface.ndim == 1
        and time_s.size
        == radius_m.size
        == moisture_axis.size
        == moisture_surface.size
    ):
        raise ValueError("Q4时间、半径、轴线与表面数组形状不一致")
    if moisture_fixed.shape != (time_s.size, fixed_radii_m.size):
        raise ValueError("Q4固定位置水分数组形状不一致")
    if not (
        np.all(np.isfinite(time_s))
        and np.all(np.isfinite(radius_m))
        and np.all(np.isfinite(moisture_axis))
        and np.all(np.isfinite(moisture_surface))
        and np.all(np.diff(time_s) > 0.0)
        and np.all(np.diff(fixed_radii_m) > 0.0)
    ):
        raise ValueError("Q4正式结果含非有限坐标或非递增坐标")
    if not np.isclose(float(data["end_time_s"]), time_s[-1]):
        raise ValueError("Q4连续终点与正式时间数组终点不一致")


def plot_radius(data) -> None:
    time_s = np.asarray(data["time_s"], dtype=float)
    radius_cm = np.asarray(data["radius_m"], dtype=float) * 100.0
    end_time_s = float(data["end_time_s"])
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    ax.plot(
        time_s / 3600.0,
        radius_cm,
        color=COLOR_MAIN,
        lw=1.8,
        label="Formal radius trajectory",
    )
    end_radius_cm = float(np.interp(end_time_s, time_s, radius_cm))
    ax.scatter(
        [end_time_s / 3600.0],
        [end_radius_cm],
        color=COLOR_BASELINE_DARK,
        s=36,
        zorder=4,
        label="Termination time",
    )
    ax.axvline(
        end_time_s / 3600.0, color=COLOR_BASELINE_DARK, lw=0.8, ls="--"
    )
    ax.set(
        xlabel="Time (h)",
        ylabel="Radius (cm)",
        title="Radius contraction over time",
    )
    style_axes(ax, grid="y")
    ax.legend(frameon=False)
    save_figure(fig, "q4_radius_time")


def plot_profiles(data) -> None:
    requested_hours = (6.0, 12.0, 18.0, 30.0, 42.0)
    solution_time_s = np.asarray(data["time_s"], dtype=float)
    snapshot_times_s = np.asarray(data["snapshot_times_s"], dtype=float)
    end_time_s = float(data["end_time_s"])
    times_s = [
        hour * 3600.0
        for hour in requested_hours
        if hour * 3600.0 < end_time_s
    ] + [end_time_s]
    colors = plt.cm.viridis(np.linspace(0.08, 0.92, len(times_s)))
    xi = np.asarray(data["xi_cell_centers"], dtype=float)
    moisture_cells = np.asarray(data["moisture_cells_snapshot"], dtype=float)
    moisture_axis = np.asarray(data["moisture_axis"], dtype=float)
    moisture_surface = np.asarray(data["moisture_surface"], dtype=float)
    radius_m = np.asarray(data["radius_m"], dtype=float)

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for color, time_s in zip(colors, times_s):
        snapshot_index = int(np.argmin(np.abs(snapshot_times_s - time_s)))
        if abs(snapshot_times_s[snapshot_index] - time_s) > 1.0e-6:
            raise ValueError(f"Q4快照中缺少时刻：{time_s} s")
        radius_cm = float(np.interp(time_s, solution_time_s, radius_m)) * 100.0
        axis_value = float(np.interp(time_s, solution_time_s, moisture_axis))
        surface_value = float(np.interp(time_s, solution_time_s, moisture_surface))
        physical_radius_cm = np.r_[0.0, xi * radius_cm, radius_cm]
        moisture_profile = np.r_[
            axis_value, moisture_cells[snapshot_index], surface_value
        ]
        label = (
            "Termination"
            if abs(time_s - end_time_s) < 1.0e-6
            else f"{time_s / 3600.0:g} h"
        )
        ax.plot(
            physical_radius_cm,
            moisture_profile,
            lw=1.6,
            color=color,
            label=label,
        )
    ax.axhline(
        0.15,
        color=COLOR_BASELINE_DARK,
        lw=0.9,
        ls="--",
        label="Threshold 0.15",
    )
    ax.set(
        xlabel="Distance from axis (cm)",
        ylabel="Moisture concentration (kg/kg)",
        title="Radial moisture profiles with moving boundary",
    )
    style_axes(ax, grid="y")
    ax.legend(frameon=False, ncol=2)
    save_figure(fig, "q4_moving_profiles")


def plot_spacetime(data) -> None:
    time_h = np.asarray(data["time_s"], dtype=float) / 3600.0
    fixed_cm = np.asarray(data["fixed_output_radii_m"], dtype=float) * 100.0
    moisture_fixed = np.asarray(data["moisture_fixed"], dtype=float)
    radius_cm = np.asarray(data["radius_m"], dtype=float) * 100.0
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    mesh = ax.pcolormesh(
        fixed_cm,
        time_h,
        moisture_fixed,
        shading="nearest",
        cmap="Blues_r",
        rasterized=True,
    )
    ax.plot(radius_cm, time_h, color=COLOR_BASELINE_DARK, lw=1.5, label="Moving surface")
    ax.set(
        xlabel="Distance from axis (cm)",
        ylabel="Time (h)",
        title="Moisture spatiotemporal field",
    )
    ax.set_xlim(0.0, 2.0)
    ax.set_ylim(0.0, time_h[-1])
    colorbar = fig.colorbar(mesh, ax=ax, pad=0.02)
    colorbar.set_label("Moisture concentration (kg/kg)")
    ax.legend(frameon=False, loc="lower right")
    save_figure(fig, "q4_moisture_spacetime")


def plot_effects() -> None:
    if not EFFECT_PATH.exists():
        raise FileNotFoundError(
            "未找到q4_effect_decomposition.json，请先运行"
            "diagnostics/q4_effect_decomposition.py生成四工况结果。"
        )
    effect = json.loads(EFFECT_PATH.read_text(encoding="utf-8"))
    labels = (
        "C\nAppendix 3 + fixed",
        "D\nAppendix 3 + moving",
        "A\nAppendix 4 + fixed",
        "B\nAppendix 4 + moving",
    )
    values = [effect["cases"][key]["end_time_h"] for key in ("C", "D", "A", "B")]
    colors = ("#5B9BD5", "#70AD47", "#FFC000", "#ED7D31")
    fig, ax = plt.subplots(figsize=(6.8, 4.1))
    bars = ax.bar(labels, values, color=colors, width=0.62)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + 2.0,
            f"{value:.2f}",
            ha="center",
            va="bottom",
        )
    ax.set(
        ylabel="Termination time (h)",
        title="Material and geometry scenario comparison",
    )
    ax.set_ylim(0.0, max(values) * 1.13)
    ax.grid(True, axis="y", alpha=0.65)
    save_figure(fig, "q4_effect_decomposition")


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            "未找到q4_solution.npz，请先运行q4_main.py生成正式数值结果。"
        )
    with np.load(DATA_PATH) as data:
        validate_solution(data)
        plot_radius(data)
        plot_profiles(data)
        plot_spacetime(data)
    plot_effects()
    print(f"图件目录：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
