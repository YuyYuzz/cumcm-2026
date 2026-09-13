# 文件名：plot_q2.py
# 用途：第二问温度、水分及扩散系数结果图绘图程序。

from __future__ import annotations

import posixpath
import re
import warnings
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, to_hex, to_rgb


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
INPUT_XLSX = PACKAGE_ROOT / "results" / "result2.xlsx"
OUTPUT_DIR = SCRIPT_DIR / "figures"

COLOR_MAIN = "#1A6FC4"
ACCENT_ORANGE = "#E28E2C"
COLOR_BASELINE_DARK = "#4D4D4D"
NEUTRAL_LIGHT = "#D8D8D8"
NEUTRAL_DARK = "#606060"
COLOR_INK = "#333333"
IDENTITY_PALETTE = (
    COLOR_MAIN,
    ACCENT_ORANGE,
    "#7B5FD6",
    "#33B5A5",
    "#D9544D",
    "#B89BD9",
)
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

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


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


def identity_color(index: int) -> str:
    return IDENTITY_PALETTE[index % len(IDENTITY_PALETTE)]


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


def column_index(cell_reference: str) -> int:
    letters = re.match(r"[A-Z]+", cell_reference)
    if letters is None:
        raise ValueError(f"Invalid cell reference: {cell_reference}")
    result = 0
    for char in letters.group(0):
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def worksheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = None
    for sheet in workbook_root.findall(f".//{{{MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            relationship_id = sheet.attrib.get(f"{{{DOC_REL_NS}}}id")
            break
    if relationship_id is None:
        raise ValueError(f"工作簿中缺少工作表：{sheet_name}")

    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in rels_root.findall(f"{{{PKG_REL_NS}}}Relationship"):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib["Target"]
            if target.startswith("/"):
                return target.lstrip("/")
            return posixpath.normpath(posixpath.join("xl", target))
    raise ValueError(f"工作表缺少关系记录：{sheet_name}")


def read_worksheet(sheet_name: str) -> list[list[object | None]]:
    """Read worksheet values without adding an Excel-library dependency."""
    with zipfile.ZipFile(INPUT_XLSX) as archive:
        shared_strings = read_shared_strings(archive)
        root = ET.fromstring(archive.read(worksheet_path(archive, sheet_name)))

    parsed_rows: list[tuple[int, dict[int, object]]] = []
    maximum_column = 0
    for row in root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row"):
        row_index = int(row.attrib["r"]) - 1
        values: dict[int, object] = {}
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            col_index = column_index(cell.attrib["r"])
            cell_type = cell.attrib.get("t")
            value_node = cell.find(f"{{{MAIN_NS}}}v")
            if cell_type == "inlineStr":
                value = "".join(
                    node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t")
                )
            elif value_node is None:
                value = None
            elif cell_type == "s":
                value = shared_strings[int(value_node.text)]
            elif cell_type == "b":
                value = value_node.text == "1"
            elif cell_type in ("str", "e"):
                value = value_node.text
            else:
                value = float(value_node.text)
            values[col_index] = value
            maximum_column = max(maximum_column, col_index + 1)
        parsed_rows.append((row_index, values))

    if not parsed_rows:
        raise ValueError(f"工作表为空：{sheet_name}")
    maximum_row = max(row_index for row_index, _ in parsed_rows) + 1
    matrix: list[list[object | None]] = [
        [None] * maximum_column for _ in range(maximum_row)
    ]
    for row_index, values in parsed_rows:
        for col_index, value in values.items():
            matrix[row_index][col_index] = value
    return matrix


def load_field(sheet_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows = read_worksheet(sheet_name)
    time_s = np.asarray([row[0] for row in rows[1:]], dtype=float)
    radius_cm = np.asarray(rows[0][1:22], dtype=float)
    values = np.asarray([row[1:22] for row in rows[1:]], dtype=float)

    expected_time = np.arange(1.0, 10801.0)
    expected_radius = np.arange(21, dtype=float) / 10.0
    if not np.array_equal(time_s, expected_time):
        raise ValueError(f"{sheet_name}的时间列必须为1至10800 s")
    if not np.allclose(radius_cm, expected_radius, rtol=0.0, atol=1.0e-12):
        raise ValueError(f"{sheet_name}的半径表头必须为0至2.0 cm，步长0.1 cm")
    if values.shape != (10800, 21):
        raise ValueError(f"{sheet_name}数据形状异常：{values.shape}")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{sheet_name}中存在非有限数值")
    return time_s, radius_cm, values


def load_fields() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    time_t, radius_t, temperature = load_field("温度")
    time_c, radius_c, moisture = load_field("水分浓度")
    if not (
        np.array_equal(time_t, time_c)
        and np.array_equal(radius_t, radius_c)
    ):
        raise ValueError("温度与水分工作表的时间列或半径表头不一致")
    return time_t, radius_t, temperature, moisture


def save_all(fig: plt.Figure, stem: str) -> None:
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


def plot_spatiotemporal(
    time_s: np.ndarray,
    radius_cm: np.ndarray,
    temperature: np.ndarray,
    moisture: np.ndarray,
) -> None:
    temperature_cmap = LinearSegmentedColormap.from_list(
        "temperature_seq", [tint(ACCENT_ORANGE, 0.92), ACCENT_ORANGE]
    )
    moisture_cmap = LinearSegmentedColormap.from_list(
        "moisture_seq", [COLOR_MAIN, tint(COLOR_MAIN, 0.92)]
    )
    time_h = time_s / 3600.0
    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    specs = (
        (
            axes[0],
            temperature,
            temperature_cmap,
            "Temperature field",
            "Temperature (°C)",
        ),
        (
            axes[1],
            moisture,
            moisture_cmap,
            "Moisture field",
            "Moisture concentration (kg/kg)",
        ),
    )
    for tag, (ax, field, cmap, title, colorbar_label) in zip("ab", specs):
        mesh = ax.pcolormesh(
            time_h,
            radius_cm,
            field.T,
            shading="auto",
            cmap=cmap,
            vmin=float(field.min()),
            vmax=float(field.max()),
            rasterized=True,
        )
        ax.contour(
            time_h,
            radius_cm,
            field.T,
            levels=np.linspace(float(field.min()), float(field.max()), 7)[1:-1],
            colors=COLOR_BASELINE_DARK,
            linewidths=0.35,
            alpha=0.45,
        )
        colorbar = fig.colorbar(mesh, ax=ax, pad=0.018, fraction=0.036)
        colorbar.set_label(colorbar_label, fontsize=FS_LABEL, color=COLOR_INK)
        colorbar.ax.tick_params(labelsize=FS_TICK, colors=COLOR_INK, width=0.7)
        colorbar.outline.set_linewidth(0.6)
        ax.set_title(title)
        ax.set_ylabel("Distance from axis (cm)")
        ax.set_ylim(0.0, 2.0)
        ax.set_yticks(np.arange(0.0, 2.01, 0.5))
        style_axes(ax, grid=None)
        add_panel_label(ax, tag)
    axes[-1].set_xlabel("Time (h)")
    axes[-1].set_xlim(0.0, 3.0)
    axes[-1].set_xticks(np.arange(0.0, 3.01, 0.5))
    fig.subplots_adjust(hspace=0.34)
    save_all(fig, "q2_spatiotemporal_fields")


def plot_radial_profiles(
    time_s: np.ndarray,
    radius_cm: np.ndarray,
    temperature: np.ndarray,
    moisture: np.ndarray,
) -> None:
    selected_h = np.arange(0.5, 3.01, 0.5)
    indices = [int(np.argmin(np.abs(time_s - hour * 3600.0))) for hour in selected_h]
    line_styles = ("-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1)))
    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    for index, (hour, time_index) in enumerate(zip(selected_h, indices)):
        color = identity_color(index)
        label = f"{hour:.1f} h"
        for ax, values in (
            (axes[0], temperature[time_index]),
            (axes[1], moisture[time_index]),
        ):
            ax.plot(
                radius_cm,
                values,
                color=color,
                linewidth=1.65,
                marker="o",
                markevery=4,
                markerfacecolor="white",
                markeredgewidth=0.75,
                linestyle=line_styles[index],
                label=label,
            )
    axes[0].set_ylabel("Temperature (°C)")
    axes[1].set_ylabel("Dry-basis moisture (kg/kg)")
    axes[1].set_xlabel("Distance from axis (cm)")
    for tag, ax in zip("ab", axes):
        ax.set_xlim(-0.03, 2.03)
        ax.set_xticks(np.arange(0.0, 2.01, 0.5))
        style_axes(ax, grid="y")
        add_panel_label(ax, tag)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        frameon=False,
        fontsize=FS_ANNOT,
    )
    fig.subplots_adjust(top=0.88, hspace=0.24)
    save_all(fig, "q2_radial_profiles")


def plot_center_surface(
    time_s: np.ndarray, temperature: np.ndarray, moisture: np.ndarray
) -> None:
    time_h = time_s / 3600.0
    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    specs = (
        (
            axes[0],
            temperature[:, 0],
            temperature[:, -1],
            "Axis and surface temperature",
            "Temperature (°C)",
        ),
        (
            axes[1],
            moisture[:, 0],
            moisture[:, -1],
            "Axis and surface moisture",
            "Moisture concentration (kg/kg)",
        ),
    )
    for tag, (ax, axis_values, surface_values, title, ylabel) in zip(
        "ab", specs
    ):
        ax.fill_between(
            time_h,
            np.minimum(axis_values, surface_values),
            np.maximum(axis_values, surface_values),
            color=tint(COLOR_MAIN, 0.45),
            alpha=0.18,
        )
        ax.plot(time_h, axis_values, color=COLOR_MAIN, linewidth=2.0)
        ax.plot(
            time_h,
            surface_values,
            color=ACCENT_ORANGE,
            linewidth=1.8,
            linestyle="--",
        )
        ax.scatter(
            [time_h[-1], time_h[-1]],
            [axis_values[-1], surface_values[-1]],
            color=[COLOR_MAIN, ACCENT_ORANGE],
            s=20,
            edgecolor="white",
            linewidth=0.7,
            zorder=5,
        )
        label_offset = 0.018 * float(np.ptp(np.r_[axis_values, surface_values]))
        if abs(axis_values[-1] - surface_values[-1]) < 4.0 * label_offset:
            axis_label_y = axis_values[-1] + label_offset
            surface_label_y = surface_values[-1] - label_offset
        else:
            axis_label_y = axis_values[-1]
            surface_label_y = surface_values[-1]
        ax.text(
            3.03,
            axis_label_y,
            "Axis",
            color=COLOR_MAIN,
            fontsize=FS_ANNOT,
            va="center",
        )
        ax.text(
            3.03,
            surface_label_y,
            "Surface",
            color=ACCENT_ORANGE,
            fontsize=FS_ANNOT,
            va="center",
        )
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        style_axes(ax, grid="y")
        add_panel_label(ax, tag)
    axes[-1].set_xlabel("Time (h)")
    axes[-1].set_xlim(0.0, 3.22)
    axes[-1].set_xticks(np.arange(0.0, 3.01, 0.5))
    fig.subplots_adjust(hspace=0.38)
    save_all(fig, "q2_center_surface_response")


def diffusivity(moisture: np.ndarray, temperature_c: np.ndarray) -> np.ndarray:
    """Evaluate the prescribed diffusivity on the saved formal fields."""
    return (
        2.4e-3
        * np.exp(-0.45 / moisture)
        * np.exp(-3850.0 / (temperature_c + 273.15))
    )


def plot_diffusivity(
    time_s: np.ndarray, temperature: np.ndarray, moisture: np.ndarray
) -> None:
    time_h = time_s / 3600.0
    diffusivity_axis = diffusivity(moisture[:, 0], temperature[:, 0]) * 1.0e9
    diffusivity_surface = (
        diffusivity(moisture[:, -1], temperature[:, -1]) * 1.0e9
    )
    fig, ax = plt.subplots(figsize=FIG_FULL)
    ax.plot(
        time_h, diffusivity_axis, color=COLOR_MAIN, linewidth=2.0, label="Axis"
    )
    ax.plot(
        time_h,
        diffusivity_surface,
        color=ACCENT_ORANGE,
        linewidth=1.8,
        label="Surface",
    )
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Moisture diffusivity (10⁻⁹ m²/s)")
    ax.set_xlim(0.0, 3.0)
    style_axes(ax, grid="y")
    ax.legend(loc="best")
    fig.tight_layout()
    save_all(fig, "q2_diffusivity_timeseries")


def main() -> None:
    if not INPUT_XLSX.exists():
        raise FileNotFoundError(f"未找到正式结果工作簿：{INPUT_XLSX}")
    time_s, radius_cm, temperature, moisture = load_fields()
    plot_spatiotemporal(time_s, radius_cm, temperature, moisture)
    plot_radial_profiles(time_s, radius_cm, temperature, moisture)
    plot_center_surface(time_s, temperature, moisture)
    plot_diffusivity(time_s, temperature, moisture)
    print(f"数据文件：{INPUT_XLSX}")
    print(f"网格：{temperature.shape[0]}个时刻 × {temperature.shape[1]}个半径位置")
    print(f"图件目录：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
