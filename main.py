#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws one invented passport spread for the Republic of Kalendra — a
windswept North Atlantic island republic — as a single image at
/output/entry.png. Left page: the data page (portrait, bilingual
Kalendri/English fields, machine-readable zone with real ICAO check
digits). Right page: visas and a coherent travel history of arrival and
departure stamps, plus the telling paperwork detail: a red condition
stamp restricting the bearer to the outer isles, and an isle fee stamp.

Every date is consistent: the passport is issued 14 MAR 2023, expires
14 MAR 2033, and every stamp falls after the date of issue, in
chronological order, each departure followed by its arrival.

Runs with no network. Output is a PNG of at most 1024x1024 pixels and
at most 1 MiB (it re-encodes as JPEG if the PNG ever runs over).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
FONTS = ASSETS / "fonts"

W, H = 1024, 724

# Palette -----------------------------------------------------------------
PAPER = (246, 241, 227)
PAPER_EDGE = (232, 224, 203)
INK = (31, 42, 55)
INK_SOFT = (74, 84, 96)
RULE = (169, 155, 122)
SLATE = (43, 53, 66)
NAVY = (31, 58, 92)
BURGUNDY = (122, 46, 58)
GREEN = (47, 93, 58)
PURPLE = (74, 58, 107)
RED = (163, 51, 39)
GOLD = (146, 110, 52)

# Holder and document -------------------------------------------------------
COUNTRY = "REPUBLIC OF KALENDRA"
PASSPORT_NO = "KL4829137"
SURNAME = "VOSS"
GIVEN = "MARA ELIN"
NATIONALITY = "KALENDRIAN"
DOB = "12 JUN 1984"
DOB_MRZ = "840612"
BIRTHPLACE = "PORT LIORA"
SEX = "F"
ISSUE = "14 MAR 2023"
EXPIRY = "14 MAR 2033"
EXPIRY_MRZ = "330314"
AUTHORITY = "PASSPORT OFFICE — PORT LIORA"
PERSONAL_NO = "VOSS840612KAL<"


# ICAO 9303 check digits ----------------------------------------------------
def mrz_check(text: str) -> str:
    """ICAO check digit: A=10 .. Z=35, '<'=0, weights 7,3,1."""
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(text):
        if ch == "<":
            value = 0
        elif ch.isdigit():
            value = int(ch)
        else:
            value = ord(ch) - ord("A") + 10
        total += value * weights[i % 3]
    return str(total % 10)


def mrz_lines() -> tuple[str, str]:
    """Two 44-character TD3 machine-readable lines."""
    name_field = (SURNAME + "<<" + GIVEN.replace(" ", "<")).ljust(39, "<")
    line1 = ("P<" + "KAL" + name_field)[:44]
    doc_check = mrz_check(PASSPORT_NO)
    dob_check = mrz_check(DOB_MRZ)
    exp_check = mrz_check(EXPIRY_MRZ)
    pers_check = mrz_check(PERSONAL_NO)
    body = (
        PASSPORT_NO + doc_check + "KAL" + DOB_MRZ + dob_check + SEX
        + EXPIRY_MRZ + exp_check + PERSONAL_NO + pers_check
    )
    line2 = (body + mrz_check(body))[:44]
    assert len(line1) == 44 and len(line2) == 44
    return line1, line2


# Fonts ---------------------------------------------------------------------
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a bundled font, falling back to the system copy."""
    for path in (FONTS / name, Path("/usr/share/fonts/truetype/dejavu") / name):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


SERIF_B = lambda s: font("DejaVuSerif-Bold.ttf", s)
SANS = lambda s: font("DejaVuSans.ttf", s)
SANS_B = lambda s: font("DejaVuSans-Bold.ttf", s)
MONO = lambda s: font("DejaVuSansMono.ttf", s)


def tracked_width(fnt: ImageFont.FreeTypeFont, text: str, tracking: int) -> int:
    return sum(fnt.getlength(ch) for ch in text) + tracking * max(len(text) - 1, 0)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    cx: float,
    y: float,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill,
    tracking: int = 1,
) -> None:
    """Draw text centred on cx with letter tracking."""
    total = tracked_width(fnt, text, tracking)
    x = cx - total / 2
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + tracking


def draw_field(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    value: str,
    value_size: int = 13,
) -> int:
    """One data field: small bilingual label above a bold value. Returns next y."""
    draw.text((x, y), label, font=SANS(8), fill=INK_SOFT)
    draw.text((x, y + 11), value, font=SANS_B(value_size), fill=INK)
    return y + 30


# Stamps ----------------------------------------------------------------------
def make_stamp(lines, color, w: int = 208, h: int = 56, size: int = 12) -> Image.Image:
    """A rectangular ink stamp on its own transparent layer."""
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ink = color + (205,)
    d.rounded_rectangle([2, 2, w - 3, h - 3], radius=6, outline=ink, width=2)
    d.rounded_rectangle([6, 6, w - 7, h - 7], radius=4, outline=ink, width=1)
    n = len(lines)
    for i, line in enumerate(lines):
        fnt = SANS_B(size) if i == 0 else SANS(size - 1)
        d.text(
            (w / 2, 8 + i * (h - 16) / max(n, 1) + (size / 2)),
            line,
            font=fnt,
            fill=ink,
            anchor="mm",
        )
    return layer


def paste_stamp(base: Image.Image, stamp: Image.Image, cx: int, cy: int, angle: float) -> None:
    rotated = stamp.rotate(angle, expand=True, resample=Image.BICUBIC)
    base.paste(rotated, (int(cx - rotated.width / 2), int(cy - rotated.height / 2)), rotated)


def draw_emblem(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    """The Kalendran arms: a compass star over three waves, in a ring."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=NAVY, width=2)
    draw.ellipse([cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4], outline=NAVY, width=1)
    for k in range(8):
        ang = k * 3.14159 / 4
        long = r - 6 if k % 2 == 0 else r - 12
        x1 = cx + long * 0.45 * _cos(ang)
        y1 = cy + long * 0.45 * _sin(ang)
        x2 = cx + long * _cos(ang)
        y2 = cy + long * _sin(ang)
        draw.line([x1, y1, x2, y2], fill=NAVY, width=2)
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=NAVY)
    for j, wy in enumerate((cy + r - 12, cy + r - 7)):
        draw.arc(
            [cx - r + 8, wy - 4, cx + r - 8, wy + 4],
            start=200,
            end=340,
            fill=NAVY,
            width=1,
        )


def _cos(a: float) -> float:
    import math

    return math.cos(a)


def _sin(a: float) -> float:
    import math

    return math.sin(a)


def draw_signature(draw: ImageDraw.ImageDraw, x: int, y: int, w: int) -> None:
    """A handwritten signature squiggle in dark blue ink."""
    import math

    pts = []
    for i in range(0, w, 2):
        t = i / w
        yy = y + 6 * math.sin(t * 9.0) * (1 - t * 0.4) + 4 * math.sin(t * 23.0)
        pts.append((x + i, yy))
    draw.line(pts, fill=(28, 48, 92), width=2)
    draw.line([(x + w * 0.55, y + 10), (x + w * 0.8, y - 6)], fill=(28, 48, 92), width=1)


def guilloche(draw: ImageDraw.ImageDraw, box, color=(120, 130, 150, 14)) -> None:
    """Faint concentric arcs, like a passport's security print."""
    x0, y0, x1, y1 = box
    for r in range(40, 420, 26):
        draw.arc([x0 - r, y0 - r, x0 + r, y0 + r], start=300, end=30, fill=color, width=1)
        draw.arc([x1 - r, y1 - r, x1 + r, y1 + r], start=120, end=210, fill=color, width=1)


# Pages -----------------------------------------------------------------------
def draw_data_page(page: Image.Image, portrait: Image.Image) -> None:
    d = ImageDraw.Draw(page, "RGBA")
    Wp, Hp = page.size
    guilloche(d, (0, 0, Wp, Hp))

    # Header ----------------------------------------------------------------
    draw_emblem(d, 50, 50, 20)
    draw_tracked(d, 274, 26, COUNTRY, SERIF_B(23), INK, tracking=2)
    draw_tracked(
        d, 274, 58, "PASSPORT  ·  PASSEPORT  ·  KALENDRI PASS",
        SANS(9), INK_SOFT, tracking=1,
    )
    d.line([(28, 78), (Wp - 28, 78)], fill=RULE, width=1)
    d.line([(28, 81), (Wp - 28, 81)], fill=RULE, width=1)

    # Portrait --------------------------------------------------------------
    px, py, pw, ph = 28, 100, 150, 200
    page.paste(portrait.resize((pw, ph), Image.LANCZOS), (px, py))
    d.rectangle([px, py, px + pw, py + ph], outline=INK, width=2)
    draw_signature(d, px + 4, py + ph + 22, pw - 8)
    d.line([(px, py + ph + 34), (px + pw, py + ph + 34)], fill=INK_SOFT, width=1)
    d.text((px, py + ph + 38), "SIGNATURE OF BEARER", font=SANS(7), fill=INK_SOFT)

    # Data fields -----------------------------------------------------------
    fx = px + pw + 20
    fy = 100
    d.text((fx, fy), "No.  " + PASSPORT_NO, font=SANS_B(14), fill=INK)
    fy += 26
    fy = draw_field(d, fx, fy, "TYPE / SLAG", "P", 13)
    fy = draw_field(d, fx, fy, "SUKUNIMI · SURNAME", SURNAME, 14)
    fy = draw_field(d, fx, fy, "ETUNIMI · GIVEN NAMES", GIVEN, 14)
    fy = draw_field(d, fx, fy, "KANSA · NATIONALITY", NATIONALITY, 13)
    fy = draw_field(d, fx, fy, "SYNTYMÄPÄIVÄ · DATE OF BIRTH", DOB, 13)
    fy = draw_field(d, fx, fy, "SYNTYMÄPAIKKA · PLACE OF BIRTH", BIRTHPLACE, 13)
    fy = draw_field(d, fx, fy, "SUKUPUOLI · SEX", SEX, 13)
    fy = draw_field(d, fx, fy, "MYÖNTÄMISPÄIVÄ · DATE OF ISSUE", ISSUE, 13)
    fy = draw_field(d, fx, fy, "VOIMASSAOLO · DATE OF EXPIRY", EXPIRY, 13)
    fy = draw_field(d, fx, fy, "MYÖNTÄJÄ · AUTHORITY", AUTHORITY, 11)

    # Machine-readable zone --------------------------------------------------
    line1, line2 = mrz_lines()
    mz_y = Hp - 62
    d.rectangle([20, mz_y - 8, Wp - 20, mz_y + 34], fill=(238, 232, 214))
    d.text((28, mz_y), line1, font=MONO(13), fill=INK)
    d.text((28, mz_y + 18), line2, font=MONO(13), fill=INK)


# Right page: visas and stamps. Every stamp is dated after the 14 MAR 2023
# issue date, in chronological order, each departure followed by its arrival.
STAMP_SET = [
    (["DEPARTURE", "PORT LIORA", "02 APR 2023"], NAVY, -3),
    (["ARRIVAL", "VEYPORT · TARNOVIA", "03 APR 2023"], BURGUNDY, 2),
    (["DEPARTURE", "VEYPORT", "18 APR 2023"], BURGUNDY, -2),
    (["ARRIVAL", "PORT LIORA", "19 APR 2023"], NAVY, 3),
    (["DEPARTURE", "PORT LIORA", "11 SEP 2023"], NAVY, 2),
    (["ARRIVAL", "MERROW", "12 SEP 2023"], GREEN, -3),
    (["DEPARTURE", "MERROW", "26 SEP 2023"], GREEN, 3),
    (["ARRIVAL", "PORT LIORA", "27 SEP 2023"], NAVY, -2),
    (["DEPARTURE", "PORT LIORA", "05 MAY 2024"], NAVY, 2),
    (["ARRIVAL", "KESSWICK · VEYMARK", "06 MAY 2024"], PURPLE, -2),
    (["DEPARTURE", "KESSWICK", "20 MAY 2024"], PURPLE, 3),
    (["ARRIVAL", "PORT LIORA", "21 MAY 2024"], NAVY, -3),
]


def draw_visa_page(page: Image.Image) -> None:
    d = ImageDraw.Draw(page, "RGBA")
    Wp, Hp = page.size
    guilloche(d, (0, 0, Wp, Hp))

    draw_tracked(d, Wp / 2, 24, "VISAS", SERIF_B(20), INK, tracking=4)
    d.text((Wp - 34, 26), "12", font=SANS_B(13), fill=INK_SOFT)
    d.line([(28, 52), (Wp - 28, 52)], fill=RULE, width=1)

    # Tarnovia visitor visa ---------------------------------------------------
    vx, vy, vw, vh = 28, 66, Wp - 56, 92
    d.rectangle([vx, vy, vx + vw, vy + vh], outline=NAVY, width=2)
    d.rectangle([vx + 4, vy + 4, vx + vw - 4, vy + vh - 4], outline=NAVY, width=1)
    d.text((vx + 14, vy + 10), "TARNOVIA — VISITOR VISA", font=SANS_B(14), fill=NAVY)
    d.text((vx + 14, vy + 34), "90 DAYS  ·  SINGLE ENTRY  ·  FEE 40 TV — PAID",
           font=SANS(11), fill=INK)
    d.text((vx + 14, vy + 54), "ISSUED 28 MAR 2023 — VEYPORT  ·  VALID TO 26 JUN 2023",
           font=SANS(11), fill=INK)
    d.text((vx + vw - 14, vy + 10), "No. TV-22914", font=SANS_B(10), fill=NAVY,
           anchor="ra")

    # Travel stamps, two columns ----------------------------------------------
    cols = [28 + 104, Wp - 28 - 104]
    row_y = 178
    row_h = 58
    for i, (lines, color, angle) in enumerate(STAMP_SET):
        col = i % 2
        row = i // 2
        stamp = make_stamp(lines, color)
        paste_stamp(page, stamp, cols[col], row_y + row * row_h + 28, angle)

    # The telling detail: the outer-isles condition, in red --------------------
    cy = row_y + 6 * row_h + 14
    cond = make_stamp(
        ["OUTER ISLES ONLY", "MAINLAND PERMIT REQUIRED",
         "KALENDRA BORDER SERVICE"],
        RED, w=300, h=64, size=13,
    )
    paste_stamp(page, cond, Wp / 2, cy + 32, -2)

    # Isle fee stamp ------------------------------------------------------------
    fee = make_stamp(["ISLE FEE 12 KR — PAID", "02 APR 2023"], GREEN,
                     w=190, h=48, size=11)
    paste_stamp(page, fee, Wp - 28 - 95, cy + 92, 4)


# Assembly ----------------------------------------------------------------------
def build() -> Path:
    out_dir = Path(os.environ.get("OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    portrait_path = ASSETS / "portrait.jpg"
    portrait = Image.open(portrait_path).convert("RGB")

    canvas = Image.new("RGB", (W, H), SLATE)
    d = ImageDraw.Draw(canvas, "RGBA")
    # Soft shadow under the spread.
    d.rounded_rectangle([30, 36, 994, 700], radius=6, fill=(18, 24, 32))
    left = Image.new("RGB", (460, 664), PAPER)
    right = Image.new("RGB", (460, 664), PAPER)
    draw_data_page(left, portrait)
    draw_visa_page(right)
    canvas.paste(left, (36, 30))
    canvas.paste(right, (528, 30))
    # Gutter shadow between the pages.
    gutter = Image.new("RGBA", (32, 664), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gutter)
    for i in range(16):
        gd.rectangle([i, 0, i + 1, 664], fill=(0, 0, 0, 26 - i))
        gd.rectangle([31 - i, 0, 32 - i, 664], fill=(0, 0, 0, 26 - i))
    canvas.paste(gutter, (496, 30), gutter)

    out = out_dir / "entry.png"
    canvas.save(out, format="PNG")
    if out.stat().st_size > 1_048_576:
        canvas.save(out, format="JPEG", quality=82)
    return out


def main() -> int:
    out = build()
    size = out.stat().st_size
    with Image.open(out) as im:
        print(f"wrote {out} {im.size[0]}x{im.size[1]} {size} bytes")
    if size > 1_048_576:
        print("ERROR: entry over 1 MiB", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
