# 文件名：plot_q1.py
# 用途：第一问温度与水分时空分布、径向剖面及响应曲线绘图程序。

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
INPUT_XLSX = PACKAGE_ROOT / "results" / "result1.xlsx"
ATTACHMENT_1 = (
    PACKAGE_ROOT / "CUMCM2026Problems" / "A题" / "附件" / "附件1.xlsx"
)
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
    """Convert an Excel cell reference to a zero-based column index."""
    letters = re.match(r"[A-Z]+", cell_reference)
    if letters is None:
        raise ValueError(f"Invalid cell reference: {cell_reference}")
    result = 0
    for char in letters.group(0):
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """Read the optional XLSX shared-string table."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def worksheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    """Resolve a worksheet name to its XML part inside an XLSX file."""
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


def read_worksheet(
    sheet_name: str, input_path: Path
) -> list[list[object | None]]:
    """Read worksheet values without adding an Excel-library dependency."""
    with zipfile.ZipFile(input_path) as archive:
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
    """Load and validate one time-radius field from result1.xlsx."""
    rows = read_worksheet(sheet_name, INPUT_XLSX)
    radius_cm = np.asarray(rows[0][1:22], dtype=float)
    time_s = np.asarray([row[0] for row in rows[1:]], dtype=float)
    values = np.asarray([row[1:22] for row in rows[1:]], dtype=float)

    expected_time = np.arange(1.0, 1801.0)
    expected_radius = np.arange(21, dtype=float) / 10.0
    if not np.array_equal(time_s, expected_time):
        raise ValueError(f"{sheet_name}的时间列必须为1至1800 s")
    if not np.allclose(radius_cm, expected_radius, rtol=0.0, atol=1.0e-12):
        raise ValueError(f"{sheet_name}的半径表头必须为0至2.0 cm，步长0.1 cm")
    if values.shape != (1800, 21):
        raise ValueError(f"{sheet_name}数据形状异常：{values.shape}")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{sheet_name}中存在非有限数值")
    return time_s, radius_cm, values


def save_all(fig: plt.Figure, stem: str) -> None:
    """Export one figure as PNG, PDF and SVG."""
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


def make_spatiotemporal_fields(
    time_s: np.ndarray,
    radius_cm: np.ndarray,
    temperature_c: np.ndarray,
    moisture: np.ndarray,
) -> None:
    """Show how heating and drying propagate from the surface to the axis."""
    temperature_cmap = LinearSegmentedColormap.from_list(
        "temperature_seq", [tint(ACCENT_ORANGE, 0.92), ACCENT_ORANGE]
    )
    moisture_cmap = LinearSegmentedColormap.from_list(
        "moisture_dry_front", [COLOR_MAIN, tint(COLOR_MAIN, 0.92)]
    )

    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    panels = (
        (
            axes[0],
            temperature_c,
            temperature_cmap,
            "Temperature field",
            "Temperature (°C)",
            np.linspace(float(temperature_c.min()), float(temperature_c.max()), 80),
        ),
        (
            axes[1],
            moisture,
            moisture_cmap,
            "Moisture field",
            "Moisture concentration (kg/kg)",
            np.linspace(float(moisture.min()), float(moisture.max()), 80),
        ),
    )

    for tag, (ax, field, cmap, title, colorbar_label, levels) in zip("ab", panels):
        filled = ax.contourf(time_s, radius_cm, field.T, levels=levels, cmap=cmap)
        line_levels = np.linspace(float(field.min()), float(field.max()), 7)[1:-1]
        ax.contour(
            time_s,
            radius_cm,
            field.T,
            levels=line_levels,
            colors=COLOR_BASELINE_DARK,
            linewidths=0.35,
            alpha=0.45,
        )
        colorbar = fig.colorbar(filled, ax=ax, pad=0.018, fraction=0.036)
        colorbar.set_label(colorbar_label, fontsize=FS_LABEL, color=COLOR_INK)
        colorbar.ax.tick_params(labelsize=FS_TICK, colors=COLOR_INK, width=0.7)
        colorbar.outline.set_linewidth(0.6)
        ax.set_title(title)
        ax.set_ylabel("Distance from axis (cm)")
        ax.set_ylim(radius_cm[0], radius_cm[-1])
        ax.set_yticks(np.arange(0.0, 2.01, 0.5))
        style_axes(ax, grid=None)
        add_panel_label(ax, tag)

    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(0.0, 1800.0)
    axes[-1].set_xticks(np.arange(0, 1801, 300))
    fig.subplots_adjust(hspace=0.34)
    save_all(fig, "q1_spatiotemporal_fields")


def make_radial_profiles(
    time_s: np.ndarray,
    radius_cm: np.ndarray,
    temperature_c: np.ndarray,
    moisture: np.ndarray,
) -> None:
    """Compare radial gradients at four representative times."""
    selected_times = (100.0, 600.0, 1200.0, 1800.0)
    indices = [int(np.argmin(np.abs(time_s - value))) for value in selected_times]
    colors = [identity_color(index) for index in range(len(selected_times))]

    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    for index, selected_time, color in zip(indices, selected_times, colors):
        label = f"{selected_time:.0f} s"
        axes[0].plot(
            radius_cm,
            temperature_c[index],
            color=color,
            linewidth=1.8,
            marker="o",
            markevery=4,
            markerfacecolor="white",
            markeredgewidth=0.8,
        )
        axes[0].text(
            radius_cm[-1] + 0.035,
            temperature_c[index, -1],
            label,
            color=color,
            fontsize=FS_ANNOT,
            va="center",
        )
        axes[1].plot(
            radius_cm,
            moisture[index],
            color=color,
            linewidth=1.8,
            marker="o",
            markevery=4,
            markerfacecolor="white",
            markeredgewidth=0.8,
        )
        axes[1].text(
            radius_cm[-1] + 0.035,
            moisture[index, -1],
            label,
            color=color,
            fontsize=FS_ANNOT,
            va="center",
        )

    axes[0].set_title("Radial temperature profiles")
    axes[0].set_ylabel("Temperature (°C)")
    axes[1].set_title("Radial moisture profiles")
    axes[1].set_ylabel("Moisture concentration (kg/kg)")
    axes[1].set_xlabel("Distance from axis (cm)")

    for tag, ax in zip("ab", axes):
        ax.set_xlim(radius_cm[0] - 0.03, radius_cm[-1] + 0.16)
        ax.set_xticks(np.arange(0.0, 2.01, 0.5))
        style_axes(ax, grid="y")
        add_panel_label(ax, tag)

    fig.subplots_adjust(hspace=0.38)
    save_all(fig, "q1_radial_profiles")


def load_ambient(time_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate the official drying-room record at the result times."""
    if not ATTACHMENT_1.exists():
        relative = ATTACHMENT_1.relative_to(PACKAGE_ROOT)
        raise FileNotFoundError(
            "未找到赛题附件1，请将官方“附件1.xlsx”放置于：\n"
            f"{relative.as_posix()}"
        )
    rows = read_worksheet("Sheet1", ATTACHMENT_1)
    records = np.asarray(
        [
            row[:3]
            for row in rows
            if len(row) >= 3 and isinstance(row[0], (float, int))
        ],
        dtype=float,
    )
    expected_times = np.arange(0.0, 14401.0, 60.0)
    if records.shape != (241, 3) or not np.array_equal(
        records[:, 0], expected_times
    ):
        raise ValueError("附件1应包含0至14400 s的241组环境记录")
    return (
        np.interp(time_s, records[:, 0], records[:, 1]),
        np.interp(time_s, records[:, 0], records[:, 2]),
    )


def make_center_surface_response(
    time_s: np.ndarray,
    temperature_c: np.ndarray,
    moisture: np.ndarray,
) -> None:
    """Compare axis, reconstructed surface and drying-room conditions."""
    ambient_temperature, ambient_moisture = load_ambient(time_s)
    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    panels = (
        (
            temperature_c,
            ambient_temperature,
            "Temperature response",
            "Temperature (°C)",
        ),
        (
            moisture,
            ambient_moisture,
            "Moisture response",
            "Moisture concentration (kg/kg)",
        ),
    )
    for tag, ax, (values, ambient, title, ylabel) in zip("ab", axes, panels):
        ax.plot(time_s, values[:, 0], color=COLOR_MAIN, lw=1.8, label="Axis")
        ax.plot(
            time_s,
            values[:, -1],
            color=ACCENT_ORANGE,
            lw=1.8,
            ls="--",
            label="Surface",
        )
        ax.plot(
            time_s,
            ambient,
            color=COLOR_BASELINE_DARK,
            lw=1.3,
            ls=":",
            label="Drying room",
        )
        ax.set(title=title, ylabel=ylabel)
        ax.legend(frameon=False, fontsize=FS_ANNOT, ncol=3)
        style_axes(ax, grid="y")
        add_panel_label(ax, tag)
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(0.0, 1800.0)
    axes[-1].set_xticks(np.arange(0, 1801, 300))
    fig.subplots_adjust(hspace=0.38)
    save_all(fig, "q1_center_surface_response")


def main() -> None:
    if not INPUT_XLSX.exists():
        raise FileNotFoundError(f"未找到正式结果工作簿：{INPUT_XLSX}")
    time_t, radius_t, temperature_c = load_field("温度")
    time_c, radius_c, moisture = load_field("水分浓度")
    if not (
        np.array_equal(time_t, time_c)
        and np.array_equal(radius_t, radius_c)
    ):
        raise ValueError("温度与水分工作表的时间列或半径表头不一致")

    make_spatiotemporal_fields(time_t, radius_t, temperature_c, moisture)
    make_radial_profiles(time_t, radius_t, temperature_c, moisture)
    make_center_surface_response(time_t, temperature_c, moisture)

    print(f"数据文件：{INPUT_XLSX}")
    print(f"网格：{time_t.size}个时刻 × {radius_t.size}个半径位置")
    print(f"图件目录：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
