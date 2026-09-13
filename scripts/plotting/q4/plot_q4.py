# 文件名：plot_q4.py
# 用途：第四问移动边界、径向水分剖面、时空场及效应对照图绘图程序。

"""由正式 Q4 数值结果独立重绘全部论文图件。"""

from __future__ import annotations

import json
from pathlib import Path
import os, sys
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2]/".mplconfig"))
import matplotlib.pyplot as plt
import numpy as np
STYLE_DIR = Path(__file__).resolve().parents[3]/".agents/skills/mathmodel-figure/code/style"
sys.path.insert(0, str(STYLE_DIR))
try:
    import seaborn
except ModuleNotFoundError:
    import types
    seaborn = types.ModuleType("seaborn")
    seaborn.set_theme = lambda *a, **k: None
    sys.modules["seaborn"] = seaborn
from plot_style import COLOR_MAIN, COLOR_MAIN_LIGHT, COLOR_BASELINE, COLOR_BASELINE_DARK, ACCENT_ORANGE, FIG_FULL, FIG_TALL, FS_ANNOT, save_fig, style_axes, tint, add_panel_label


SCRIPT_DIR = Path(__file__).resolve().parent
IN_REPOSITORY_LAYOUT = (
    SCRIPT_DIR.name.casefold() == "q4"
    and SCRIPT_DIR.parent.name.casefold() == "plotting"
    and SCRIPT_DIR.parent.parent.name.casefold() == "scripts"
)
if IN_REPOSITORY_LAYOUT:
    ROOT = SCRIPT_DIR.parents[2]
    DATA_PATH = ROOT / "results" / "q4" / "q4_solution.npz"
    EFFECT_PATH = ROOT / "results" / "q4" / "q4_effect_decomposition.json"
    FIGURE_DIR = ROOT / "figures" / "final" / "q4"
    ATTACHMENT_2 = ROOT / "data" / "raw" / "problems" / "A题" / "附件" / "附件2.xlsx"
else:
    ROOT = SCRIPT_DIR.parent
    DATA_PATH = SCRIPT_DIR / "q4_solution.npz"
    EFFECT_PATH = SCRIPT_DIR / "q4_effect_decomposition.json"
    FIGURE_DIR = SCRIPT_DIR / "figures"
    ATTACHMENT_2 = ROOT / "CUMCM2026Problems" / "A题" / "附件" / "附件2.xlsx"


def configure_style() -> None:
    # 全文统一采用项目共享 Nature 风格模块。
    plt.rcParams["axes.unicode_minus"] = False



def save_both(figure: plt.Figure, stem: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    base = FIGURE_DIR / stem
    save_fig(figure, str(base.with_suffix(".png")), close=False, dpi=300)
    figure.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.1)
    figure.savefig(base.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.1)
    plt.close(figure)


def load_radius_input(data):
    """Use the formal PCHIP trajectory saved with the solved state."""
    return np.asarray(data["time_s"], dtype=float), np.asarray(data["radius_m"], dtype=float) * 100.0


def plot_radius(data) -> None:
    time_input, radius_input_cm = load_radius_input(data)
    t_end = float(data["end_time_s"])
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    ax.plot(time_input / 3600.0, radius_input_cm, color=COLOR_MAIN, lw=1.8, label="Formal radius trajectory")
    r_end = float(np.interp(t_end, time_input, radius_input_cm))
    ax.scatter([t_end / 3600.0], [r_end], color=COLOR_BASELINE_DARK, s=36, zorder=4, label="Termination time")
    ax.axvline(t_end / 3600.0, color=COLOR_BASELINE_DARK, lw=0.8, ls="--")
    ax.set(xlabel="Time (h)", ylabel="Radius (cm)", title="Radius contraction over time")
    style_axes(ax, grid="y")
    ax.legend(frameon=False)
    save_both(fig, "q4_radius_time")


def plot_profiles(data) -> None:
    requested_hours = [6, 12, 18, 30, 42]
    snapshot_times = data["snapshot_times_s"]
    end_time = float(data["end_time_s"])
    times = [h * 3600.0 for h in requested_hours if h * 3600.0 < end_time] + [end_time]
    colors = plt.cm.viridis(np.linspace(0.08, 0.92, len(times)))
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    xi = data["xi_cell_centers"]
    for color, t in zip(colors, times):
        index = int(np.argmin(np.abs(snapshot_times - t)))
        radius_cm = float(np.interp(t, data["time_s"], data["radius_m"])) * 100.0
        cell = data["moisture_cells_snapshot"][index]
        axis = float(np.interp(t, data["time_s"], data["moisture_axis"]))
        surface = float(np.interp(t, data["time_s"], data["moisture_surface"]))
        r = np.r_[0.0, xi * radius_cm, radius_cm]
        c = np.r_[axis, cell, surface]
        label = "Termination" if abs(t - end_time) < 1.0e-6 else f"{t/3600.0:g} h"
        ax.plot(r, c, lw=1.6, color=color, label=label)
    ax.axhline(0.15, color=COLOR_BASELINE_DARK, lw=0.9, ls="--", label="Threshold 0.15")
    ax.set(xlabel="Distance from axis (cm)", ylabel="Moisture concentration (kg/kg)", title="Radial moisture profiles with moving boundary")
    style_axes(ax, grid="y")
    ax.legend(frameon=False, ncol=2)
    save_both(fig, "q4_moving_profiles")


def plot_spacetime(data) -> None:
    time_h = data["time_s"] / 3600.0
    fixed_cm = data["fixed_output_radii_m"] * 100.0
    field = data["moisture_fixed"]
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    mesh = ax.pcolormesh(fixed_cm, time_h, field, shading="nearest", cmap="Blues_r", rasterized=True)
    ax.plot(data["radius_m"] * 100.0, time_h, color=COLOR_BASELINE_DARK, lw=1.5, label="Moving surface")
    ax.set(xlabel="Distance from axis (cm)", ylabel="Time (h)", title="Moisture spatiotemporal field")
    ax.set_xlim(0.0, 2.0)
    ax.set_ylim(0.0, time_h[-1])
    colorbar = fig.colorbar(mesh, ax=ax, pad=0.02)
    colorbar.set_label("Moisture concentration (kg/kg)")
    ax.legend(frameon=False, loc="lower right")
    save_both(fig, "q4_moisture_spacetime")


def plot_effects() -> None:
    effect = json.loads(EFFECT_PATH.read_text(encoding="utf-8"))
    labels = ["C\nAppendix 3 + fixed", "D\nAppendix 3 + moving", "A\nAppendix 4 + fixed", "B\nAppendix 4 + moving"]
    values = [effect["cases"][key]["end_time_h"] for key in ("C", "D", "A", "B")]
    colors = ["#5B9BD5", "#70AD47", "#FFC000", "#ED7D31"]
    fig, ax = plt.subplots(figsize=(6.8, 4.1))
    bars = ax.bar(labels, values, color=colors, width=0.62)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 2.0, f"{value:.2f}", ha="center", va="bottom")
    ax.set(ylabel="Termination time (h)", title="Material and geometry scenario comparison")
    ax.set_ylim(0.0, max(values) * 1.13)
    ax.grid(True, axis="y", alpha=0.65)
    save_both(fig, "q4_effect_decomposition")


def main() -> None:
    configure_style()
    with np.load(DATA_PATH) as data:
        plot_radius(data)
        plot_profiles(data)
        plot_spacetime(data)
    plot_effects()
    print(f"图件已输出到：{FIGURE_DIR}")


if __name__ == "__main__":
    main()
