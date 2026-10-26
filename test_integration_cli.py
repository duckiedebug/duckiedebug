import subprocess
import sys
import unittest
from pathlib import Path

from integration_cli import (
    IntegrationMode,
    IntegrationRequest,
    UnclosedPathError,
    VariableOrderingError,
    integrate_with_timeout,
)


ROOT = Path(__file__).parent


class IntegrationTests(unittest.TestCase):
    def test_normal_integral_outputs_integrated_expression(self) -> None:
        result = integrate_with_timeout(
            IntegrationRequest(IntegrationMode.NORMAL, "x**2", ("x",), ("0:2",))
        )
        self.assertEqual(result.integrated_expression, "8/3")
        self.assertLess(result.elapsed_seconds, 15)

    def test_double_integral(self) -> None:
        result = integrate_with_timeout(
            IntegrationRequest(IntegrationMode.DOUBLE, "x + y", ("x", "y"), ("0:1", "0:2"))
        )
        self.assertEqual(result.integrated_expression, "3")

    def test_triple_integral(self) -> None:
        result = integrate_with_timeout(
            IntegrationRequest(
                IntegrationMode.TRIPLE, "x + y + z", ("x", "y", "z"), ("0:1", "0:1", "0:1")
            )
        )
        self.assertEqual(result.integrated_expression, "3/2")

    def test_line_integral(self) -> None:
        result = integrate_with_timeout(
            IntegrationRequest(
                IntegrationMode.LINE,
                variables=("t",),
                bounds=("0:1",),
                field="x,y",
                parametrization="t,t**2",
            )
        )
        self.assertEqual(result.integrated_expression, "1")

    def test_surface_flux(self) -> None:
        result = integrate_with_timeout(
            IntegrationRequest(
                IntegrationMode.SURFACE,
                variables=("u", "v"),
                bounds=("0:1", "0:1"),
                field="0,0,1",
                parametrization="u,v,0",
            )
        )
        self.assertEqual(result.integrated_expression, "1")

    def test_variable_order_is_required(self) -> None:
        with self.assertRaises(VariableOrderingError):
            integrate_with_timeout(IntegrationRequest(IntegrationMode.DOUBLE, "x+y", ("x",), ()))

    def test_unclosed_path_is_reported(self) -> None:
        with self.assertRaises(UnclosedPathError):
            integrate_with_timeout(
                IntegrationRequest(
                    IntegrationMode.LINE,
                    variables=("t",),
                    bounds=("0:1",),
                    field="x,y",
                    parametrization="t,t**2",
                    closed=True,
                )
            )

    def test_quit_deactivates(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "integration_cli.py")],
            input="quit\n",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Machine deactivated.", completed.stdout)


if __name__ == "__main__":
    unittest.main()
