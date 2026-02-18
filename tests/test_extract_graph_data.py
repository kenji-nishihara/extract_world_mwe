import unittest

from extract_graph_data import (
    build_country_series_table,
    estimate_bar_values_from_page,
    extract_all_countries_elements,
    is_merge_marker_line,
)


class ExtractGraphDataTests(unittest.TestCase):
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

    def test_extract_all_countries_elements_auto_bar_only(self):
        pages = [
            {
                "page": "1",
                "lines": ["Argentina", "2025 10 20 30"],
                "words": [
                    {"text": "0", "x0": 10, "x1": 20, "top": 100, "bottom": 110},
                    {"text": "100", "x0": 10, "x1": 30, "top": 0, "bottom": 10},
                    {"text": "2025", "x0": 90, "x1": 110, "top": 120, "bottom": 130},
                ],
                "rects": [{"x0": 95, "x1": 105, "top": 20, "bottom": 100}],
            },
        ]
        rows = extract_all_countries_elements(pages, year_min=2025, year_max=2050)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["country"], "Argentina")
        self.assertEqual(rows[0]["unit"], "MWe")
        self.assertEqual(rows[0]["source"], "bar_height")

    def test_build_country_series_table_from_bar_rows(self):
        rows = [
            {
                "country": "Argentina",
                "page": "1",
                "year": "2025",
                "element": "element_1",
                "value": "11",
                "source": "bar_height",
                "unit": "MWe",
                "line": "",
            },
            {
                "country": "Argentina",
                "page": "1",
                "year": "2025",
                "element": "element_2",
                "value": "22",
                "source": "bar_height",
                "unit": "MWe",
                "line": "",
            },
        ]
        table = build_country_series_table(
            bar_rows=rows,
            country="Argentina",
            series=["60 year operation", "80 year operation", "Government target"],
            year_min=2025,
            year_max=2050,
        )
        self.assertEqual(len(table), 1)
        self.assertEqual(table[0]["60 year operation"], "11")
        self.assertEqual(table[0]["80 year operation"], "22")
        self.assertEqual(table[0]["Government target"], "")

    def test_merge_marker_lines_are_ignored(self):
        self.assertTrue(is_merge_marker_line(">>>>>>> main"))


if __name__ == "__main__":
    unittest.main()
