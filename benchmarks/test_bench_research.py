#!/usr/bin/env python3
"""Correctness and reproducibility checks for bench_research.py (stdlib only)."""
import random
import unittest

from bench_research import (
    indexed_nearest, linear_nearest, topk, topk_int8,
    unit_vector, geo_bench, vector_bench,
)


class GeoTests(unittest.TestCase):
    def test_ties_and_boundaries(self):
        times = [0, 30, 60, 90]
        cases = [(-100, 0), (0, 0), (15, 0), (16, 1),
                 (30, 1), (45, 1), (46, 2), (10000, 3)]
        for query, expected in cases:
            self.assertEqual(linear_nearest(times, query), expected)
            self.assertEqual(indexed_nearest(times, query), expected)

    def test_many_deterministic_queries(self):
        rng = random.Random(1245)
        times = list(range(0, 307, 3))
        for _ in range(500):
            q = rng.randrange(-400, 800)
            self.assertEqual(indexed_nearest(times, q),
                             linear_nearest(times, q))

    def test_benchmark_zero_mismatches(self):
        x = geo_bench(101, 100, 2, 123)
        self.assertEqual(x["mismatches"], 0)
        self.assertEqual(x["baseline"]["total_calls"], 200)


class VectorTests(unittest.TestCase):
    def test_normalized_deterministic(self):
        a = unit_vector(random.Random(9), 48)
        b = unit_vector(random.Random(9), 48)
        self.assertEqual(a, b)
        self.assertAlmostEqual(sum(v * v for v in a), 1.0, places=12)

    def test_float_and_int8_exact_identity(self):
        self.assertEqual(topk([(1.0, 0.0), (0.0, 1.0)], (1.0, 0.0), 1), (0,))
        self.assertEqual(topk_int8([(127, 0), (0, 127)], (127, 0), 1), (0,))

    def test_benchmark_shape_and_repeatability(self):
        a = vector_bench(48, 12, 8, 4, 1, 11)
        b = vector_bench(48, 12, 8, 4, 1, 11)
        self.assertEqual(a["int8_recall_at_k_vs_float64"],
                         b["int8_recall_at_k_vs_float64"])
        self.assertEqual(a["float64_exact_scan"]["total_calls"], 8)
        self.assertEqual(a["theoretical_raw_payload_bytes"]["float64"],
                         8 * a["theoretical_raw_payload_bytes"]["int8"])


if __name__ == "__main__":
    unittest.main()
