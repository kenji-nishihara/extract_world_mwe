import unittest

from extract_graph_data import (
    CATEGORIES,
    best_color_to_category_mapping,
    build_country_series_table,
    extract_page_timeseries,
    is_merge_marker_line,
    mapping_cost_vs_table,
    parse_country_and_table,
    extract_y_ticks,
)


class ExtractGraphDataTests(unittest.TestCase):
    def test_parse_country_and_table(self):
        text = """
        3.2.1 Argentina
        1,000 2,000 3,000 4,000 5,000 6,000 7,000 28,000
        """
        country, nums = parse_country_and_table(text)
        self.assertEqual(country, "Argentina")
        self.assertEqual(nums[-1], 28000.0)

    def test_best_color_to_category_mapping(self):
        color_vals = {(1.0, 0.0, 0.0): 100.0, (0.0, 1.0, 0.0): 200.0}
        table = [200.0, 100.0, 0, 0, 0, 0, 0, 300.0]
        mapping = best_color_to_category_mapping(color_vals, table)
        self.assertEqual(mapping[(0.0, 1.0, 0.0)], CATEGORIES[0])
        self.assertEqual(mapping[(1.0, 0.0, 0.0)], CATEGORIES[1])

    def test_mapping_cost_vs_table(self):
        mapping = {(1.0, 0.0, 0.0): "60-year operation"}
        color_values = {(1.0, 0.0, 0.0): 100.0}
        table = [100.0, 0, 0, 0, 0, 0, 0, 100.0]
        self.assertEqual(mapping_cost_vs_table(mapping, color_values, table), 0.0)


    def test_extract_y_ticks_ignores_noise_numbers(self):
        words = [
            {"text": "0", "x0": 20, "x1": 30, "top": 360, "bottom": 370},
            {"text": "500", "x0": 20, "x1": 35, "top": 320, "bottom": 330},
            {"text": "1000", "x0": 20, "x1": 40, "top": 280, "bottom": 290},
            {"text": "1500", "x0": 20, "x1": 40, "top": 240, "bottom": 250},
            {"text": "2000", "x0": 20, "x1": 40, "top": 200, "bottom": 210},
            # noise near left area but different column
            {"text": "1235", "x0": 90, "x1": 110, "top": 260, "bottom": 270},
        ]
        ymap = extract_y_ticks(words)
        self.assertIsNotNone(ymap)
        # top around y=220 should be about 1750MWe with this axis spacing
        self.assertAlmostEqual(ymap.f(220), 1750, delta=90)

    def test_extract_page_timeseries_with_legend(self):
        page = {
            "text": "3.2.1 Argentina\n1,780 0 0 0 300 0 0 2,080",
            "words": [
                {"text": "0", "x0": 20, "x1": 30, "top": 360, "bottom": 370},
                {"text": "2000", "x0": 20, "x1": 40, "top": 200, "bottom": 210},
                {"text": "2025", "x0": 200, "x1": 220, "top": 520, "bottom": 540},
                {"text": "2050", "x0": 500, "x1": 520, "top": 520, "bottom": 540},
                {"text": "60-year", "x0": 200, "x1": 240, "top": 560, "bottom": 570},
                {"text": "operation", "x0": 245, "x1": 300, "top": 560, "bottom": 570},
                {"text": "Proposed", "x0": 200, "x1": 260, "top": 580, "bottom": 590},
            ],
            "rects": [
                # legend swatches
                {"fill": True, "non_stroking_color": (1, 0, 0), "x0": 185, "x1": 195, "top": 560, "bottom": 570, "width": 10, "height": 10},
                {"fill": True, "non_stroking_color": (0, 1, 0), "x0": 185, "x1": 195, "top": 580, "bottom": 590, "width": 10, "height": 10},
                # bars at 2025
                {"fill": True, "non_stroking_color": (1, 0, 0), "x0": 198, "x1": 210, "top": 220, "bottom": 360, "width": 12, "height": 140},
                {"fill": True, "non_stroking_color": (0, 1, 0), "x0": 198, "x1": 210, "top": 340, "bottom": 360, "width": 12, "height": 20},
            ],
        }
        rows = extract_page_timeseries(page)
        self.assertTrue(rows)
        self.assertTrue(all(r["source"] == "bar_height" for r in rows))
        self.assertTrue(any(r["country"] == "Argentina" and r["year"] == "2025" for r in rows))

    def test_build_country_series_table(self):
        rows = [
            {"country": "Argentina", "year": "2025", "category": "60-year operation", "mwe": "100", "unit": "MWe", "source": "bar_height"},
            {"country": "Argentina", "year": "2025", "category": "Government target", "mwe": "50", "unit": "MWe", "source": "bar_height"},
        ]
        table = build_country_series_table(rows, "Argentina", ["60-year operation", "Government target"], 2025, 2050)
        self.assertEqual(table[0]["60-year operation"], "100")
        self.assertEqual(table[0]["Government target"], "50")

    def test_merge_marker_lines_are_ignored(self):
        self.assertTrue(is_merge_marker_line(">>>>>>> main"))


if __name__ == "__main__":
    unittest.main()
