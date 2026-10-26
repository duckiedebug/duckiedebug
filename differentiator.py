#!/usr/bin/env python3
"""A safe, timed command-line symbolic differentiator."""

from __future__ import annotations

import signal
import time
from dataclasses import dataclass
from typing import NoReturn

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


MAX_PROCESSING_SECONDS = 15
MAX_EXPRESSION_LENGTH = 500
MAX_RESULT_LENGTH = 10_000
MAX_DIFFERENTIATIONS = 100
TRANSFORMATIONS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)


class DifferentiatorError(Exception):
    """An expected, user-facing differentiation error."""


class ProcessingTimeout(DifferentiatorError):
    """Raised after the processing-time requirement is exceeded."""


@dataclass(frozen=True)
class DifferentiationResult:
    derivatives: list[sp.Expr]
    elapsed_seconds: float


def _timeout_handler(_signum: int, _frame: object) -> NoReturn:
    raise ProcessingTimeout(
        f"Processing exceeded {MAX_PROCESSING_SECONDS} seconds; operation halted."
    )


def _install_timeout() -> object:
    """Install a short-lived POSIX alarm and return its previous handler."""
    previous = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, MAX_PROCESSING_SECONDS)
    return previous


def _clear_timeout(previous_handler: object) -> None:
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, previous_handler)


def _safe_symbols(variable: str) -> dict[str, object]:
    """Supply named variables and a deliberately small approved function set."""
    names = {name: sp.Symbol(name) for name in "abcdefghijklmnopqrstuvwxyz"}
    names.update(
        {
            # Parser-generated numeric constructors; these do not expose Python builtins.
            "Integer": sp.Integer,
            "Float": sp.Float,
            "Rational": sp.Rational,
            "pi": sp.pi,
            "E": sp.E,
            "sin": sp.sin,
            "cos": sp.cos,
            "tan": sp.tan,
            "asin": sp.asin,
            "acos": sp.acos,
            "atan": sp.atan,
            "exp": sp.exp,
            "log": sp.log,
            "sqrt": sp.sqrt,
            "abs": sp.Abs,
        }
    )
    names[variable] = sp.Symbol(variable)
    return names


def parse_expression(text: str, variable: str) -> sp.Expr:
    """Parse a mathematical expression without exposing Python builtins."""
    if not text.strip():
        raise DifferentiatorError("Expression cannot be empty.")
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise DifferentiatorError(
            f"Expression swelling risk: input is limited to {MAX_EXPRESSION_LENGTH} characters."
        )
    if "__" in text or "[" in text or "]" in text:
        raise DifferentiatorError("Invalid expression: only mathematical notation is accepted.")

    try:
        expression = parse_expr(
            text,
            local_dict=_safe_symbols(variable),
            global_dict={"__builtins__": {}},
            transformations=TRANSFORMATIONS,
            evaluate=True,
        )
    except (SyntaxError, TypeError, ValueError, NameError) as exc:
        raise DifferentiatorError(f"Invalid expression: {exc}") from exc
    except ZeroDivisionError as exc:
        raise DifferentiatorError("Zero Division Error: division by zero is undefined.") from exc

    if not isinstance(expression, sp.Expr):
        raise DifferentiatorError("Invalid expression: enter a mathematical expression.")
    if expression.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        raise DifferentiatorError(
            "Zero Division Error: the expression contains an undefined or infinite value."
        )
    if expression.has(sp.Abs, sp.sign, sp.Heaviside, sp.floor, sp.ceiling):
        raise DifferentiatorError(
            "Discontinuity and Non-Differentiable Points Error: "
            "the expression contains a function that is not differentiable everywhere."
        )
    return expression


def differentiate(text: str, variable_name: str, count: int) -> DifferentiationResult:
    """Return every derivative from first through ``count`` within the time limit."""
    if count < 1 or count > MAX_DIFFERENTIATIONS:
        raise DifferentiatorError(
            f"Differentiation count must be between 1 and {MAX_DIFFERENTIATIONS}."
        )
    if not (len(variable_name) == 1 and variable_name.isalpha()):
        raise DifferentiatorError("Variable must be one letter, for example x or y.")

    previous_handler = _install_timeout()
    started = time.perf_counter()
    try:
        variable = sp.Symbol(variable_name)
        current = parse_expression(text, variable_name)
        derivatives: list[sp.Expr] = []
        for _ in range(count):
            current = sp.cancel(sp.diff(current, variable))
            rendered = str(current)
            if len(rendered) > MAX_RESULT_LENGTH:
                raise DifferentiatorError(
                    "Expression Swelling Error: result is too large to display safely."
                )
            derivatives.append(current)
        return DifferentiationResult(derivatives, time.perf_counter() - started)
    except ProcessingTimeout:
        raise
    except (sp.PoleError, sp.SympifyError) as exc:
        raise DifferentiatorError(f"Simplification Error: {exc}") from exc
    except (ArithmeticError, OverflowError, FloatingPointError) as exc:
        raise DifferentiatorError(f"Arithmetic Error: {exc}") from exc
    finally:
        _clear_timeout(previous_handler)


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def format_results(result: DifferentiationResult, variable: str) -> str:
    rows = ["\nDerivatives:"]
    for index, derivative in enumerate(result.derivatives, start=1):
        primes = "'" * index if index <= 3 else f"^({index})"
        rows.append(f"  f{primes}({variable}) = {derivative}")
    final = result.derivatives[-1]
    rows.extend(
        [
            f"General result: the {ordinal(len(result.derivatives))} derivative is "
            f"f^({len(result.derivatives)})({variable}) = {final}",
            f"Processing time: {result.elapsed_seconds:.6f} seconds",
        ]
    )
    return "\n".join(rows)


def _read(prompt: str) -> str | None:
    try:
        response = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nDeactivated.")
        return None
    return response


def _choose_mode() -> str | None:
    while True:
        choice = _read("Choose mode [1 normal, 2 partial, quit]: ")
        if choice is None or choice.lower() == "quit":
            return None
        if choice in {"1", "normal", "n"}:
            return "normal"
        if choice in {"2", "partial", "p"}:
            return "partial"
        print("Input Error: choose 1 (normal), 2 (partial), or quit.")


def run_cli() -> None:
    """Run the activation, cycle, and deactivation operations."""
    print("Symbolic Differentiator")
    print("Enter expressions using x**2, sin(x), log(x), etc. Type 'quit' to close.")

    while True:
        mode = _choose_mode()
        if mode is None:
            print("Machine deactivated.")
            return

        count_text = _read("Number of differentiations: ")
        if count_text is None or count_text.lower() == "quit":
            print("Machine deactivated.")
            return
        try:
            count = int(count_text)
        except ValueError:
            print("Input Error: enter a whole number. Returning to cycle.\n")
            continue

        expression = _read("Expression: ")
        if expression is None or expression.lower() == "quit":
            print("Machine deactivated.")
            return

        variable = "x"
        if mode == "partial":
            variable_text = _read("Differentiate partially with respect to: ")
            if variable_text is None or variable_text.lower() == "quit":
                print("Machine deactivated.")
                return
            variable = variable_text
        else:
            variable_text = _read("Variable [x]: ")
            if variable_text is None or variable_text.lower() == "quit":
                print("Machine deactivated.")
                return
            variable = variable_text or "x"

        try:
            print(format_results(differentiate(expression, variable, count), variable))
        except DifferentiatorError as exc:
            print(f"{exc}\nReturning to cycle.")
        except Exception as exc:  # Defensive clean exit for unexpected symbolic failures.
            print(f"System Error: {exc}\nReturning to cycle.")
        print()


if __name__ == "__main__":
    run_cli()
