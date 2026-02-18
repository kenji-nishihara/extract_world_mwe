#!/usr/bin/env python3
"""Extract year/value data rows from graph-heavy PDFs.

Default mode:
  - Extract candidate lines containing a year + numeric values.

Country/series mode:
  - Filter to pages mentioning a country name.
  - Parse year rows and map numeric columns to user-provided series names.
  - Export a tidy CSV (year x series values).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|21\d{2})\b")
VALUE_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?")


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def parse_numeric(token: str) -> float | None:
    cleaned = token.replace(",", "").replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_year_value_row(line: str) -> tuple[int, list[float]] | None:
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
    return rows


def build_country_series_table(
    lines: list[dict[str, str]],
    country: str,
    series: list[str],
    year_min: int,
    year_max: int,
) -> list[dict[str, str]]:
    """Build a wide table where each row is one year and each column is a series."""
    country_lower = country.lower()
    candidate_pages = {
        entry["page"] for entry in lines if country_lower in entry["line"].lower()
    }

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
        values = by_year[year]
        row: dict[str, str] = {"country": country, "year": str(year)}
        for idx, series_name in enumerate(series):
            row[series_name] = ""
            if idx < len(values):
                row[series_name] = str(values[idx]).rstrip("0").rstrip(".")
        table.append(row)

    return table


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
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

    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    if args.country and args.series:
        series = [s.strip() for s in args.series.split(",") if s.strip()]
        if not series:
            raise SystemExit("No valid series names were provided in --series")

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


if __name__ == "__main__":
    main()
