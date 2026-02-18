#!/usr/bin/env python3
from __future__ import annotations

"""Extract country/year/category MWe values from stacked-bar charts in the WNO PDF.

Default behavior:
- Read all pages.
- Extract chart bars from geometry (`source=bar_height`) only.
- Convert bar heights to MWe from Y-axis ticks.
- Save long-format CSV and a pivot CSV.
"""

import argparse
import csv
import itertools
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

CATEGORIES = [
    "60-year operation",
    "80-year operation",
    "Under construction",
    "Planned",
    "Proposed",
    "Potential",
    "Government target",
]

MERGE_MARKER_PREFIXES = ("<<<<<<<", "=======", ">>>>>>>")


class LinMap:
    def __init__(self, a: float, b: float) -> None:
        self.a = a
        self.b = b

    def f(self, y: float) -> float:
        return self.a * y + self.b


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def is_merge_marker_line(line: str) -> bool:
    stripped = line.strip()
    return any(stripped.startswith(prefix) for prefix in MERGE_MARKER_PREFIXES)


def norm_color(c: object, nd: int = 2) -> tuple[float, ...] | None:
    if c is None:
        return None
    if isinstance(c, (int, float)):
        return (round(float(c), nd),)
    if isinstance(c, (list, tuple)):
        try:
            return tuple(round(float(x), nd) for x in c)
        except (TypeError, ValueError):
            return None
    return None




def color_distance(c1: tuple[float, ...], c2: tuple[float, ...]) -> float:
    if not c1 or not c2:
        return float("inf")
    n = min(len(c1), len(c2))
    return sum((float(c1[i]) - float(c2[i])) ** 2 for i in range(n)) ** 0.5


def resolve_category_by_color(
    color: tuple[float, ...],
    direct_map: dict[tuple[float, ...], str],
    *,
    max_dist: float = 0.18,
) -> str | None:
    """Resolve a bar color to category with nearest-color fallback.

    PDF drawing colors often differ slightly between legend swatches and bars,
    so exact tuple equality can miss valid matches.
    """
    if color in direct_map:
        return direct_map[color]
    if not direct_map:
        return None

    best_color = min(direct_map.keys(), key=lambda k: color_distance(color, k))
    if color_distance(color, best_color) <= max_dist:
        return direct_map[best_color]
    return None

def parse_country_and_table(page_text: str) -> tuple[str | None, list[float] | None]:
    lines = [normalize_line(ln) for ln in (page_text or "").splitlines()]
    lines = [ln for ln in lines if ln and not is_merge_marker_line(ln)]

    country = None
    for idx, ln in enumerate(lines):
        m = re.match(r"^(\d+\.\d+\.\d+)\s+(.+)$", ln)
        if not m:
            continue
        head = m.group(2).strip()
        if idx + 1 < len(lines):
            nxt = lines[idx + 1]
            if not re.match(r"^\d+\.\d+\.\d+\s+", nxt) and not nxt.startswith("["):
                if (not re.search(r"\d", nxt)) and (len(head) < 14 or head.endswith(("Kin", "Arab", "Rep", "Isl", "Fed", "Dem"))):
                    head = f"{head} {nxt}".strip()
        country = head
        break

    nums = None
    for ln in lines:
        toks = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", ln)
        if len(toks) == 8:
            nums = [float(t.replace(",", "")) for t in toks]
            break

    return country, nums


def fit_linear_y_to_value(points: list[tuple[float, float]]) -> LinMap | None:
    if len(points) < 2:
        return None
    ys = [p[0] for p in points]
    vs = [p[1] for p in points]
    y_mean = sum(ys) / len(ys)
    v_mean = sum(vs) / len(vs)
    var_y = sum((y - y_mean) ** 2 for y in ys)
    if var_y == 0:
        return None
    cov = sum((y - y_mean) * (v - v_mean) for y, v in points)
    a = cov / var_y
    b = v_mean - a * y_mean
    return LinMap(a, b)


def extract_y_ticks(words: list[dict]) -> LinMap | None:
    """Extract a robust y->value map from axis ticks.

    We prioritize left-side, round-number ticks and select the densest x-column
    to avoid contaminating the fit with non-axis numbers.
    """

    candidates: list[tuple[float, float, float]] = []  # (x_mid, y_mid, value)
    for w in words:
        txt = str(w.get("text", "")).strip()
        if not re.fullmatch(r"\d{1,4}(?:,\d{3})*", txt):
            continue

        value = float(txt.replace(",", ""))
        if value % 50 != 0:
            continue

        x0 = float(w.get("x0", 0.0))
        x1 = float(w.get("x1", x0))
        x_mid = 0.5 * (x0 + x1)
        if x_mid >= 150:
            continue

        top = float(w.get("top", 0.0))
        bottom = float(w.get("bottom", top))
        if not (150 <= top <= 500):
            continue
        y_mid = 0.5 * (top + bottom)
        candidates.append((x_mid, y_mid, value))

    if len(candidates) < 2:
        return None

    # choose the densest x column (axis tick labels align vertically)
    bins: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for x_mid, y_mid, value in candidates:
        bins[int(round(x_mid / 12.0))].append((y_mid, value))
    best_bin = max(bins, key=lambda b: len(bins[b]))
    selected = bins[best_bin]

    if len(selected) < 2:
        selected = [(y, v) for _, y, v in candidates]

    by_val: dict[float, list[float]] = defaultdict(list)
    for y, v in selected:
        by_val[v].append(y)
    dedup = [(median(ys), v) for v, ys in by_val.items()]

    # keep points that follow monotonic trend (higher value should be higher on chart)
    dedup.sort(key=lambda t: t[0])
    monotonic: list[tuple[float, float]] = []
    for y, v in dedup:
        if not monotonic or v <= monotonic[-1][1]:
            monotonic.append((y, v))

    if len(monotonic) >= 2:
        dedup = monotonic

    dedup.sort(key=lambda t: t[1])
    return fit_linear_y_to_value(dedup)


def extract_year_positions(words: list[dict], rects: list[dict]) -> dict[int, float]:
    year_to_x: dict[int, list[float]] = defaultdict(list)
    for w in words:
        txt = str(w.get("text", "")).strip()
        if not re.fullmatch(r"\d{4}", txt):
            continue
        for cand in (txt, txt[::-1]):
            if cand.startswith("20"):
                year = int(cand)
                if 2024 <= year <= 2051 and 240 <= float(w.get("top", 0.0)) <= 580:
                    xc = 0.5 * (float(w.get("x0", 0.0)) + float(w.get("x1", w.get("x0", 0.0))))
                    year_to_x[year].append(xc)
                break

    if year_to_x:
        out = {y: float(median(xs)) for y, xs in year_to_x.items()}
        return dict(sorted(out.items()))

    # fallback from bar centers
    x_centers: list[float] = []
    for r in rects:
        if not r.get("fill"):
            continue
        if norm_color(r.get("non_stroking_color")) is None:
            continue
        top = float(r.get("top", 0.0))
        h = float(r.get("height", 0.0))
        w = float(r.get("width", 0.0))
        if not (110 <= top <= 390) or h < 2.0 or w > 40.0:
            continue
        xc = 0.5 * (float(r.get("x0", 0.0)) + float(r.get("x1", r.get("x0", 0.0))))
        x_centers.append(xc)

    if not x_centers:
        return {}

    x_centers.sort()
    dedup = [x_centers[0]]
    for x in x_centers[1:]:
        if abs(x - dedup[-1]) > 0.9:
            dedup.append(x)
    if len(dedup) < 26:
        return {}

    # quantile-style picks for 26 years
    years = list(range(2025, 2051))
    n = len(dedup)
    out: dict[int, float] = {}
    for i, yr in enumerate(years):
        q = i / (len(years) - 1)
        pos = q * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        val = dedup[lo] * (1 - frac) + dedup[hi] * frac
        out[yr] = float(val)
    return out


def parse_legend_color_map(words: list[dict], rects: list[dict]) -> dict[tuple[float, ...], str]:
    legend_rects: list[dict] = []
    for r in rects:
        if not r.get("fill"):
            continue
        col = norm_color(r.get("non_stroking_color"))
        if col is None:
            continue
        w = float(r.get("width", 0.0))
        h = float(r.get("height", 0.0))
        top = float(r.get("top", 0.0))
        if 3.5 <= w <= 14.0 and 3.5 <= h <= 14.0 and 340 <= top <= 570:
            legend_rects.append(r)

    if not legend_rects:
        return {}

    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        # split robustly: "60-year", "60year", "60 year" -> ["60", "year"]
        return re.findall(r"[a-z]+|\d+", lowered)

    def find_label_bbox(cat: str) -> tuple[float, float, float, float] | None:
        cat_toks = _tokenize(cat)
        if not cat_toks:
            return None

        legend_words = [
            w
            for w in words
            if 330 <= float(w.get("top", 0.0)) <= 600 and str(w.get("text", "")).strip()
        ]
        legend_words.sort(key=lambda w: (round(float(w.get("top", 0.0)) / 8.0), float(w.get("x0", 0.0))))

        best_hits: list[dict] | None = None
        for i in range(len(legend_words)):
            hits = [legend_words[i]]
            seen_toks = _tokenize(str(legend_words[i].get("text", "")))
            j = i + 1
            while j < len(legend_words) and len(seen_toks) < len(cat_toks):
                if abs(float(legend_words[j].get("top", 0.0)) - float(hits[-1].get("top", 0.0))) > 12:
                    break
                hits.append(legend_words[j])
                seen_toks.extend(_tokenize(str(legend_words[j].get("text", ""))))
                j += 1

            if seen_toks[: len(cat_toks)] == cat_toks:
                best_hits = hits[: max(1, len(cat_toks))]
                break

        if not best_hits:
            return None

        return (
            min(float(h["x0"]) for h in best_hits),
            min(float(h["top"]) for h in best_hits),
            max(float(h["x1"]) for h in best_hits),
            max(float(h["bottom"]) for h in best_hits),
        )

    cmap: dict[tuple[float, ...], str] = {}
    for cat in CATEGORIES:
        bb = find_label_bbox(cat)
        if bb is None:
            continue
        x0, y0, _, y1 = bb
        ymid = 0.5 * (y0 + y1)
        best = None
        best_dist = 10**9
        for r in legend_rects:
            rx1 = float(r.get("x1", 0.0))
            rymid = 0.5 * (float(r.get("top", 0.0)) + float(r.get("bottom", 0.0)))
            if rx1 <= x0 and abs(rymid - ymid) <= 14:
                dist = x0 - rx1
                if dist < best_dist:
                    best_dist = dist
                    best = r
        if best is not None:
            col = norm_color(best.get("non_stroking_color"))
            if col is not None:
                cmap[col] = cat

    return cmap


def best_color_to_category_mapping(color_values_2050: dict[tuple[float, ...], float], table_values: list[float], min_mwe: float = 1.0) -> dict[tuple[float, ...], str]:
    """Map observed 2050 bar colors to 7 categories using table values.

    Unlike earlier versions, zero-valued categories are also valid targets so
    colors that fade out by 2050 (e.g., 60-year operation) are not dropped.
    """

    targets_full = table_values[:7]
    all_target_idx = list(range(len(CATEGORIES)))

    observed = [(c, v) for c, v in color_values_2050.items() if v >= min_mwe]
    observed.sort(key=lambda x: x[1], reverse=True)
    if not observed:
        return {}

    # At most 7 categories can be assigned directly.
    if len(observed) > len(all_target_idx):
        observed = observed[: len(all_target_idx)]

    colors = [c for c, _ in observed]
    obs_vals = [v for _, v in observed]
    k = len(colors)

    best_cost = float("inf")
    best_subset = None
    best_perm = None
    for subset in itertools.combinations(all_target_idx, k):
        target_vals = [targets_full[i] for i in subset]
        for perm in itertools.permutations(range(k)):
            cost = 0.0
            for i_t, j_o in enumerate(perm):
                # slight preference for matching nonzero table categories
                base = abs(target_vals[i_t] - obs_vals[j_o])
                if target_vals[i_t] == 0 and obs_vals[j_o] > 0:
                    base += 0.05 * obs_vals[j_o]
                cost += base
            if cost < best_cost:
                best_cost = cost
                best_subset = subset
                best_perm = perm

    if best_subset is None or best_perm is None:
        return {}

    mapping: dict[tuple[float, ...], str] = {}
    for i_t, j_o in enumerate(best_perm):
        mapping[colors[j_o]] = CATEGORIES[best_subset[i_t]]
    return mapping


def mapping_cost_vs_table(
    mapping: dict[tuple[float, ...], str],
    year_color_values: dict[tuple[float, ...], float],
    table_values: list[float],
) -> float:
    if not mapping:
        return float("inf")

    est = {cat: 0.0 for cat in CATEGORIES}
    for color, value in year_color_values.items():
        cat = resolve_category_by_color(color, mapping)
        if cat:
            est[cat] += value

    cost = 0.0
    for idx, cat in enumerate(CATEGORIES):
        cost += abs(est[cat] - float(table_values[idx]))
    return cost


def rect_value_mwe(rect: dict, ymap: LinMap) -> float:
    top = float(rect.get("top", rect.get("y0", 0.0)))
    bottom = float(rect.get("bottom", rect.get("y1", top)))
    return abs(ymap.f(bottom) - ymap.f(top))


def extract_page_timeseries(page: dict) -> list[dict[str, str]]:
    country, table_nums = parse_country_and_table(page.get("text", ""))
    if not country:
        return []

    words = page.get("words", [])
    rects = page.get("rects", [])
    if not words or not rects:
        return []

    ymap = extract_y_ticks(words)
    if ymap is None:
        return []

    year_to_x = extract_year_positions(words, rects)
    years = sorted(y for y in year_to_x if 2025 <= y <= 2050)
    if len(years) < 2:
        return []

    x_vals = [year_to_x[y] for y in years]
    x_min, x_max = min(x_vals) - 20.0, max(x_vals) + 20.0

    by_year_color: dict[int, dict[tuple[float, ...], float]] = {y: {} for y in years}
    for r in rects:
        if not r.get("fill"):
            continue
        col = norm_color(r.get("non_stroking_color"))
        if col is None:
            continue

        w = float(r.get("width", 0.0))
        h = float(r.get("height", 0.0))
        top = float(r.get("top", 0.0))
        xc = 0.5 * (float(r.get("x0", 0.0)) + float(r.get("x1", r.get("x0", 0.0))))

        if not (x_min <= xc <= x_max):
            continue
        if not (105 <= top <= 440):
            continue
        if w > 40.0 or w < 2.5 or h < 1.0:
            continue
        if w <= 14.0 and 360 <= top <= 570:
            continue

        nearest_year = min(years, key=lambda y: abs(year_to_x[y] - xc))
        mwe = rect_value_mwe(r, ymap)
        by_year_color[nearest_year][col] = by_year_color[nearest_year].get(col, 0.0) + mwe

    legend_map = parse_legend_color_map(words, rects)
    color_to_category = legend_map
    if table_nums is not None:
        yr2050 = 2050 if 2050 in by_year_color else max(by_year_color)
        fallback_map = best_color_to_category_mapping(by_year_color[yr2050], table_nums)
        legend_cost = mapping_cost_vs_table(legend_map, by_year_color[yr2050], table_nums)
        fallback_cost = mapping_cost_vs_table(fallback_map, by_year_color[yr2050], table_nums)
        if fallback_cost < legend_cost:
            color_to_category = fallback_map

    if not color_to_category:
        return []

    rows: list[dict[str, str]] = []
    for year in years:
        sums = {cat: 0.0 for cat in CATEGORIES}
        for col, value in by_year_color[year].items():
            cat = resolve_category_by_color(col, color_to_category)
            if cat:
                sums[cat] += value

        for cat in CATEGORIES:
            rows.append(
                {
                    "country": country,
                    "year": str(year),
                    "category": cat,
                    "mwe": f"{sums[cat]:.2f}",
                    "unit": "MWe",
                    "source": "bar_height",
                }
            )

    if table_nums is not None and 2050 in years:
        bars_total = sum(float(r["mwe"]) for r in rows if int(r["year"]) == 2050)
        table_total = float(table_nums[7])
        if abs(bars_total - table_total) > max(20.0, 0.08 * max(table_total, 1.0)):
            print(f"[WARN] {country}: 2050 sum mismatch bars={bars_total:.1f}, table={table_total:.1f}")

    return rows


def load_pdf_pages(pdf_path: Path) -> list[dict]:
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: pdfplumber is required for bar-height extraction.\n"
            "Install in same interpreter: pip install pdfplumber\n"
            f"Current interpreter: {sys.executable}"
        ) from exc

    pages: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            text = "\n".join(
                ln for ln in text.splitlines() if ln.strip() and not is_merge_marker_line(ln)
            )
            pages.append({"text": text, "words": page.extract_words() or [], "rects": page.rects or []})
    return pages


def build_country_series_table(rows: list[dict[str, str]], country: str, series: list[str], year_min: int, year_max: int) -> list[dict[str, str]]:
    target = country.lower().strip()
    filtered = [r for r in rows if r["country"].lower().strip() == target and year_min <= int(r["year"]) <= year_max]

    by_year_category: dict[int, dict[str, str]] = defaultdict(dict)
    for r in filtered:
        by_year_category[int(r["year"])][r["category"]] = r["mwe"]

    out: list[dict[str, str]] = []
    for year in sorted(by_year_category):
        row = {"country": country, "year": str(year)}
        for s in series:
            row[s] = by_year_category[year].get(s, "")
        out.append(row)
    return out


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_pivot_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    agg: dict[tuple[str, str], dict[str, str]] = {}
    for r in rows:
        key = (r["country"], r["year"])
        agg.setdefault(key, {})[r["category"]] = r["mwe"]

    out = []
    for (country, year), cats in sorted(agg.items(), key=lambda kv: (kv[0][0], int(kv[0][1]))):
        row = {"country": country, "year": year}
        for cat in CATEGORIES:
            row[cat] = cats.get(cat, "0")
        out.append(row)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract year/category MWe from PDF stacked bars (bar_height only).")
    parser.add_argument("pdf", type=Path, help="Input PDF path")
    parser.add_argument("-o", "--output", type=Path, default=Path("world_nuclear_outlook_country_year_category_mwe.csv"))
    parser.add_argument("--pivot-output", type=Path, default=None, help="Output path for pivot CSV")
    parser.add_argument("-c", "--country", "-country", dest="country")
    parser.add_argument("-s", "--series", "-series", dest="series")
    parser.add_argument("-y", "--year-min", "-year-min", dest="year_min", type=int, default=2025)
    parser.add_argument("-Y", "--year-max", "-year-max", dest="year_max", type=int, default=2050)
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    pages = load_pdf_pages(args.pdf)
    rows: list[dict[str, str]] = []
    for page in pages:
        rows.extend(extract_page_timeseries(page))

    rows = [r for r in rows if args.year_min <= int(r["year"]) <= args.year_max]
    if args.country:
        rows = [r for r in rows if r["country"].lower() == args.country.lower()]

    if not rows:
        raise SystemExit("No data extracted. Check PDF_PATH and heuristics.")

    if args.series:
        if not args.country:
            raise SystemExit("--series requires --country.")
        series = [s.strip() for s in args.series.split(",") if s.strip()]
        table = build_country_series_table(rows, args.country, series, args.year_min, args.year_max)
        write_csv(args.output, table, ["country", "year", *series])
        print(f"Saved: {args.output}")
        return

    write_csv(args.output, rows, ["country", "year", "category", "mwe", "unit", "source"])
    pivot_output = args.pivot_output or args.output.with_name(f"{args.output.stem}_pivot.csv")
    pivot_rows = build_pivot_rows(rows)
    write_csv(pivot_output, pivot_rows, ["country", "year", *CATEGORIES])
    print(f"Saved: {args.output}")
    print(f"Saved: {pivot_output}")


if __name__ == "__main__":
    main()
