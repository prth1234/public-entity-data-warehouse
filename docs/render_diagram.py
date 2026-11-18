"""Render a crisp, accurate architecture & results overview PNG in docs/pipeline_overview.png."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 2400, 1320
BG = "#F8FAFC"
CARD_BG = "#FFFFFF"
BORDER = "#CBD5E1"
ACCENT = "#1D4ED8"
ACCENT_LIGHT = "#EFF6FF"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#475569"
GREEN_BG = "#ECFDF5"
GREEN_BORDER = "#10B981"
AMBER_BG = "#FFFBEB"
AMBER_BORDER = "#F59E0B"

FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for p in FONT_PATHS:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size, index=1 if (bold and p.endswith(".ttc")) else 0)
            except Exception:
                return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def draw_arrow(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, color: str = "#64748B") -> None:
    draw.line([(x1, y1), (x2, y2)], fill=color, width=4)
    # Arrowhead
    if x2 > x1 and y1 == y2:
        draw.polygon([(x2, y2), (x2 - 16, y2 - 9), (x2 - 16, y2 + 9)], fill=color)
    elif y2 > y1 and x1 == x2:
        draw.polygon([(x2, y2), (x2 - 9, y2 - 16), (x2 + 9, y2 - 16)], fill=color)


def draw_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    step_num: str,
    title: str,
    fill: str = CARD_BG,
    outline: str = BORDER,
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=3)
    # Header pill
    draw.rounded_rectangle((x0 + 20, y0 + 20, x0 + 64, y0 + 64), radius=12, fill=ACCENT)
    f_num = load_font(28, bold=True)
    draw.text((x0 + 34, y0 + 26), step_num, fill="#FFFFFF", font=f_num)
    f_title = load_font(28, bold=True)
    draw.text((x0 + 80, y0 + 26), title, fill=TEXT_DARK, font=f_title)
    draw.line([(x0 + 20, y0 + 80), (x1 - 20, y0 + 80)], fill="#E2E8F0", width=2)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    f_h1 = load_font(42, bold=True)
    f_sub = load_font(23, bold=False)
    f_b = load_font(21, bold=True)
    f_t = load_font(20, bold=False)
    f_sm = load_font(18, bold=False)



    # Card coordinates
    y_top, y_bot = 160, 820
    c1 = (70, y_top, 550, y_bot)
    c2 = (610, y_top, 1090, y_bot)
    c3 = (1150, y_top, 1690, y_bot)
    c4 = (1750, y_top, 2330, y_bot)

    draw_arrow(draw, 550, 480, 606, 480)
    draw_arrow(draw, 1090, 480, 1146, 480)
    draw_arrow(draw, 1690, 480, 1746, 480)

    # --- Card 1: Catalog Discovery ---
    draw_card(draw, c1, "1", "Catalog Discovery")
    y = y_top + 105
    draw.text((95, y), "Surepass.io & Perfios.ai Sitemaps", fill=ACCENT, font=f_b); y += 40
    draw.text((95, y), "612 product & solution pages", fill=TEXT_DARK, font=load_font(26, bold=True)); y += 42
    draw.text((95, y), "(URL/keyword classified; 18-row HTTP 200 check)", fill=TEXT_MUTED, font=f_sm); y += 45
    for line in [
        "• 316  Proprietary / SaaS (excluded)",
        "• 141  Personal KYC data (excluded)",
        "•  79  Consent-gated / credit (excluded)",
        "•  76  Entity-level public candidates",
    ]:
        draw.text((95, y), line, fill=TEXT_DARK, font=f_t); y += 38

    y += 20
    draw.rounded_rectangle((95, y, 525, y + 145), radius=12, fill=AMBER_BG, outline=AMBER_BORDER, width=2)
    draw.text((112, y + 16), "Vendor Access Finding:", fill="#92400E", font=f_b)
    draw.text((112, y + 50), "• Surepass sandbox: approval-gated", fill=TEXT_DARK, font=f_sm)
    draw.text((112, y + 78), "• Perfios Hub: behind enterprise login", fill=TEXT_DARK, font=f_sm)
    draw.text((112, y + 106), "• Prototype uses open upstreams only", fill=TEXT_DARK, font=f_sm)

    # --- Card 2: Scoring & Selection ---
    draw_card(draw, c2, "2", "Scoring & Selection")
    y = y_top + 105
    draw.text((635, y), "Scored 76 Survivors (1–5 Scale):", fill=ACCENT, font=f_b); y += 42
    for line in [
        "• Authoritative public upstream exists",
        "• Bulk download or open API access",
        "• Clear commercial licence (GODL/CC0/MIT)",
        "• Entity richness (zero individual PII)",
        "• Cross-source joinability (CIN, Pincode, State)",
    ]:
        draw.text((635, y), line, fill=TEXT_DARK, font=f_t); y += 38

    y += 18
    draw.rounded_rectangle((635, y, 1065, y + 235), radius=12, fill=ACCENT_LIGHT, outline="#93C5FD", width=2)
    draw.text((652, y + 16), "Selected Open Upstreams:", fill=ACCENT, font=f_b)
    for idx, line in enumerate([
        "1. RBI IFSC (razorpay/ifsc MIT mirror)",
        "2. MCA Master (data.gov.in GODL API)",
        "3. GLEIF LEI (api.gleif.org CC0 API)",
        "+ India Post Pincode (MIT mirror)",
        "Gap: GSTIN (captcha/GSP-gated ->",
        "     Mod-36 validator + HSN/SAC ref)",
    ]):
        draw.text((652, y + 52 + idx * 29), line, fill=TEXT_DARK, font=f_sm)

    # --- Card 3: Legitimacy & Mode Audit ---
    draw_card(draw, c3, "3", "Legitimacy & Mode Audit")
    y = y_top + 105
    draw.text((1175, y), "Pre-Fetch Compliance Gates:", fill=ACCENT, font=f_b); y += 38
    for line in [
        "• robots.txt fail-closed checker (goldencopy 403 blocked)",
        "• Licence & DPDP Act 2023 audit (entity-level only)",
        "• Immutable raw landing: SHA-256 + .meta.json",
    ]:
        draw.text((1175, y), line, fill=TEXT_DARK, font=f_sm); y += 32

    y += 16
    # Clean light-mode audit table
    cols_x = [1175, 1300, 1465, 1670]
    row_h = 54
    headers = ["Source", "Upstream / Licence", "Ingest Mode"]
    draw.rectangle((1175, y, 1670, y + 42), fill="#E2E8F0")
    draw.text((1185, y + 10), headers[0], fill=TEXT_DARK, font=f_sm)
    draw.text((1305, y + 10), headers[1], fill=TEXT_DARK, font=f_sm)
    draw.text((1475, y + 10), headers[2], fill=TEXT_DARK, font=f_sm)
    y += 42

    table_rows = [
        ("IFSC", "RBI / MIT mirror", "Bulk CSV + JSON"),
        ("MCA", "MCA / GODL API", "Paged API + ckpt"),
        ("GLEIF LEI", "GLEIF / CC0 API", "Cursor (10K cap)"),
        ("Pincode", "India Post / MIT", "Bulk CSV mirror"),
        ("GSTIN", "GSTN (Captcha)", "Gap + Mod-36"),
    ]
    for i, (s, u, m) in enumerate(table_rows):
        bg_r = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
        draw.rectangle((1175, y, 1670, y + row_h), fill=bg_r, outline="#E2E8F0", width=1)
        draw.text((1185, y + 15), s, fill=TEXT_DARK, font=load_font(17, bold=True))
        draw.text((1305, y + 15), u, fill=TEXT_DARK, font=load_font(17))
        draw.text((1475, y + 15), m, fill=TEXT_DARK, font=load_font(17))
        y += row_h

    # --- Card 4: DuckDB Warehouse & Verified Results ---
    draw_card(draw, c4, "4", "DuckDB Warehouse & Results", fill=GREEN_BG, outline=GREEN_BORDER)
    y = y_top + 105
    draw.text((1775, y), "warehouse/zintrl.duckdb (SCD Type 2)", fill="#065F46", font=f_b); y += 44
    results = [
        ("1. 183,214", "RBI bank branches (dim_bank_branch)"),
        ("   26,164", "pincodes inferred_from_district (approx.)"),
        ("2. 8,408", "MCA company CINs (first 10K; 1,592 LLPs excl.)"),
        ("3. 10,000", "Indian GLEIF LEIs (of 411,277; API 10K cap)"),
        ("4. 19,300", "unique pincodes (dim_pincode)"),
        ("5. 649", "CBIC HSN/SAC tariff codes (non-entity ref)"),
    ]
    for num, desc in results:
        draw.text((1775, y), num, fill="#065F46", font=load_font(21, bold=True))
        draw.text((1900, y), desc, fill=TEXT_DARK, font=load_font(18))
        y += 42

    y += 18
    draw.rounded_rectangle((1775, y, 2305, y + 115), radius=12, fill="#FFFFFF", outline=GREEN_BORDER, width=2)
    draw.text((1795, y + 16), "Validation & Tests:", fill="#065F46", font=f_b)
    draw.text((1795, y + 48), "• 8/8 pytest tests passing (idempotent SCD2)", fill=TEXT_DARK, font=f_sm)
    draw.text((1795, y + 76), "• 91/91 GLEIF GSTINs pass Mod-36 checksum", fill=TEXT_DARK, font=f_sm)

    # --- Bottom Connected Section: Zintrl Use Cases ---
    draw_arrow(draw, 2040, 820, 2040, 895, color="#10B981")
    draw.rounded_rectangle((70, 900, 2330, 1250), radius=18, fill=CARD_BG, outline=BORDER, width=3)
    draw.text((100, 925), "Zintrl Downstream Use Cases & Commercial Value", fill=ACCENT, font=load_font(26, bold=True))
    draw.line([(100, 968), (2300, 968)], fill="#E2E8F0", width=2)

    use_cases = [
        ("1. KYB Vendor Onboarding", "Verify company CIN, status, RoC, and paid-up capital."),
        ("2. Payout & Branch Validation", "Validate IFSC, MICR, NEFT/RTGS/UPI rails across 183K+ branches."),
        ("3. Cross-Source Entity Linking", "Join MCA CINs, GLEIF LEIs, pincodes, and state codes in DuckDB."),
        ("4. Cost & Compliance Control", "Replace paid vendor APIs for open GODL/CC0/MIT data; isolate GSP gaps."),
    ]
    ux = 100
    for title_uc, desc_uc in use_cases:
        draw.rounded_rectangle((ux, 995, ux + 525, 1215), radius=12, fill=BG, outline="#CBD5E1", width=2)
        draw.text((ux + 20, 1018), title_uc, fill=TEXT_DARK, font=f_b)
        # Wrap desc_uc manually cleanly
        words = desc_uc.split()
        line1, line2 = [], []
        for w in words:
            if len(" ".join(line1 + [w])) <= 42:
                line1.append(w)
            else:
                line2.append(w)
        draw.text((ux + 20, 1065), " ".join(line1), fill=TEXT_MUTED, font=f_t)
        if line2:
            draw.text((ux + 20, 1098), " ".join(line2), fill=TEXT_MUTED, font=f_t)
        ux += 555

    out_path = Path("docs/pipeline_overview.png")
    img.save(out_path)
    print(f"Saved {out_path} ({W}x{H})")


if __name__ == "__main__":
    main()
