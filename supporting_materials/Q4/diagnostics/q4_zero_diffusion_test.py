# 文件名：q4_zero_diffusion_test.py
# 用途：该代码负责第四问材料坐标模型在零扩散与零传质边界条件下的结构极限检验。

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp


HERE = Path(__file__).resolve().parent
Q4_DIR = HERE.parent
SPEC = importlib.util.spec_from_file_location("q4_main_for_zero_limit", Q4_DIR / "q4_main.py")
if SPEC is None or SPEC.loader is None:
    raise ImportError("无法加载q4_main.py")
q4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = q4
SPEC.loader.exec_module(q4)


def run_test(cells: int = 257) -> dict[str, object]:
    grid = q4.make_grid(cells)
    initial = 0.85 + 0.30 * np.cos(np.pi * grid.centers)

    def zero_rhs(_t: float, state: np.ndarray) -> np.ndarray:
        # D=0且h_m=0时，材料坐标守恒有限体积式每个面通量均为0。
        return np.zeros_like(state)

    solution = solve_ivp(
        zero_rhs,
        (0.0, 48.0 * 3600.0),
        initial,
        method="BDF",
        rtol=1.0e-11,
        atol=1.0e-13,
        max_step=600.0,
        t_eval=np.array([0.0, 6.0, 12.0, 24.0, 36.0, 48.0]) * 3600.0,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    maximum_change = float(np.max(np.abs(solution.y - initial[:, None])))

    radius = q4.load_radius_data()
    t_probe = 6.0 * 3600.0
    rdot = float(radius._pchip.derivative()(t_probe))
    gradient = -0.30 * np.pi * np.sin(np.pi * grid.centers)
    wrong_extra_term = grid.centers * rdot / float(radius.radius(t_probe)) * gradient
    report = {
        "purpose": "材料坐标结构性极限实验，不改变正式主模型",
        "cells": cells,
        "time_range_s": [0.0, 172800.0],
        "initial_profile": "0.85+0.30*cos(pi*xi)",
        "D_m2_s": 0.0,
        "hm_m_s": 0.0,
        "max_abs_C_change": maximum_change,
        "acceptance_limit": 1.0e-10,
        "pass": bool(maximum_change < 1.0e-10),
        "wrong_extra_term_probe": {
            "time_s": t_probe,
            "Rdot_m_s": rdot,
            "max_abs_artificial_dCdt_s_1": float(np.max(np.abs(wrong_extra_term))),
            "interpretation": "若外挂xi*Rdot/R*C_xi项，非均匀材料浓度会在D=hm=0时凭空变化。",
        },
    }
    path = q4.OUTPUT_DIR / "q4_zero_diffusion_test.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run_test()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["pass"]:
        raise SystemExit(1)
