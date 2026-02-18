#!/usr/bin/env python3
"""Extract year/value rows from chart-heavy PDFs.

This script is a practical fallback for reports where chart source data is not
provided as machine-readable tables. It scans text content and captures lines
that contain a year + at least one numeric value.
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


def extract_rows(pdf_path: Path) -> list[dict[str, str]]:
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

    rows: list[dict[str, str]] = []
    if extractor_name == "pdfplumber":
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                for raw_line in text.splitlines():
                    line = normalize_line(raw_line)
                    if not line:
                        continue

                    year_match = YEAR_RE.search(line)
                    if not year_match:
                        continue

                    values = VALUE_RE.findall(line)
                    # Exclude trivial cases where only the year exists.
                    filtered = [v for v in values if v != year_match.group(1)]
                    if not filtered:
                        continue

                    rows.append(
                        {
                            "page": str(page_index),
                            "year": year_match.group(1),
                            "line": line,
                            "values": " | ".join(filtered),
                        }
                    )
    else:
        reader = PdfReader(str(pdf_path))
        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = normalize_line(raw_line)
                if not line:
                    continue

                year_match = YEAR_RE.search(line)
                if not year_match:
                    continue

                values = VALUE_RE.findall(line)
                filtered = [v for v in values if v != year_match.group(1)]
                if not filtered:
                    continue

                rows.append(
                    {
                        "page": str(page_index),
                        "year": year_match.group(1),
                        "line": line,
                        "values": " | ".join(filtered),
                    }
                )
    return rows


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
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    rows = extract_rows(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["page", "year", "values", "line"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Extracted {len(rows)} candidate rows -> {args.output}")


if __name__ == "__main__":
    main()
