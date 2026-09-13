# 文件名：make_q1_spatiotemporal_figures.py
# 用途：第一问温度与水分时空分布、径向剖面及响应曲线绘图程序。
from __future__ import annotations

import os
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault(
    "MPLCONFIGDIR", str(PROJECT_ROOT / "scripts" / "plotting" / ".mplconfig")
)

STYLE_DIR = (
    PROJECT_ROOT
    / ".agents"
    / "skills"
    / "mathmodel-figure"
    / "code"
    / "style"
)
sys.path.insert(0, str(STYLE_DIR))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

try:
    import seaborn  # noqa: F401
except ModuleNotFoundError:
    import types

    from cycler import cycler

    seaborn_fallback = types.ModuleType("seaborn")

    def set_theme(*, style="ticks", palette=None, font_scale=1.0, rc=None):
        """Provide the small seaborn surface required by plot_style."""
        del style, font_scale
        if palette is not None:
            plt.rcParams["axes.prop_cycle"] = cycler(color=palette)
        if rc:
            plt.rcParams.update(rc)

    seaborn_fallback.set_theme = set_theme
    sys.modules["seaborn"] = seaborn_fallback

from plot_style import (
    ACCENT_ORANGE,
    COLOR_BASELINE_DARK,
    COLOR_INK,
    COLOR_MAIN,
    FIG_TALL,
    FS_ANNOT,
    FS_LABEL,
    FS_TICK,
    add_panel_label,
    identity_color,
    save_fig,
    style_axes,
    tint,
)


INPUT_XLSX = PROJECT_ROOT / "tables" / "q1" / "result1.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "figures" / "final" / "q1"

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


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
    strings: list[str] = []
    for item in root.findall(f"{{{MAIN_NS}}}si"):
        strings.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
    return strings


def worksheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    """Resolve a worksheet name to its XML part inside the XLSX archive."""
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = None
    for sheet in workbook_root.findall(f".//{{{MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            relationship_id = sheet.attrib.get(f"{{{DOC_REL_NS}}}id")
            break
    if relationship_id is None:
        raise ValueError(f"Missing worksheet: {sheet_name}")

    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in rels_root.findall(f"{{{PKG_REL_NS}}}Relationship"):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib["Target"]
            if target.startswith("/"):
                return target.lstrip("/")
            return posixpath.normpath(posixpath.join("xl", target))
    raise ValueError(f"Missing relationship for worksheet: {sheet_name}")


def read_worksheet(sheet_name: str, input_path: Path = INPUT_XLSX) -> list[list[object | None]]:
    """Read values from one worksheet without third-party Excel dependencies."""
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

    maximum_row = max(row_index for row_index, _ in parsed_rows) + 1
    matrix: list[list[object | None]] = [
        [None] * maximum_column for _ in range(maximum_row)
    ]
    for row_index, values in parsed_rows:
        for col_index, value in values.items():
            matrix[row_index][col_index] = value
    return matrix


def load_field(sheet_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load a time-radius field from the official result workbook."""
    rows = read_worksheet(sheet_name)

    radius_cm = np.asarray(rows[0][1:], dtype=float)
    time_s = np.asarray([row[0] for row in rows[1:]], dtype=float)
    values = np.asarray([row[1:] for row in rows[1:]], dtype=float)

    expected_shape = (time_s.size, radius_cm.size)
    if values.shape != expected_shape:
        raise ValueError(f"Unexpected {sheet_name} shape: {values.shape}")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"Non-finite values found in {sheet_name}")
    if not (np.all(np.diff(time_s) > 0) and np.all(np.diff(radius_cm) > 0)):
        raise ValueError(f"Axes are not strictly increasing in {sheet_name}")
    return time_s, radius_cm, values


def save_all(fig: plt.Figure, stem: str) -> None:
    """Export one figure as publication-ready PNG, PDF, and SVG."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUTPUT_DIR / stem
    save_fig(fig, str(base.with_suffix(".png")), close=False, dpi=300)
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.1)
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)


def make_spatiotemporal_fields(
    time_s: np.ndarray,
    radius_cm: np.ndarray,
    temperature_c: np.ndarray,
    moisture: np.ndarray,
) -> None:
    """Show how heating and drying propagate from the surface toward the axis."""
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
            "%.1f",
        ),
        (
            axes[1],
            moisture,
            moisture_cmap,
            "Moisture field",
            "Moisture concentration (kg/kg)",
            np.linspace(float(moisture.min()), float(moisture.max()), 80),
            "%.2f",
        ),
    )

    for tag, (ax, field, cmap, title, colorbar_label, levels, tick_format) in zip(
        "ab", panels
    ):
        filled = ax.contourf(time_s, radius_cm, field.T, levels=levels, cmap=cmap)
        line_levels = np.linspace(float(field.min()), float(field.max()), 7)[1:-1]
        ax.contour(
            time_s, radius_cm, field.T, levels=line_levels,
            colors=COLOR_BASELINE_DARK, linewidths=0.35, alpha=0.45,
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
    axes[-1].set_xlim(time_s[0], time_s[-1])
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
    colors = [identity_color(i) for i in range(len(selected_times))]

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


def make_center_surface_response(
    time_s: np.ndarray,
    temperature_c: np.ndarray,
    moisture: np.ndarray,
) -> None:
    """Expose the growing axis-to-surface lag during preheating."""
    # 环境曲线只读取附件1并分段线性插值，不重新求解主模型。
    attachment = PROJECT_ROOT / "data/raw/problems/A题/附件/附件1.xlsx"
    rows = read_worksheet("Sheet1", attachment)
    records = np.asarray([row[:3] for row in rows
                          if len(row) >= 3 and isinstance(row[0], (float, int))], dtype=float)
    if records.shape != (241, 3) or not np.array_equal(records[:, 0], np.arange(0, 14401, 60)):
        raise ValueError("附件1应包含0至14400 s的241组环境记录")
    if time_s.min() < 0 or time_s.max() > 1800:
        raise ValueError("本图只使用问题一0至1800 s结果")
    ambient_t = np.interp(time_s, records[:, 0], records[:, 1])
    ambient_c = np.interp(time_s, records[:, 0], records[:, 2])
    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    panels = [(temperature_c, ambient_t, "Temperature response", "Temperature (°C)"),
              (moisture, ambient_c, "Moisture response", "Moisture concentration (kg/kg)")]
    for tag, ax, (values, ambient, title, ylabel) in zip("ab", axes, panels):
        ax.plot(time_s, values[:, 0], color=COLOR_MAIN, lw=1.8, label="Axis")
        ax.plot(time_s, values[:, -1], color=ACCENT_ORANGE, lw=1.8, ls="--", label="Surface")
        ax.plot(time_s, ambient, color=COLOR_BASELINE_DARK, lw=1.3, ls=":", label="Drying room")
        ax.set(title=title, ylabel=ylabel)
        ax.legend(frameon=False, fontsize=FS_ANNOT, ncol=3)
        style_axes(ax, grid="y")
        add_panel_label(ax, tag)
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(0, 1800)
    axes[-1].set_xticks(np.arange(0, 1801, 300))
    fig.subplots_adjust(hspace=0.38)
    save_all(fig, "q1_center_surface_response")


def main() -> None:
    time_t, radius_t, temperature_c = load_field("温度")
    time_c, radius_c, moisture = load_field("水分浓度")
    if not (np.array_equal(time_t, time_c) and np.array_equal(radius_t, radius_c)):
        raise ValueError("Temperature and moisture grids do not match")

    make_spatiotemporal_fields(time_t, radius_t, temperature_c, moisture)
    make_radial_profiles(time_t, radius_t, temperature_c, moisture)
    make_center_surface_response(time_t, temperature_c, moisture)

    print(f"Source: {INPUT_XLSX}")
    print(f"Grid: {time_t.size} times × {radius_t.size} radii")
    print(
        "Final axis/surface: "
        f"T={temperature_c[-1, 0]:.4f}/{temperature_c[-1, -1]:.4f} °C, "
        f"C={moisture[-1, 0]:.4f}/{moisture[-1, -1]:.4f} kg/kg"
    )
    for stem in (
        "q1_spatiotemporal_fields",
        "q1_radial_profiles",
        "q1_center_surface_response",
    ):
        print(OUTPUT_DIR / f"{stem}.png")
        print(OUTPUT_DIR / f"{stem}.pdf")
        print(OUTPUT_DIR / f"{stem}.svg")


if __name__ == "__main__":
    main()
