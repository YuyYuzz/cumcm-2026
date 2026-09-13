from pathlib import Path
from xml.sax.saxutils import escape
import os
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl-flowchart")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "figures/final/problem_relationship_flowchart.drawio"

BLUE, ORANGE, GRAY = "#1A6FC4", "#E58A22", "#767676"
INK, PALE_BLUE, PALE_ORANGE, PALE_GRAY = "#333333", "#EEF5FC", "#FFF3E3", "#F7F9FC"


def vertex(i, x, y, w, h, text, style):
    return f'<mxCell id="{i}" value="{escape(text)}" style="{style}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'


def edge(i, s, t, color=GRAY, label=""):
    return f'<mxCell id="{i}" value="{escape(label)}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={color};strokeWidth=1.8;endArrow=block;" edge="1" parent="1" source="{s}" target="{t}"><mxGeometry relative="1" as="geometry"/></mxCell>'


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    styles = {
        "start": f"rounded=1;whiteSpace=wrap;html=1;fillColor={BLUE};strokeColor={BLUE};fontColor=#FFFFFF;fontSize=13;fontStyle=1;align=center;verticalAlign=middle;",
        "input": f"rounded=1;whiteSpace=wrap;html=1;fillColor={PALE_GRAY};strokeColor={GRAY};strokeWidth=1.4;fontColor={INK};fontSize=12;align=center;verticalAlign=middle;",
        "model": f"rounded=1;whiteSpace=wrap;html=1;fillColor={PALE_BLUE};strokeColor={BLUE};strokeWidth=1.8;fontColor={INK};fontSize=12;align=center;verticalAlign=middle;",
        "q4": f"rounded=1;whiteSpace=wrap;html=1;fillColor={PALE_ORANGE};strokeColor={ORANGE};strokeWidth=1.8;fontColor={INK};fontSize=12;align=center;verticalAlign=middle;",
        "decision": f"rhombus;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor={GRAY};strokeWidth=1.5;fontColor={INK};fontSize=11;align=center;verticalAlign=middle;",
        "output": f"rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor={BLUE};strokeWidth=1.5;fontColor={INK};fontSize=12;align=center;verticalAlign=middle;",
        "end": f"rounded=1;whiteSpace=wrap;html=1;fillColor={BLUE};strokeColor={BLUE};fontColor=#FFFFFF;fontSize=13;fontStyle=1;align=center;verticalAlign=middle;",
    }
    items = [
        vertex("start", 330, 25, 260, 48, "Start: define drying problem", styles["start"]),
        vertex("input", 260, 105, 400, 58, "Read drying-air data, material properties,\\nand initial temperature/moisture", styles["input"]),
        vertex("prep", 285, 200, 350, 58, "Preprocess data and initialize radial grid\\n(axis r = 0, surface r = R)", styles["input"]),
        vertex("q1", 285, 295, 350, 64, "Q1: coupled heat–moisture model\\nfixed geometry; validate T(r,t), C(r,t)", styles["model"]),
        vertex("q2", 285, 400, 350, 64, "Q2: fixed-radius drying dynamics\\nprofiles, response, diffusivity", styles["model"]),
        vertex("q3", 285, 505, 350, 64, "Q3: global maximum Cmax(t)\\nand termination tracking", styles["model"]),
        vertex("judge", 340, 615, 240, 92, "Cmax ≤ 0.15?", styles["decision"]),
        vertex("again", 40, 630, 220, 60, "No: advance time\\nand repeat Q3", styles["input"]),
        vertex("record", 285, 755, 350, 58, "Record fixed-radius termination time\\nand boundary sensitivity", styles["output"]),
        vertex("q4", 285, 850, 350, 70, "Q4: introduce moving radius R(t)\\nmaterial-coordinate transport", styles["q4"]),
        vertex("compare", 285, 955, 350, 64, "Compare fixed/moving geometry\\nand A–D scenarios", styles["q4"]),
        vertex("end", 330, 1060, 260, 48, "Output figures, tables, conclusions", styles["end"]),
        edge("e0", "start", "input", BLUE), edge("e1", "input", "prep"), edge("e2", "prep", "q1"),
        edge("e3", "q1", "q2", BLUE), edge("e4", "q2", "q3", BLUE), edge("e5", "q3", "judge", BLUE),
        edge("e6", "judge", "again", GRAY, "No"), edge("e7", "again", "q3", GRAY, "repeat"),
        edge("e8", "judge", "record", BLUE, "Yes"), edge("e9", "record", "q4", ORANGE),
        edge("e10", "q4", "compare", ORANGE), edge("e11", "compare", "end", BLUE),
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?><mxGraphModel adaptiveColors="auto"><root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(items) + "</root></mxGraphModel>"
    OUT.write_text(xml, encoding="utf-8")
    print(OUT)

    render_static()


def render_static():
    """Export a publication preview while keeping the Draw.io source editable."""
    png = OUT.with_suffix(".png")
    pdf = OUT.with_suffix(".pdf")
    svg = OUT.with_suffix(".svg")
    fig, ax = plt.subplots(figsize=(7.2, 11.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 16)
    ax.axis("off")

    def box(x, y, w, h, text, face, edge, text_color=INK):
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                               facecolor=face, edgecolor=edge, linewidth=1.4)
        ax.add_patch(patch)
        lines = text.split("\n")
        ax.text(x + w / 2, y + h / 2, "\n".join(lines), ha="center", va="center",
                fontsize=9.2, color=text_color, linespacing=1.25,
                fontweight="bold" if face == BLUE else "normal")
        return (x, y, w, h)

    def diamond(x, y, w, h, text):
        points = [(x + w/2, y + h), (x + w, y + h/2), (x + w/2, y), (x, y + h/2)]
        ax.add_patch(Polygon(points, closed=True, facecolor="white", edgecolor=GRAY, linewidth=1.4))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=9.2, color=INK)
        return (x, y, w, h)

    def down(a, b, color=GRAY):
        x1, y1, w1, h1 = a; x2, y2, w2, h2 = b
        ax.add_patch(FancyArrowPatch((x1+w1/2, y1), (x2+w2/2, y2+h2),
                                     arrowstyle="-|>", mutation_scale=11,
                                     linewidth=1.3, color=color))

    def side(a, b, label, color=GRAY):
        x1, y1, w1, h1 = a; x2, y2, w2, h2 = b
        ax.add_patch(FancyArrowPatch((x1, y1+h1/2), (x2+w2, y2+h2/2),
                                     arrowstyle="-|>", mutation_scale=11,
                                     linewidth=1.3, color=color,
                                     connectionstyle="arc3,rad=0.18"))
        ax.text((x1+x2+w2)/2, (y1+y2+h2)/2+0.18, label, fontsize=8, color=GRAY, ha="center")

    stages = []
    stages.append(box(2.2, 14.9, 5.6, .62, "Start: define drying problem", BLUE, BLUE, "white"))
    stages.append(box(1.2, 13.75, 7.6, .72, "Read drying-air data, material properties, geometry,\nand initial temperature/moisture", PALE_GRAY, GRAY))
    stages.append(box(1.7, 12.55, 6.6, .72, "Preprocess data and initialize radial grid\n(axis r = 0, surface r = R)", PALE_GRAY, GRAY))
    stages.append(box(1.7, 11.25, 6.6, .82, "Q1: coupled heat–moisture model\nfixed geometry; validate T(r,t), C(r,t)", PALE_BLUE, BLUE))
    stages.append(box(1.7, 9.95, 6.6, .82, "Q2: fixed-radius drying dynamics\nprofiles, response, diffusivity", PALE_BLUE, BLUE))
    stages.append(box(1.7, 8.65, 6.6, .82, "Q3: global maximum Cmax(t)\nand termination tracking", PALE_BLUE, BLUE))
    judge = diamond(3.15, 7.15, 3.7, 1.0, "Cmax ≤ 0.15?")
    again = box(.35, 7.25, 2.1, .65, "No: advance time\nand repeat Q3", PALE_GRAY, GRAY)
    record = box(1.7, 5.72, 6.6, .72, "Record fixed-radius termination time\nand boundary sensitivity", "white", BLUE)
    q4 = box(1.7, 4.35, 6.6, .9, "Q4: introduce moving radius R(t)\nmaterial-coordinate transport", PALE_ORANGE, ORANGE)
    compare = box(1.7, 2.98, 6.6, .82, "Compare fixed/moving geometry\nand A–D scenarios", PALE_ORANGE, ORANGE)
    end = box(2.2, 1.65, 5.6, .62, "Output figures, tables, conclusions", BLUE, BLUE, "white")
    for a,b,c in zip(stages[:-1], stages[1:], [BLUE, GRAY, GRAY, BLUE, BLUE, BLUE]): down(a,b,c)
    down(stages[-1], judge, BLUE); side(judge, again, "No"); side(again, stages[-1], "repeat")
    down(judge, record, BLUE); ax.text(6.0, 6.75, "Yes", fontsize=8, color=BLUE)
    down(record, q4, ORANGE); down(q4, compare, ORANGE); down(compare, end, BLUE)
    fig.savefig(png, dpi=300, bbox_inches="tight", pad_inches=.15)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=.15)
    fig.savefig(svg, bbox_inches="tight", pad_inches=.15)
    plt.close(fig)
    print(png)
    print(pdf)
    print(svg)


if __name__ == "__main__":
    main()
