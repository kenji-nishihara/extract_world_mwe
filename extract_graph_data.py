#!/usr/bin/env python3
from __future__ import annotations

"""Extract bar-height based MWe values from graph-heavy PDFs.

Default mode:
- Automatically extract all countries/elements in 2025-2050.
- Uses bar-height estimation only (`source=bar_height`).
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|21\d{2})\b")
COUNTRY_CANDIDATE_RE = re.compile(r"^[A-Z][A-Za-z .\-']{2,}$")

COUNTRY_STOPWORDS = {
    "world nuclear outlook",
    "reference case",
    "capacity",
    "generation",
    "government target",
    "year",
    "source",
    "figure",
    "mwe",
}

MERGE_MARKER_PREFIXES = ("<<<<<<<", "=======", ">>>>>>>")


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def is_merge_marker_line(line: str) -> bool:
    stripped = line.strip()
    return any(stripped.startswith(prefix) for prefix in MERGE_MARKER_PREFIXES)


def parse_numeric(token: str) -> float | None:
    cleaned = token.replace(",", "").replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def is_country_candidate(line: str) -> bool:
    lower = line.lower().strip()
    if lower in COUNTRY_STOPWORDS:
        return False
    if any(ch.isdigit() for ch in line):
        return False
    if len(line) > 40 or line.count(" ") > 3:
        return False
    return bool(COUNTRY_CANDIDATE_RE.match(line))


def infer_country_for_lines(lines: list[str], fallback: str = "Unknown") -> str:
    for line in lines:
        if is_country_candidate(line):
            return line
    return fallback


def _pick_y(rect: dict, key_top: bool) -> float:
    if key_top:
        for k in ("top", "y0"):
            if k in rect and rect[k] is not None:
                return float(rect[k])
    else:
        for k in ("bottom", "y1"):
            if k in rect and rect[k] is not None:
                return float(rect[k])
    return 0.0


def estimate_bar_values_from_page(page_obj: dict, year_min: int, year_max: int) -> list[dict[str, str]]:
    """Estimate MWe values from bar heights using y-axis ticks and bar rectangles."""
    words = page_obj.get("words", [])
    rects = page_obj.get("rects", [])
    if not words or not rects:
        return []

    year_words: list[tuple[int, float]] = []
    for word in words:
        txt = str(word.get("text", "")).strip()
        if not YEAR_RE.fullmatch(txt):
            continue
        year = int(txt)
        if year_min <= year <= year_max:
            x0 = float(word.get("x0", 0.0))
            x1 = float(word.get("x1", x0))
            year_words.append((year, (x0 + x1) / 2))
    if not year_words:
        return []

    min_year_x = min(x for _, x in year_words)

    ticks: list[tuple[float, float]] = []
    for word in words:
        txt = str(word.get("text", "")).strip().replace(",", "")
        val = parse_numeric(txt)
        if val is None:
            continue
        if 1900 <= val <= 2100:
            continue
        x0 = float(word.get("x0", 0.0))
        x1 = float(word.get("x1", x0))
        xc = (x0 + x1) / 2
        if xc >= min_year_x - 8:
            continue
        top = float(word.get("top", word.get("y0", 0.0)))
        bottom = float(word.get("bottom", word.get("y1", top)))
        yc = (top + bottom) / 2
        ticks.append((yc, val))

    if len(ticks) < 2:
        return []

    ticks.sort(key=lambda t: t[1])
    y_low, v_low = ticks[0]
    y_high, v_high = ticks[-1]
    if abs(y_high - y_low) < 1e-6 or abs(v_high - v_low) < 1e-6:
        return []

    def y_to_value(y: float) -> float:
        ratio = (y - y_low) / (y_high - y_low)
        return v_low + ratio * (v_high - v_low)

    bars: list[tuple[float, float]] = []
    for rect in rects:
        x0 = float(rect.get("x0", 0.0))
        x1 = float(rect.get("x1", x0))
        y_top = _pick_y(rect, key_top=True)
        y_bottom = _pick_y(rect, key_top=False)
        width = abs(x1 - x0)
        height = abs(y_bottom - y_top)
        if width < 1.0 or height < 4.0:
            continue
        xc = (x0 + x1) / 2
        if xc < min_year_x - 5:
            continue
        bars.append((xc, min(y_top, y_bottom)))

    if not bars:
        return []

    grouped: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for year, x_year in year_words:
        near = [(xc, y_top) for (xc, y_top) in bars if abs(xc - x_year) <= 30]
        if near:
            near.sort(key=lambda item: item[0])
            grouped[year] = near

    out: list[dict[str, str]] = []
    for year in sorted(grouped):
        for idx, (_, y_top) in enumerate(grouped[year], start=1):
            out.append(
                {
                    "year": str(year),
                    "element": f"element_{idx}",
                    "value": str(round(y_to_value(y_top), 2)).rstrip("0").rstrip("."),
                    "source": "bar_height",
                }
            )
    return out


def load_pdf_content(pdf_path: Path) -> list[dict]:
    """Load per-page lines/words/rects using pdfplumber (required for bar-height mode)."""
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: pdfplumber is required for bar-height extraction.\n"
            "Install in the same interpreter:\n"
            "- pip install pdfplumber\n\n"
            f"Current interpreter: {sys.executable}\n"
            "Tip (Windows): use `py -m pip install pdfplumber` and run with `py extract_graph_data.py ...`"
        ) from exc

    pages: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            page_lines = []
            for raw_line in text.splitlines():
                normalized = normalize_line(raw_line)
                if normalized and not is_merge_marker_line(normalized):
                    page_lines.append(normalized)
            pages.append(
                {
                    "page": str(page_index),
                    "lines": page_lines,
                    "words": page.extract_words() or [],
                    "rects": page.rects or [],
                }
            )
    return pages


def extract_all_countries_elements(pages: list[dict], year_min: int, year_max: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for page in pages:
        page_id = page["page"]
        country = infer_country_for_lines(page.get("lines", []))
        for row in estimate_bar_values_from_page(page, year_min=year_min, year_max=year_max):
            rows.append(
                {
                    "country": country,
                    "page": page_id,
                    "year": row["year"],
                    "element": row["element"],
                    "value": row["value"],
                    "line": "",
                    "source": "bar_height",
                    "unit": "MWe",
                }
            )
    return rows


def build_country_series_table(
    bar_rows: list[dict[str, str]],
    country: str,
    series: list[str],
    year_min: int,
    year_max: int,
) -> list[dict[str, str]]:
    target = country.lower()
    matched = [r for r in bar_rows if r["country"].lower() == target]

    by_year: dict[int, dict[int, str]] = defaultdict(dict)
    for row in matched:
        year = int(row["year"])
        if not (year_min <= year <= year_max):
            continue
        element = row["element"]
        if not element.startswith("element_"):
            continue
        try:
            idx = int(element.split("_", 1)[1]) - 1
        except ValueError:
            continue
        by_year[year][idx] = row["value"]

    table: list[dict[str, str]] = []
    for year in sorted(by_year):
        out_row: dict[str, str] = {"country": country, "year": str(year)}
        for idx, series_name in enumerate(series):
            out_row[series_name] = by_year[year].get(idx, "")
        table.append(out_row)
    return table


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract MWe values from graph-based PDF bars (bar-height only).")
    parser.add_argument("pdf", type=Path, help="Input PDF path")
    parser.add_argument("-o", "--output", type=Path, default=Path("extracted_all_countries_long.csv"))
    parser.add_argument("-c", "--country", "-country", dest="country")
    parser.add_argument("-s", "--series", "-series", dest="series")
    parser.add_argument("-y", "--year-min", "-year-min", dest="year_min", type=int, default=2025)
    parser.add_argument("-Y", "--year-max", "-year-max", dest="year_max", type=int, default=2050)
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    pages = load_pdf_content(args.pdf)
    rows = extract_all_countries_elements(pages, args.year_min, args.year_max)

    if args.country and args.series:
        series = [s.strip() for s in args.series.split(",") if s.strip()]
        if not series:
            raise SystemExit("No valid series names were provided in --series")
        table_rows = build_country_series_table(rows, args.country, series, args.year_min, args.year_max)
        write_csv(args.output, table_rows, ["country", "year", *series])
        print(f"Extracted {len(table_rows)} rows for {args.country} ({args.year_min}-{args.year_max}) -> {args.output}")
        return

    if args.country or args.series:
        raise SystemExit("Use --country and --series together, or neither.")

    write_csv(args.output, rows, ["country", "page", "year", "element", "value", "unit", "source", "line"])
    print(f"Auto extracted {len(rows)} element rows ({args.year_min}-{args.year_max}) -> {args.output}")


if __name__ == "__main__":
    main()
