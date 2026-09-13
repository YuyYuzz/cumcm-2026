# 文件名：make_q2_figures_from_excel.py
# 用途：第二问温度、水分及扩散系数结果图绘图程序。
from __future__ import annotations

import os
import posixpath
import re
import sys
import types
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "scripts" / "plotting" / ".mplconfig"))
STYLE_DIR = PROJECT_ROOT / ".agents" / "skills" / "mathmodel-figure" / "code" / "style"
sys.path.insert(0, str(STYLE_DIR))

import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler
from matplotlib.colors import LinearSegmentedColormap

try:
    import seaborn  # noqa: F401
except ModuleNotFoundError:
    seaborn_fallback = types.ModuleType("seaborn")

    def set_theme(*, style="ticks", palette=None, font_scale=1.0, rc=None):
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
    FIG_FULL,
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


INPUT_XLSX = PROJECT_ROOT / "tables" / "q2" / "result2.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "figures" / "final" / "q2"
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def col_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def read_sheet(sheet_name: str) -> list[list[float | None]]:
    with zipfile.ZipFile(INPUT_XLSX) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationship_id = next(
            sheet.attrib[f"{{{DOC_REL_NS}}}id"]
            for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet")
            if sheet.attrib.get("name") == sheet_name
        )
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(
            rel.attrib["Target"]
            for rel in relationships.findall(f"{{{PKG_REL_NS}}}Relationship")
            if rel.attrib.get("Id") == relationship_id
        )
        sheet_path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        root = ET.fromstring(archive.read(sheet_path))

    rows = root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row")
    matrix: list[list[float | None]] = []
    for row in rows:
        values: list[float | None] = [None] * 22
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            node = cell.find(f"{{{MAIN_NS}}}v")
            values[col_index(cell.attrib["r"])] = None if node is None else float(node.text)
        matrix.append(values)
    return matrix


def load_fields() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    temp_rows = read_sheet("温度")
    moisture_rows = read_sheet("水分浓度")
    time_s = np.asarray([row[0] for row in temp_rows[1:]], dtype=float)
    radius_cm = np.asarray(temp_rows[0][1:], dtype=float)
    temperature = np.asarray([row[1:] for row in temp_rows[1:]], dtype=float)
    moisture = np.asarray([row[1:] for row in moisture_rows[1:]], dtype=float)
    assert temperature.shape == moisture.shape == (10800, 21)
    assert np.all(np.isfinite(temperature)) and np.all(np.isfinite(moisture))
    assert np.all(np.diff(time_s) > 0) and np.all(np.diff(radius_cm) > 0)
    return time_s, radius_cm, temperature, moisture


def save_all(fig: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUTPUT_DIR / stem
    save_fig(fig, str(base.with_suffix(".png")), close=False, dpi=300)
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.1)
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)


def plot_spatiotemporal(time_s, radius_cm, temperature, moisture) -> None:
    temperature_cmap = LinearSegmentedColormap.from_list(
        "temperature_seq", [tint(ACCENT_ORANGE, 0.92), ACCENT_ORANGE]
    )
    moisture_cmap = LinearSegmentedColormap.from_list(
        "moisture_seq", [COLOR_MAIN, tint(COLOR_MAIN, 0.92)]
    )
    time_h = time_s / 3600.0
    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    specs = (
        (axes[0], temperature, temperature_cmap, "Temperature field", "Temperature (°C)"),
        (axes[1], moisture, moisture_cmap, "Moisture field", "Moisture concentration (kg/kg)"),
    )
    for tag, (ax, field, cmap, title, cbar_label) in zip("ab", specs):
        levels = np.linspace(float(field.min()), float(field.max()), 80)
        mesh = ax.pcolormesh(
            time_h, radius_cm, field.T, shading="auto", cmap=cmap,
            vmin=float(field.min()), vmax=float(field.max()), rasterized=True,
        )
        ax.contour(
            time_h, radius_cm, field.T,
            levels=np.linspace(float(field.min()), float(field.max()), 7)[1:-1],
            colors=COLOR_BASELINE_DARK, linewidths=0.35, alpha=0.45,
        )
        cbar = fig.colorbar(mesh, ax=ax, pad=0.018, fraction=0.036)
        cbar.set_label(cbar_label, fontsize=FS_LABEL, color=COLOR_INK)
        cbar.ax.tick_params(labelsize=FS_TICK, colors=COLOR_INK, width=0.7)
        cbar.outline.set_linewidth(0.6)
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


def plot_radial_profiles(time_s, radius_cm, temperature, moisture) -> None:
    selected_h = np.arange(0.5, 3.01, 0.5)
    indices = [int(np.argmin(np.abs(time_s - h * 3600.0))) for h in selected_h]
    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    for i, (h, index) in enumerate(zip(selected_h, indices)):
        color = identity_color(i)
        label = f"{h:.1f} h"
        for ax, values in ((axes[0], temperature[index]), (axes[1], moisture[index])):
            ax.plot(radius_cm, values, color=color, linewidth=1.65, marker="o", markevery=4,
                    markerfacecolor="white", markeredgewidth=0.75,
                    linestyle=("-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1)))[i],
                    label=label)
    axes[0].set_ylabel("Temperature (°C)")
    axes[1].set_ylabel("Dry-basis moisture (kg/kg)")
    axes[1].set_xlabel("Distance from axis (cm)")
    for tag, ax in zip("ab", axes):
        ax.set_xlim(-0.03, 2.03)
        ax.set_xticks(np.arange(0.0, 2.01, 0.5))
        style_axes(ax, grid="y")
        add_panel_label(ax, tag)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, fontsize=FS_ANNOT)
    fig.subplots_adjust(top=0.88, hspace=0.24)
    save_all(fig, "q2_radial_profiles")


def plot_center_surface(time_s, temperature, moisture) -> None:
    time_h = time_s / 3600.0
    fig, axes = plt.subplots(2, 1, figsize=FIG_TALL, sharex=True)
    specs = (
        (axes[0], temperature[:, 0], temperature[:, -1], "Axis and surface temperature", "Temperature (°C)"),
        (axes[1], moisture[:, 0], moisture[:, -1], "Axis and surface moisture", "Moisture concentration (kg/kg)"),
    )
    for tag, (ax, axis_values, surface_values, title, ylabel) in zip("ab", specs):
        ax.fill_between(time_h, np.minimum(axis_values, surface_values),
                        np.maximum(axis_values, surface_values), color=tint(COLOR_MAIN, 0.45), alpha=0.18)
        ax.plot(time_h, axis_values, color=COLOR_MAIN, linewidth=2.0)
        ax.plot(time_h, surface_values, color=ACCENT_ORANGE, linewidth=1.8, linestyle="--")
        ax.scatter([time_h[-1], time_h[-1]], [axis_values[-1], surface_values[-1]],
                   color=[COLOR_MAIN, ACCENT_ORANGE], s=20, edgecolor="white", linewidth=0.7, zorder=5)
        label_offset = 0.018 * float(np.ptp(np.r_[axis_values, surface_values]))
        if abs(axis_values[-1] - surface_values[-1]) < 4 * label_offset:
            axis_label_y = axis_values[-1] + label_offset
            surface_label_y = surface_values[-1] - label_offset
        else:
            axis_label_y = axis_values[-1]
            surface_label_y = surface_values[-1]
        ax.text(3.03, axis_label_y, "Axis", color=COLOR_MAIN, fontsize=FS_ANNOT, va="center")
        ax.text(3.03, surface_label_y, "Surface", color=ACCENT_ORANGE, fontsize=FS_ANNOT, va="center")
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        style_axes(ax, grid="y")
        add_panel_label(ax, tag)
    axes[-1].set_xlabel("Time (h)")
    axes[-1].set_xlim(0.0, 3.22)
    axes[-1].set_xticks(np.arange(0.0, 3.01, 0.5))
    fig.subplots_adjust(hspace=0.38)
    save_all(fig, "q2_center_surface_response")


def plot_diffusivity(time_s, temperature, moisture) -> None:
    time_h = time_s / 3600.0
    def diffusivity(c, temp):
        return 2.4e-3 * np.exp(-0.45 / c) * np.exp(-3850.0 / (temp + 273.15))
    d_axis = diffusivity(moisture[:, 0], temperature[:, 0]) * 1e9
    d_surface = diffusivity(moisture[:, -1], temperature[:, -1]) * 1e9
    fig, ax = plt.subplots(figsize=FIG_FULL)
    ax.plot(time_h, d_axis, color=COLOR_MAIN, linewidth=2.0, label="Axis")
    ax.plot(time_h, d_surface, color=ACCENT_ORANGE, linewidth=1.8, label="Surface")
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Moisture diffusivity (10⁻⁹ m²/s)")
    ax.set_xlim(0.0, 3.0)
    style_axes(ax, grid="y")
    ax.legend(loc="best")
    fig.tight_layout()
    save_all(fig, "q2_diffusivity_timeseries")


def main() -> None:
    time_s, radius_cm, temperature, moisture = load_fields()
    plot_spatiotemporal(time_s, radius_cm, temperature, moisture)
    plot_radial_profiles(time_s, radius_cm, temperature, moisture)
    plot_center_surface(time_s, temperature, moisture)
    plot_diffusivity(time_s, temperature, moisture)
    print(f"Source: {INPUT_XLSX}")
    print(f"Grid: {temperature.shape[0]} time rows × {temperature.shape[1]} radial positions")
    print(f"Temperature range: {temperature.min():.4f}–{temperature.max():.4f} °C")
    print(f"Moisture range: {moisture.min():.4f}–{moisture.max():.4f} kg/kg")


if __name__ == "__main__":
    main()
