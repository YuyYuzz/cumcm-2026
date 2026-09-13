from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "figures/final/problem_relationship_flowchart"
BLUE, ORANGE, GRAY = "#1A6FC4", "#E58A22", "#767676"
INK, PALE_BLUE, PALE_ORANGE, PALE_GRAY = "#333333", "#EEF5FC", "#FFF3E3", "#F7F9FC"


def font(size, bold=False):
    path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"
    if not Path(path).exists():
        path = "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf"
    if not Path(path).exists():
        path = "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf"
    return ImageFont.truetype(path, size)


def main():
    w, h = 1200, 1800
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    title = font(34, True); body = font(22); small = font(19); label = font(18, True)

    def box(x, y, ww, hh, text, fill, stroke, white=False):
        d.rounded_rectangle((x, y, x+ww, y+hh), radius=18, fill=fill, outline=stroke, width=4)
        lines = text.split("\n")
        bb = d.multiline_textbbox((0, 0), text, font=body, spacing=8, align="center")
        d.multiline_text((x+ww/2, y+hh/2-(bb[3]-bb[1])/2), text, font=body, fill="white" if white else INK, anchor="ma", align="center", spacing=8)
        return (x, y, ww, hh)

    def arrow(x1, y1, x2, y2, color=GRAY, text=None):
        d.line((x1, y1, x2, y2), fill=color, width=5)
        d.polygon([(x2, y2), (x2-14, y2-24), (x2+14, y2-24)], fill=color)
        if text: d.text(((x1+x2)//2+12, (y1+y2)//2), text, font=small, fill=GRAY)

    d.text((w/2, 45), "Problem-solving algorithm and question progression", font=title, fill=INK, anchor="ma")
    start = box(300, 110, 600, 80, "Start: define drying problem", BLUE, BLUE, True)
    inp = box(190, 270, 820, 100, "Read drying-air data, material properties, geometry,\nand initial temperature/moisture", PALE_GRAY, GRAY)
    prep = box(240, 450, 720, 100, "Preprocess data and initialize radial grid\n(axis r = 0, surface r = R)", PALE_GRAY, GRAY)
    q1 = box(240, 630, 720, 115, "Q1: coupled heat–moisture model\nfixed geometry; validate T(r,t), C(r,t)", PALE_BLUE, BLUE)
    q2 = box(240, 825, 720, 115, "Q2: fixed-radius drying dynamics\nprofiles, response, diffusivity", PALE_BLUE, BLUE)
    q3 = box(240, 1020, 720, 115, "Q3: global maximum Cmax(t)\nand termination tracking", PALE_BLUE, BLUE)
    arrow(600, 190, 600, 270, BLUE); arrow(600, 370, 600, 450); arrow(600, 550, 600, 630); arrow(600, 745, 600, 825, BLUE); arrow(600, 940, 600, 1020, BLUE)
    diamond = [(460, 1270), (600, 1190), (740, 1270), (600, 1350)]
    d.polygon(diamond, fill="white", outline=GRAY); d.line(diamond+[diamond[0]], fill=GRAY, width=4)
    d.multiline_text((600, 1270), "Cmax ≤ 0.15?", font=body, fill=INK, anchor="mm", align="center")
    arrow(600, 1135, 600, 1190, BLUE)
    again = box(20, 1215, 300, 100, "No: advance time\nand repeat Q3", PALE_GRAY, GRAY)
    arrow(460, 1270, 320, 1270, GRAY, "No")
    arrow(170, 1215, 230, 1135, GRAY, "repeat")
    record = box(240, 1435, 720, 100, "Yes: record fixed-radius termination time\nand boundary sensitivity", "white", BLUE)
    arrow(600, 1350, 600, 1435, BLUE, "Yes")
    q4 = box(240, 1605, 720, 115, "Q4: introduce moving radius R(t)\nmaterial-coordinate transport and A–D comparison", PALE_ORANGE, ORANGE)
    arrow(600, 1535, 600, 1605, ORANGE)
    im.save(OUT.with_suffix(".png"), dpi=(300, 300), optimize=True)
    im.save(OUT.with_suffix(".pdf"), "PDF", resolution=300)
    print(OUT.with_suffix(".png")); print(OUT.with_suffix(".pdf"))


if __name__ == "__main__":
    main()
