import unittest

from differentiator import DifferentiatorError, differentiate, format_results


class DifferentiatorTests(unittest.TestCase):
    def test_returns_each_normal_derivative(self):
        result = differentiate("x^3 + 2*x", "x", 3)
        self.assertEqual([str(item) for item in result.derivatives], ["3*x**2 + 2", "6*x", "6"])

    def test_returns_partial_derivative(self):
        result = differentiate("x^2*y + sin(y)", "y", 1)
        self.assertEqual(str(result.derivatives[0]), "x**2 + cos(y)")

    def test_rejects_zero_division(self):
        with self.assertRaisesRegex(DifferentiatorError, "Zero Division Error"):
            differentiate("1 / 0", "x", 1)

    def test_rejects_known_nondifferentiable_form(self):
        with self.assertRaisesRegex(DifferentiatorError, "Non-Differentiable"):
            differentiate("abs(x)", "x", 1)

    def test_rejects_invalid_count(self):
        with self.assertRaisesRegex(DifferentiatorError, "count"):
            differentiate("x", "x", 0)

    def test_formats_general_result_and_timing(self):
        text = format_results(differentiate("x^2", "x", 2), "x")
        self.assertIn("General result", text)
        self.assertIn("Processing time", text)


if __name__ == "__main__":
    unittest.main()
