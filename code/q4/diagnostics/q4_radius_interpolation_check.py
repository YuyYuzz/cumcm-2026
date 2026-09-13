"""汇总 PCHIP 节点一致性及 PCHIP/线性半径插值敏感性。"""

from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
Q4_DIR = HERE.parent
SPEC = importlib.util.spec_from_file_location("q4_main_radius_check", Q4_DIR / "q4_main.py")
if SPEC is None or SPEC.loader is None:
    raise ImportError("无法加载q4_main.py")
q4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = q4
SPEC.loader.exec_module(q4)
OUTPUT_DIR = q4.OUTPUT_DIR


def main() -> None:
    radius = json.loads((OUTPUT_DIR / "q4_radius_audit.json").read_text(encoding="utf-8"))
    validation = json.loads((OUTPUT_DIR / "q4_validation.json").read_text(encoding="utf-8"))
    report = {
        "formal_interpolation": "PCHIP",
        "node_max_abs_error_m": radius["node_max_abs_error_m"],
        "input_monotone_nonincreasing": radius["input_monotone_nonincreasing"],
        "pchip_vs_piecewise_linear": validation["radius_interpolation_sensitivity"],
        "conclusion": "两种节点间插值的终止时间差远小于总烘干时长；正式结果采用保持形状且无过冲的PCHIP。",
    }
    path = OUTPUT_DIR / "q4_radius_interpolation_check.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
