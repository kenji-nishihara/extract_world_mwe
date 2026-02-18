#!/usr/bin/env python3
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
from __future__ import annotations

"""Extract year/value data from graph-heavy PDFs.

Default mode:
- Automatically extract all countries/elements in 2025-2050.
- Uses both text parsing and (when possible) bar-height estimation from PDF shapes.
"""
=======
"""Extract year/value data rows from graph-heavy PDFs.

Default mode:
  - Extract candidate lines containing a year + numeric values.

Country/series mode:
  - Filter to pages mentioning a country name.
  - Parse year rows and map numeric columns to user-provided series names.
  - Export a tidy CSV (year x series values).
"""
from __future__ import annotations
>>>>>>> main

import argparse
import csv
import re
import sys
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
from collections import defaultdict
=======
>>>>>>> main
from pathlib import Path

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|21\d{2})\b")
VALUE_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?")
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
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
=======
>>>>>>> main


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def parse_numeric(token: str) -> float | None:
    cleaned = token.replace(",", "").replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_year_value_row(line: str) -> tuple[int, list[float]] | None:
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
    year_match = YEAR_RE.search(line)
    if not year_match:
        return None
    year = int(year_match.group(1))
    tokens = VALUE_RE.findall(line[year_match.end():])
    values = [v for v in (parse_numeric(t) for t in tokens) if v is not None]
    if not values:
        return None
    return year, values


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
    words = page_obj.get("words", [])
    rects = page_obj.get("rects", [])
    if not words or not rects:
        return []

    year_words: list[tuple[int, float]] = []
    for w in words:
        txt = str(w.get("text", "")).strip()
        if not YEAR_RE.fullmatch(txt):
            continue
        year = int(txt)
        if year_min <= year <= year_max:
            x0 = float(w.get("x0", 0.0))
            x1 = float(w.get("x1", x0))
            year_words.append((year, (x0 + x1) / 2))
    if not year_words:
        return []

    min_year_x = min(x for _, x in year_words)

    ticks: list[tuple[float, float]] = []
    for w in words:
        txt = str(w.get("text", "")).strip().replace(",", "")
        val = parse_numeric(txt)
        if val is None:
            continue
        if 1900 <= val <= 2100:
            continue
        x0 = float(w.get("x0", 0.0))
        x1 = float(w.get("x1", x0))
        xc = (x0 + x1) / 2
        if xc >= min_year_x - 8:
            continue
        top = float(w.get("top", w.get("y0", 0.0)))
        bottom = float(w.get("bottom", w.get("y1", top)))
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

    bars: list[tuple[float, float, float]] = []
    for r in rects:
        x0 = float(r.get("x0", 0.0))
        x1 = float(r.get("x1", x0))
        y_top = _pick_y(r, key_top=True)
        y_bottom = _pick_y(r, key_top=False)
        w = abs(x1 - x0)
        h = abs(y_bottom - y_top)
        if w < 1.0 or h < 4.0:
            continue
        xc = (x0 + x1) / 2
        if xc < min_year_x - 5:
            continue
        bars.append((xc, min(y_top, y_bottom), max(y_top, y_bottom)))

    if not bars:
        return []

    grouped: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for year, xyear in year_words:
        # collect bars near this year label
        near = [(xc, ytop) for (xc, ytop, _) in bars if abs(xc - xyear) <= 30]
        if near:
            near.sort(key=lambda t: t[0])
            grouped[year] = near

    out: list[dict[str, str]] = []
    for year in sorted(grouped):
        for idx, (_, ytop) in enumerate(grouped[year], start=1):
            est = y_to_value(ytop)
            out.append(
                {
                    "year": str(year),
                    "element": f"element_{idx}",
                    "value": str(round(est, 2)).rstrip("0").rstrip("."),
                    "source": "bar_height",
                }
            )
    return out


def load_pdf_content(pdf_path: Path) -> tuple[list[dict[str, str]], list[dict]]:
    lines: list[dict[str, str]] = []
    pages: list[dict] = []
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                page_lines = []
                for raw_line in text.splitlines():
                    normalized = normalize_line(raw_line)
                    if normalized:
                        page_lines.append(normalized)
                        lines.append({"page": str(page_index), "line": normalized})
                pages.append(
                    {
                        "page": str(page_index),
                        "lines": page_lines,
                        "words": page.extract_words() or [],
                        "rects": page.rects or [],
                    }
                )
        return lines, pages
    except ModuleNotFoundError:
        pass

    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependencies: install one of the following in the same Python interpreter\n"
            "- pip install pdfplumber\n"
            "- pip install pypdf\n\n"
            f"Current interpreter: {sys.executable}\n"
            "Tip (Windows): use `py -m pip install pdfplumber` and run with `py extract_graph_data.py ...`"
        ) from exc

    reader = PdfReader(str(pdf_path))
    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        page_lines = []
        for raw_line in text.splitlines():
            normalized = normalize_line(raw_line)
            if normalized:
                page_lines.append(normalized)
                lines.append({"page": str(page_index), "line": normalized})
        pages.append({"page": str(page_index), "lines": page_lines, "words": [], "rects": []})
    return lines, pages


def extract_all_countries_elements(pages: list[dict], year_min: int, year_max: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for page in pages:
        page_id = page["page"]
        country = infer_country_for_lines(page.get("lines", []))

        # 1) Text-based extraction
        for line in page.get("lines", []):
            parsed = parse_year_value_row(line)
            if not parsed:
                continue
            year, values = parsed
            if not (year_min <= year <= year_max):
                continue
            for idx, value in enumerate(values, start=1):
                rows.append(
                    {
                        "country": country,
                        "page": page_id,
                        "year": str(year),
                        "element": f"element_{idx}",
                        "value": str(value).rstrip("0").rstrip("."),
                        "line": line,
                        "source": "text",
                        "unit": "MWe",
                    }
                )

        # 2) Bar-height extraction (adds missing values when bars are vector rectangles)
        bar_rows = estimate_bar_values_from_page(page, year_min=year_min, year_max=year_max)
        for r in bar_rows:
            rows.append(
                {
                    "country": country,
                    "page": page_id,
                    "year": r["year"],
                    "element": r["element"],
                    "value": r["value"],
                    "line": "",
                    "source": r["source"],
                    "unit": "MWe",
                }
            )

=======
    """Parse a text line that contains one year followed by numeric values."""
    year_match = YEAR_RE.search(line)
    if not year_match:
        return None

    year = int(year_match.group(1))
    tail = line[year_match.end():]
    tokens = VALUE_RE.findall(tail)

    values: list[float] = []
    for token in tokens:
        parsed = parse_numeric(token)
        if parsed is not None:
            values.append(parsed)

    if not values:
        return None

    return year, values


def load_pdf_lines(pdf_path: Path) -> list[dict[str, str]]:
    extractor_name = ""
    try:
        import pdfplumber

        extractor_name = "pdfplumber"
    except ModuleNotFoundError as exc:
        try:
            from pypdf import PdfReader

            extractor_name = "pypdf"
        except ModuleNotFoundError:
            raise SystemExit(
                "Missing dependencies: install one of the following in the same Python interpreter\n"
                "- pip install pdfplumber\n"
                "- pip install pypdf\n\n"
                f"Current interpreter: {sys.executable}\n"
                "Tip (Windows): use `py -m pip install pdfplumber` and run with `py extract_graph_data.py ...`"
            ) from exc

    lines: list[dict[str, str]] = []
    if extractor_name == "pdfplumber":
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                for raw_line in text.splitlines():
                    normalized = normalize_line(raw_line)
                    if normalized:
                        lines.append({"page": str(page_index), "line": normalized})
    else:
        reader = PdfReader(str(pdf_path))
        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                normalized = normalize_line(raw_line)
                if normalized:
                    lines.append({"page": str(page_index), "line": normalized})

    return lines


def extract_candidate_rows(pdf_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in load_pdf_lines(pdf_path):
        parsed = parse_year_value_row(entry["line"])
        if not parsed:
            continue
        year, values = parsed
        rows.append(
            {
                "page": entry["page"],
                "year": str(year),
                "values": " | ".join(str(v).rstrip("0").rstrip(".") for v in values),
                "line": entry["line"],
            }
        )
>>>>>>> main
    return rows


def build_country_series_table(
    lines: list[dict[str, str]],
    country: str,
    series: list[str],
    year_min: int,
    year_max: int,
) -> list[dict[str, str]]:
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
=======
    """Build a wide table where each row is one year and each column is a series."""
>>>>>>> main
    country_lower = country.lower()
    candidate_pages = {
        entry["page"] for entry in lines if country_lower in entry["line"].lower()
    }
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
=======

>>>>>>> main
    filtered_lines = [entry for entry in lines if entry["page"] in candidate_pages]

    by_year: dict[int, list[float]] = {}
    for entry in filtered_lines:
        parsed = parse_year_value_row(entry["line"])
        if not parsed:
            continue
        year, values = parsed
        if year < year_min or year > year_max:
            continue
        if year not in by_year or len(values) > len(by_year[year]):
            by_year[year] = values

    table: list[dict[str, str]] = []
    for year in sorted(by_year):
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
        row: dict[str, str] = {"country": country, "year": str(year)}
        values = by_year[year]
        for idx, series_name in enumerate(series):
            row[series_name] = str(values[idx]).rstrip("0").rstrip(".") if idx < len(values) else ""
        table.append(row)
=======
        values = by_year[year]
        row: dict[str, str] = {"country": country, "year": str(year)}
        for idx, series_name in enumerate(series):
            row[series_name] = ""
            if idx < len(values):
                row[series_name] = str(values[idx]).rstrip("0").rstrip(".")
        table.append(row)

>>>>>>> main
    return table


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
    parser = argparse.ArgumentParser(description="Extract year/value data from graph-based PDF reports.")
    parser.add_argument("pdf", type=Path, help="Input PDF path")
    parser.add_argument("-o", "--output", type=Path, default=Path("extracted_all_countries_long.csv"))
    parser.add_argument("-c", "--country", "-country", dest="country")
    parser.add_argument("-s", "--series", "-series", dest="series")
    parser.add_argument("-y", "--year-min", "-year-min", dest="year_min", type=int, default=2025)
    parser.add_argument("-Y", "--year-max", "-year-max", dest="year_max", type=int, default=2050)
=======
    parser = argparse.ArgumentParser(
        description="Extract year/value candidate rows from graph-based PDF reports."
    )
    parser.add_argument("pdf", type=Path, help="Input PDF path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("extracted_graph_rows.csv"),
        help="Output CSV path (default: extracted_graph_rows.csv)",
    )
    parser.add_argument(
        "-c",
        "--country",
        "-country",
        dest="country",
        help="Country name filter (e.g., Argentina)",
    )
    parser.add_argument(
        "-s",
        "--series",
        "-series",
        dest="series",
        help="Comma-separated series names in chart order (e.g., '60 year operation,80 year operation,Government target')",
    )
    parser.add_argument(
        "-y",
        "--year-min",
        "-year-min",
        dest="year_min",
        type=int,
        default=2025,
        help="Minimum year (default: 2025)",
    )
    parser.add_argument(
        "-Y",
        "--year-max",
        "-year-max",
        dest="year_max",
        type=int,
        default=2050,
        help="Maximum year (default: 2050)",
    )

>>>>>>> main
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
    lines, pages = load_pdf_content(args.pdf)

=======
>>>>>>> main
    if args.country and args.series:
        series = [s.strip() for s in args.series.split(",") if s.strip()]
        if not series:
            raise SystemExit("No valid series names were provided in --series")
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
        table_rows = build_country_series_table(lines, args.country, series, args.year_min, args.year_max)
        write_csv(args.output, table_rows, ["country", "year", *series])
        print(f"Extracted {len(table_rows)} rows for {args.country} ({args.year_min}-{args.year_max}) -> {args.output}")
        return
    if args.country or args.series:
        raise SystemExit("Use --country and --series together, or neither.")

    rows = extract_all_countries_elements(pages, args.year_min, args.year_max)
    write_csv(args.output, rows, ["country", "page", "year", "element", "value", "unit", "source", "line"])
    print(f"Auto extracted {len(rows)} element rows ({args.year_min}-{args.year_max}) -> {args.output}")
=======

        lines = load_pdf_lines(args.pdf)
        table_rows = build_country_series_table(
            lines=lines,
            country=args.country,
            series=series,
            year_min=args.year_min,
            year_max=args.year_max,
        )

        fieldnames = ["country", "year", *series]
        write_csv(args.output, table_rows, fieldnames)
        print(
            f"Extracted {len(table_rows)} rows for {args.country} ({args.year_min}-{args.year_max}) -> {args.output}"
        )
        return

    if args.country or args.series:
        raise SystemExit("Use --country and --series together, or neither.")

    rows = extract_candidate_rows(args.pdf)
    write_csv(args.output, rows, ["page", "year", "values", "line"])
    print(f"Extracted {len(rows)} candidate rows -> {args.output}")
>>>>>>> main


if __name__ == "__main__":
    main()
