"""Analytic decay example for the layout preview, not contest results."""
from math import exp, isclose


def state(t, x0=1.0, k=0.5):
    if t < 0 or k <= 0:
        raise ValueError("Require t >= 0 and k > 0")
    return x0 * exp(-k * t)


if __name__ == "__main__":
    assert isclose(state(0), 1.0)
    for time in range(6):
        print(f"t={time}, x={state(time):.6f}")
