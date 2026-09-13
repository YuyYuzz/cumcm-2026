# 文件名：plot_q3.py
# 用途：第三问全域最大水分浓度、时空场、径向剖面及边界敏感性绘图程序。

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_hex, to_rgb


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_PATH = SCRIPT_DIR / "q3_solution.npz"
VALIDATION_PATH = SCRIPT_DIR / "q3_validation.json"
OUTPUT_DIR = SCRIPT_DIR / "figures"

COLOR_MAIN = "#1A6FC4"
COLOR_BASELINE = "#767676"
ACCENT_ORANGE = "#E28E2C"
NEUTRAL_LIGHT = "#D8D8D8"
NEUTRAL_DARK = "#606060"
COLOR_INK = "#333333"
FIG_FULL = (6.3, 4.0)
FIG_TALL = (6.3, 5.5)
FS_TITLE = 10.5
FS_LABEL = 9.5
FS_TICK = 8.5
FS_LEGEND = 8.5
FS_ANNOT = 8.0
FS_PANEL = 12.0
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


def tint(color: str, amount: float = 0.35) -> str:
    red, green, blue = to_rgb(color)
    return to_hex(
        (
            red + (1.0 - red) * amount,
            green + (1.0 - green) * amount,
            blue + (1.0 - blue) * amount,
        )
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


def add_panel_label(ax, label: str) -> None:
    ax.text(
        -0.11,
        1.02,
        label,
        transform=ax.transAxes,
        fontsize=FS_PANEL,
        fontweight="bold",
        color=COLOR_INK,
        va="bottom",
        ha="left",
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    """Overwrite only this program's stable figure names."""
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


def load_inputs() -> tuple[dict[str, np.ndarray | float], dict[str, object]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            "未找到q3_solution.npz，请先运行q3_main.py生成正式数值结果。"
        )
    if not VALIDATION_PATH.exists():
        raise FileNotFoundError(
            "未找到q3_validation.json，请先运行q3_validation.py生成验证结果。"
        )
    with np.load(DATA_PATH) as archive:
        data: dict[str, np.ndarray | float] = {
            name: np.array(archive[name], copy=True) for name in archive.files
        }
    validation = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))
    return data, validation


def validate_inputs(
    data: dict[str, np.ndarray | float], validation: dict[str, object]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float]:
    time_h = np.asarray(data["time_s"], dtype=float) / 3600.0
    radius_cm = np.asarray(data["output_radii_m"], dtype=float) * 100.0
    moisture = np.asarray(data["moisture_output"], dtype=float)
    maximum_moisture = np.asarray(data["cmax"], dtype=float)
    terminal_moisture = np.asarray(data["terminal_moisture"], dtype=float)
    end_time_h = float(np.asarray(data["end_time_s"])) / 3600.0
    threshold = float(validation["formal"]["end_max_moisture"])

    if moisture.shape != (time_h.size, radius_cm.size):
        raise ValueError(f"Q3水分数组形状异常：{moisture.shape}")
    if radius_cm.size != 21 or not np.allclose(
        radius_cm, np.arange(21, dtype=float) / 10.0, rtol=0.0, atol=1.0e-12
    ):
        raise ValueError("Q3输出半径必须为0至2.0 cm，步长0.1 cm")
    if not (
        np.all(np.isfinite(moisture))
        and np.all(np.isfinite(maximum_moisture))
        and np.all(np.diff(time_h) > 0.0)
        and np.all(np.diff(radius_cm) > 0.0)
    ):
        raise ValueError("Q3正式结果含非有限数值或非递增坐标")
    if not np.allclose(moisture[0], 2.55):
        raise ValueError("Q3初始水分状态不一致")
    if not (
        np.isclose(maximum_moisture[-1], threshold)
        and np.isclose(moisture[-1, 0], threshold)
        and np.max(terminal_moisture) <= threshold + 1.0e-9
    ):
        raise ValueError("Q3终止状态与阈值不一致")
    return time_h, radius_cm, moisture, maximum_moisture, end_time_h, threshold


def draw_criterion(
    ax,
    time_h: np.ndarray,
    maximum_moisture: np.ndarray,
    end_time_h: float,
    threshold: float,
) -> None:
    ax.plot(time_h, maximum_moisture, color=COLOR_MAIN)
    ax.axhline(threshold, color=COLOR_BASELINE, ls="--", lw=0.8)
    ax.scatter([end_time_h], [threshold], color=ACCENT_ORANGE, zorder=4)
    ax.annotate(
        f"{end_time_h:.2f} h",
        (end_time_h, threshold),
        xytext=(-5, 20),
        textcoords="offset points",
        ha="right",
        fontsize=FS_ANNOT,
        arrowprops={"arrowstyle": "-", "color": ACCENT_ORANGE},
    )
    ax.text(
        0.97,
        0.30,
        "Threshold = 0.15",
        transform=ax.transAxes,
        ha="right",
        fontsize=FS_ANNOT,
        color=COLOR_BASELINE,
    )
    ax.set(
        xlabel="Time (h)",
        ylabel="Maximum moisture (kg/kg)",
        xlim=(0.0, 60.0),
        ylim=(0.0, 2.7),
        title="Termination criterion",
    )
    style_axes(ax, grid="y")


def draw_field(
    ax,
    time_h: np.ndarray,
    radius_cm: np.ndarray,
    moisture: np.ndarray,
    end_time_h: float,
    threshold: float,
) -> None:
    color_map = LinearSegmentedColormap.from_list(
        "moisture", [COLOR_MAIN, tint(COLOR_MAIN, 0.92)]
    )
    normalization = Normalize(float(moisture.min()), float(moisture.max()))
    mesh = ax.pcolormesh(
        time_h,
        radius_cm,
        moisture.T,
        shading="auto",
        cmap=color_map,
        norm=normalization,
        rasterized=True,
    )
    ax.contour(
        time_h,
        radius_cm,
        moisture.T,
        levels=[threshold],
        colors=[ACCENT_ORANGE],
        linewidths=0.9,
    )
    colorbar = ax.figure.colorbar(mesh, ax=ax, pad=0.03, fraction=0.045)
    colorbar.set_label("Moisture (kg/kg)")
    ax.set(
        xlabel="Time (h)",
        ylabel="Radius (cm)",
        xlim=(0.0, end_time_h),
        ylim=(0.0, 2.0),
        title="Moisture field",
    )
    ax.text(
        0.97,
        0.10,
        "Orange: C = 0.15",
        transform=ax.transAxes,
        ha="right",
        fontsize=FS_ANNOT,
        color=ACCENT_ORANGE,
    )
    style_axes(ax, grid=None)


def draw_profiles(
    ax,
    time_h: np.ndarray,
    radius_cm: np.ndarray,
    moisture: np.ndarray,
    end_time_h: float,
    threshold: float,
) -> None:
    selected_hours = (6.0, 18.0, 30.0, 42.0)
    indices = [
        int(np.argmin(np.abs(time_h - value))) for value in selected_hours
    ] + [time_h.size - 1]
    labels = [f"{value:g} h" for value in selected_hours] + [f"{end_time_h:.2f} h"]
    line_styles = ("--", "-.", ":", "--", "-")
    for index, (time_index, label) in enumerate(zip(indices, labels)):
        ax.plot(
            radius_cm,
            moisture[time_index],
            color=tint(COLOR_MAIN, 0.65 * (1.0 - index / 4.0)),
            ls=line_styles[index],
            label=label,
        )
    ax.axhline(threshold, color=COLOR_BASELINE, ls="--", lw=0.8)
    ax.set(
        xlabel="Radius (cm)",
        ylabel="Moisture (kg/kg)",
        xlim=(0.0, 2.0),
        ylim=(0.0, 1.1),
        title="Radial profiles",
    )
    ax.legend(frameon=False, fontsize=FS_ANNOT, loc="upper right")
    style_axes(ax, grid="y")


def draw_sensitivity(ax, validation: dict[str, object]) -> None:
    formal = validation["formal"]
    high_humidity = validation["cases"]["post_Ca_0.07"]
    ambient = np.array(
        [0.04986, high_humidity["options"]["post_moisture"]], dtype=float
    )
    end_times_h = np.array(
        [formal["end_time_h"], high_humidity["end_time_h"]], dtype=float
    )
    ax.plot(ambient, end_times_h, color=COLOR_MAIN, lw=1.2)
    ax.scatter(ambient, end_times_h, color=COLOR_MAIN, zorder=3)
    for moisture, end_time_h in zip(ambient, end_times_h):
        ax.annotate(
            f"{end_time_h:.2f} h",
            (moisture, end_time_h),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=FS_ANNOT,
        )
    padding = max(0.2, 0.12 * float(np.ptp(end_times_h)))
    ax.set(
        xlabel="Ambient moisture after 4 h (kg/kg)",
        ylabel="Termination time (h)",
        xlim=(0.047, 0.073),
        ylim=(float(end_times_h.min() - padding), float(end_times_h.max() + padding)),
        title="Boundary-condition sensitivity",
    )
    ax.set_xticks(ambient, ["0.04986", "0.070"])
    style_axes(ax, grid="y")


def main() -> None:
    data, validation = load_inputs()
    time_h, radius_cm, moisture, maximum_moisture, end_time_h, threshold = (
        validate_inputs(data, validation)
    )

    drawers = (
        lambda ax: draw_criterion(
            ax, time_h, maximum_moisture, end_time_h, threshold
        ),
        lambda ax: draw_field(
            ax, time_h, radius_cm, moisture, end_time_h, threshold
        ),
        lambda ax: draw_profiles(
            ax, time_h, radius_cm, moisture, end_time_h, threshold
        ),
        lambda ax: draw_sensitivity(ax, validation),
    )
    names = (
        "q3_cmax_threshold",
        "q3_spatiotemporal_field",
        "q3_moisture_profiles",
        "q3_ambient_sensitivity",
    )

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(FIG_FULL[0] * 2.0, FIG_TALL[1] * 1.35),
        layout="constrained",
    )
    for tag, ax, draw in zip("abcd", axes.flat, drawers):
        draw(ax)
        add_panel_label(ax, tag)
    save_figure(fig, "q3_summary")

    for name, draw in zip(names, drawers):
        fig, ax = plt.subplots(figsize=FIG_FULL, layout="constrained")
        draw(ax)
        save_figure(fig, name)

    print(f"数据形状：{moisture.shape}")
    print(f"终止时间：{end_time_h:.8f} h")
    print(f"图件目录：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
