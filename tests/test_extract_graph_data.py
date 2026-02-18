import unittest

from extract_graph_data import (
    build_country_series_table,
    estimate_bar_values_from_page,
    extract_all_countries_elements,
    parse_year_value_row,
)


class ExtractGraphDataTests(unittest.TestCase):
    def test_parse_year_value_row(self):
        parsed = parse_year_value_row("2025 10.0 20 30%")
        self.assertIsNotNone(parsed)
        year, values = parsed
        self.assertEqual(year, 2025)
        self.assertEqual(values, [10.0, 20.0, 30.0])

    def test_build_country_series_table(self):
        lines = [
            {"page": "2", "line": "Argentina"},
            {"page": "2", "line": "2025 11 22 33 44"},
            {"page": "2", "line": "2030 12 23 34 45"},
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
=======
            {"page": "3", "line": "Brazil"},
            {"page": "3", "line": "2025 99 99 99 99"},
>>>>>>> main
        ]
        table = build_country_series_table(
            lines=lines,
            country="Argentina",
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
            series=["60 year operation", "80 year operation", "Government target"],
=======
            series=[
                "60 year operation",
                "80 year operation",
                "Government target",
            ],
>>>>>>> main
            year_min=2025,
            year_max=2050,
        )
        self.assertEqual(len(table), 2)
<<<<<<< codex/extract-data-from-graphs-in-pdf-pvdyhs
        self.assertEqual(table[0]["60 year operation"], "11")

    def test_estimate_bar_values_from_page(self):
        page = {
            "words": [
                {"text": "0", "x0": 10, "x1": 20, "top": 100, "bottom": 110},
                {"text": "100", "x0": 10, "x1": 30, "top": 0, "bottom": 10},
                {"text": "2025", "x0": 90, "x1": 110, "top": 120, "bottom": 130},
            ],
            "rects": [
                {"x0": 95, "x1": 105, "top": 20, "bottom": 100},
            ],
        }
        rows = estimate_bar_values_from_page(page, 2025, 2050)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["year"], "2025")
        self.assertEqual(rows[0]["source"], "bar_height")

    def test_extract_all_countries_elements_auto(self):
        pages = [
            {"page": "1", "lines": ["Argentina", "2025 10 20 30"], "words": [], "rects": []},
        ]
        rows = extract_all_countries_elements(pages, year_min=2025, year_max=2050)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["country"], "Argentina")
        self.assertEqual(rows[0]["unit"], "MWe")
=======
        self.assertEqual(table[0]["country"], "Argentina")
        self.assertEqual(table[0]["year"], "2025")
        self.assertEqual(table[0]["60 year operation"], "11")
        self.assertEqual(table[0]["80 year operation"], "22")
        self.assertEqual(table[0]["Government target"], "33")
>>>>>>> main


if __name__ == "__main__":
    unittest.main()
