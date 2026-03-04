import random
import unittest

from fuel_composition_generator import generate_one, is_valid


class FuelCompositionGeneratorTests(unittest.TestCase):
    def test_generate_one_produces_valid_composition(self):
        rng = random.Random(42)
        comp = generate_one(rng)
        self.assertTrue(is_valid(comp))
        self.assertAlmostEqual(sum(comp.values()), 1.0, places=12)

    def test_is_valid_rejects_invalid_u238(self):
        comp = {
            "U235": 0.05,
            "U238": 0.50,
            "Pu238": 0.01,
            "Pu239": 0.04,
            "Pu240": 0.20,
            "Pu241": 0.02,
            "Pu242": 0.06,
            "Am241": 0.12,
        }
        self.assertFalse(is_valid(comp))


if __name__ == "__main__":
    unittest.main()
