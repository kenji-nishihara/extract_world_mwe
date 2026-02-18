import unittest

from extract_graph_data import build_country_series_table, parse_year_value_row


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
            {"page": "3", "line": "Brazil"},
            {"page": "3", "line": "2025 99 99 99 99"},
        ]
        table = build_country_series_table(
            lines=lines,
            country="Argentina",
            series=[
                "60 year operation",
                "80 year operation",
                "Government target",
            ],
            year_min=2025,
            year_max=2050,
        )
        self.assertEqual(len(table), 2)
        self.assertEqual(table[0]["country"], "Argentina")
        self.assertEqual(table[0]["year"], "2025")
        self.assertEqual(table[0]["60 year operation"], "11")
        self.assertEqual(table[0]["80 year operation"], "22")
        self.assertEqual(table[0]["Government target"], "33")


if __name__ == "__main__":
    unittest.main()
