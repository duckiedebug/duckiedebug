#!/usr/bin/env python3
"""A small, timed CLI for symbolic single, multiple, line, and surface integrals."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import re
import sys
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from time import monotonic
from typing import Any

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


MAX_PROCESSING_SECONDS = 15.0
MAX_EXPRESSION_LENGTH = 1_000
TRANSFORMATIONS = standard_transformations + (convert_xor, implicit_multiplication_application)


class IntegrationError(Exception):
    """Expected, user-facing error that ends one integration cycle."""


class ParseError(IntegrationError):
    pass


class FloatingPointRoundoffError(IntegrationError):
    pass


class LossOfSignificanceError(IntegrationError):
    pass


class StepSizeError(IntegrationError):
    pass


class AliasingError(IntegrationError):
    pass


class IllConditionedError(IntegrationError):
    pass


class InfiniteIntervalError(IntegrationError):
    pass


class VariableOrderingError(IntegrationError):
    pass


class DomainConstraintError(IntegrationError):
    pass


class DiscontinuityError(IntegrationError):
    pass


class VolumeFluxUnderestimateError(IntegrationError):
    pass


class CurseOfDimensionalityError(IntegrationError):
    pass


class CoordinateSingularityError(IntegrationError):
    pass


class BranchCutError(IntegrationError):
    pass


class UnclosedPathError(IntegrationError):
    pass


class IntegrationFailureError(IntegrationError):
    pass


class IntegrationMode(StrEnum):
    NORMAL = "normal"
    DOUBLE = "double"
    TRIPLE = "triple"
    LINE = "line"
    SURFACE = "surface"


@dataclass(frozen=True)
class IntegrationRequest:
    mode: IntegrationMode
    expression: str = ""
    variables: tuple[str, ...] = ()
    bounds: tuple[str, ...] = ()
    field: str = ""
    parametrization: str = ""
    closed: bool = False


@dataclass(frozen=True)
class IntegrationResult:
    mode: str
    integrated_expression: str
    elapsed_seconds: float


def integrate_with_timeout(
    request: IntegrationRequest,
    timeout_seconds: float = MAX_PROCESSING_SECONDS,
) -> IntegrationResult:
    """Run one request in an isolated process and enforce the time limit."""
    started = monotonic()
    queue: mp.Queue[dict[str, Any]] = mp.Queue(maxsize=1)
    process = mp.Process(target=_worker, args=(request, queue))
    process.start()
    process.join(timeout_seconds)
    elapsed = monotonic() - started
    if process.is_alive():
        process.terminate()
        process.join()
        raise TimeoutError(f"Processing exceeded {timeout_seconds:g} seconds; operation halted.")

    try:
        payload = queue.get(timeout=0.5)
    except Exception as error:
        raise IntegrationFailureError("The integration worker stopped without a result.") from error
    if not payload["ok"]:
        raise _restore_error(payload["type"], payload["message"])
    return IntegrationResult(request.mode.value, payload["result"], elapsed)


def _worker(request: IntegrationRequest, queue: mp.Queue) -> None:
    try:
        result = _integrate(request)
        queue.put({"ok": True, "result": str(result)})
    except FloatingPointError as error:
        queue.put({"ok": False, "type": "FloatingPointRoundoffError", "message": str(error)})
    except MemoryError as error:
        queue.put({"ok": False, "type": "CurseOfDimensionalityError", "message": "Grid or symbolic state exceeded available memory."})
    except ZeroDivisionError as error:
        queue.put({"ok": False, "type": "CoordinateSingularityError", "message": "A coordinate transformation divided by zero."})
    except OverflowError as error:
        queue.put({"ok": False, "type": "IllConditionedError", "message": "The calculation overflowed and is numerically ill-conditioned."})
    except Exception as error:
        queue.put({"ok": False, "type": type(error).__name__, "message": str(error)})


def _restore_error(error_type: str, message: str) -> Exception:
    error_class = {
        name: value
        for name, value in globals().items()
        if isinstance(value, type) and issubclass(value, IntegrationError)
    }.get(error_type, IntegrationFailureError)
    return error_class(message)


def _safe_locals(names: list[str]) -> dict[str, Any]:
    local: dict[str, Any] = {
        "E": sp.E,
        "I": sp.I,
        "pi": sp.pi,
        "oo": sp.oo,
        "inf": sp.oo,
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
        "Abs": sp.Abs,
        "Integer": sp.Integer,
        "Float": sp.Float,
        "Rational": sp.Rational,
    }
    for name in names:
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise ParseError(f"Invalid variable name: {name!r}.")
        local[name] = sp.Symbol(name, real=True)
    return local


def _parse(text: str, names: list[str]) -> sp.Expr:
    text = text.strip()
    if not text or len(text) > MAX_EXPRESSION_LENGTH:
        raise ParseError("Expression is empty or exceeds the 1,000-character limit.")
    if "__" in text or any(mark in text for mark in ("[", "]", "{" , "}")):
        raise ParseError("Only mathematical expressions are accepted.")
    try:
        value = parse_expr(
            text,
            transformations=TRANSFORMATIONS,
            evaluate=True,
            local_dict=_safe_locals(names),
            global_dict={"__builtins__": {}},
        )
    except (SyntaxError, TypeError, ValueError, NameError, ZeroDivisionError) as error:
        raise ParseError(f"Invalid mathematical expression: {error}") from error
    if not isinstance(value, sp.Expr):
        raise ParseError("Input must be a mathematical expression.")
    if value.has(sp.zoo, sp.nan):
        raise CoordinateSingularityError("The expression contains division by zero or an undefined value.")
    return value


def _split_components(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(text):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                raise ParseError("Unbalanced parentheses in vector input.")
        elif character == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if depth:
        raise ParseError("Unbalanced parentheses in vector input.")
    parts.append(text[start:].strip())
    if any(not part for part in parts):
        raise ParseError("Vector components cannot be empty.")
    return parts


def _parse_bounds(bounds: tuple[str, ...], variables: tuple[str, ...]) -> list[tuple[sp.Symbol, Any, Any]]:
    if not bounds:
        return []
    if len(bounds) != len(variables):
        raise VariableOrderingError("Every integration variable needs exactly one lower and upper bound.")
    parsed: list[tuple[sp.Symbol, Any, Any]] = []
    for variable, spec in zip(variables, bounds):
        if ":" not in spec:
            raise ParseError(f"Bound for {variable} must use lower:upper notation.")
        lower_text, upper_text = spec.split(":", 1)
        lower = _parse(lower_text, list(variables))
        upper = _parse(upper_text, list(variables))
        if lower.free_symbols or upper.free_symbols:
            raise DomainConstraintError("Bounds must be numeric or ±infinity; symbolic domain constraints are unspecified.")
        if lower == sp.oo or upper == -sp.oo:
            raise DomainConstraintError("Bounds must run from a lower endpoint to an upper endpoint.")
        if lower.is_finite and upper.is_finite and bool(sp.ask(sp.Q.gt(lower, upper))):
            raise DomainConstraintError(f"Lower bound exceeds upper bound for {variable}.")
        parsed.append((sp.Symbol(variable, real=True), lower, upper))
    return parsed


def _check_domain(expression: sp.Expr, variable: sp.Symbol, lower: Any, upper: Any) -> None:
    if not (lower.is_finite and upper.is_finite):
        return
    try:
        domain = sp.calculus.util.continuous_domain(expression, variable, sp.S.Reals)
        interval = sp.Interval(lower, upper)
        if not interval.is_subset(domain):
            raise DomainConstraintError(
                f"The integrand is discontinuous or singular inside the {variable} interval."
            )
    except DomainConstraintError:
        raise
    except Exception as error:
        raise DomainConstraintError(f"The real domain of the integrand is unspecified for {variable}.") from error


def _check_result(result: sp.Expr, has_infinite_bound: bool) -> sp.Expr:
    if result.has(sp.nan, sp.zoo):
        raise FloatingPointRoundoffError("The integrated result is not a finite number or expression.")
    if result.has(sp.oo, -sp.oo):
        if has_infinite_bound:
            raise InfiniteIntervalError("The improper integral diverges on the requested infinite interval.")
        raise IllConditionedError("The integral contains a singular or unbounded result.")
    if result.has(sp.Integral):
        raise IntegrationFailureError("The integrator could not resolve the requested expression.")
    if result.has(sp.I) and not result.is_real:
        raise BranchCutError("The result crosses a complex branch cut; specify a real-valued domain.")
    return sp.simplify(result)


def _integrate(request: IntegrationRequest) -> sp.Expr:
    mode = IntegrationMode(request.mode)
    if mode is IntegrationMode.NORMAL:
        return _normal(request)
    if mode in (IntegrationMode.DOUBLE, IntegrationMode.TRIPLE):
        return _multiple(request, mode)
    if mode is IntegrationMode.LINE:
        return _line(request)
    return _surface(request)


def _normal(request: IntegrationRequest) -> sp.Expr:
    variables = request.variables or ("x",)
    if len(variables) != 1:
        raise VariableOrderingError("Normal integration requires exactly one variable.")
    variable = sp.Symbol(variables[0], real=True)
    expression = _parse(request.expression, list(variables))
    if expression.free_symbols - {variable}:
        raise VariableOrderingError("The expression contains variables not declared for integration.")
    bounds = _parse_bounds(request.bounds, variables)
    if not bounds:
        result = sp.integrate(expression, variable)
        return _check_result(result, False)
    _, lower, upper = bounds[0]
    _check_domain(expression, variable, lower, upper)
    return _check_result(sp.integrate(expression, (variable, lower, upper)), not lower.is_finite or not upper.is_finite)


def _multiple(request: IntegrationRequest, mode: IntegrationMode) -> sp.Expr:
    dimension = 2 if mode is IntegrationMode.DOUBLE else 3
    if len(request.variables) != dimension:
        raise VariableOrderingError(f"{mode.value.title()} integration requires {dimension} explicitly ordered variables.")
    if len(set(request.variables)) != dimension:
        raise VariableOrderingError("Integration variables must be unique and explicitly ordered.")
    expression = _parse(request.expression, list(request.variables))
    variables = tuple(sp.Symbol(name, real=True) for name in request.variables)
    if expression.free_symbols - set(variables):
        raise VariableOrderingError("The expression contains variables not declared for integration.")
    bounds = _parse_bounds(request.bounds, request.variables)
    for variable, lower, upper in bounds:
        _check_domain(expression, variable, lower, upper)
    result = expression
    if bounds:
        for variable, lower, upper in reversed(bounds):
            result = sp.integrate(result, (variable, lower, upper))
    else:
        for variable in reversed(variables):
            result = sp.integrate(result, variable)
    return _check_result(result, any(not lower.is_finite or not upper.is_finite for _, lower, upper in bounds))


def _line(request: IntegrationRequest) -> sp.Expr:
    if not request.field or not request.parametrization:
        raise ParseError("Line integration requires a vector field and a parametrization.")
    if len(request.variables) != 1:
        raise VariableOrderingError("Line integration requires exactly one ordered parameter.")
    parameter = sp.Symbol(request.variables[0], real=True)
    field_parts = _split_components(request.field)
    coordinate_parts = _split_components(request.parametrization)
    names = list({name for part in field_parts + coordinate_parts for name in re.findall(r"[A-Za-z_]\w*", part)})
    names.append(parameter.name)
    field = [_parse(part, names) for part in field_parts]
    coordinates = [_parse(part, names) for part in coordinate_parts]
    if len(field) != len(coordinates) or len(field) not in (2, 3):
        raise VariableOrderingError("Line fields and paths must both have two or three components.")
    mapping = {sp.Symbol(name, real=True): value for name, value in zip(sorted({str(s) for expr in coordinates for s in expr.free_symbols if s != parameter}), [*coordinates])}
    # The normal case has coordinates named x,y,z. Preserve the declared component order.
    coordinate_names = [sp.Symbol(name, real=True) for name in ("x", "y", "z")[: len(coordinates)]]
    mapping = dict(zip(coordinate_names, coordinates))
    substituted = [component.subs(mapping) for component in field]
    derivative = sp.Matrix(coordinates).diff(parameter)
    integrand = sp.Matrix(substituted).dot(derivative)
    bounds = _parse_bounds(request.bounds, (parameter.name,))
    if not bounds:
        raise ParseError("Line integration requires parameter bounds in lower:upper notation.")
    _, lower, upper = bounds[0]
    if request.closed and any(sp.simplify(point.subs(parameter, lower) - point.subs(parameter, upper)) != 0 for point in coordinates):
        raise UnclosedPathError("The requested Green/Stokes path is not closed.")
    _check_domain(integrand, parameter, lower, upper)
    return _check_result(sp.integrate(integrand, (parameter, lower, upper)), not lower.is_finite or not upper.is_finite)


def _surface(request: IntegrationRequest) -> sp.Expr:
    if not request.field or not request.parametrization:
        raise ParseError("Surface integration requires a vector field and a parametrization.")
    if len(request.variables) != 2:
        raise VariableOrderingError("Surface integration requires two ordered parameters, for example u,v.")
    field_parts = _split_components(request.field)
    coordinate_parts = _split_components(request.parametrization)
    if len(field_parts) != 3 or len(coordinate_parts) != 3:
        raise VariableOrderingError("Surface flux requires three field and three parametrization components.")
    names = list({name for part in field_parts + coordinate_parts for name in re.findall(r"[A-Za-z_]\w*", part)}) + list(request.variables)
    field = [_parse(part, names) for part in field_parts]
    u, v = (sp.Symbol(name, real=True) for name in request.variables)
    coordinates = [_parse(part, names) for part in coordinate_parts]
    coordinate_names = [sp.Symbol(name, real=True) for name in ("x", "y", "z")]
    substituted = [component.subs(dict(zip(coordinate_names, coordinates))) for component in field]
    tangent_u = sp.Matrix(coordinates).diff(u)
    tangent_v = sp.Matrix(coordinates).diff(v)
    normal = tangent_u.cross(tangent_v)
    if all(sp.simplify(component) == 0 for component in normal):
        raise CoordinateSingularityError("The coordinate transformation has a zero surface Jacobian.")
    flux = sp.Matrix(substituted).dot(normal)
    bounds = _parse_bounds(request.bounds, request.variables)
    if len(bounds) != 2:
        raise ParseError("Surface integration requires u and v bounds in lower:upper notation.")
    for variable, lower, upper in bounds:
        _check_domain(flux, variable, lower, upper)
    result = flux
    for variable, lower, upper in reversed(bounds):
        result = sp.integrate(result, (variable, lower, upper))
    return _check_result(result, any(not lower.is_finite or not upper.is_finite for _, lower, upper in bounds))


ERROR_LABELS = {
    FloatingPointRoundoffError: "Floating Point Round-Off Error",
    LossOfSignificanceError: "Loss of Significance (Subtractive Cancellation)",
    StepSizeError: "Step-Size Dilemma",
    AliasingError: "Sampling Error (Aliasing)",
    IllConditionedError: "Ill-Conditioned Function or Singularity",
    InfiniteIntervalError: "Infinite Interval",
    VariableOrderingError: "Implicit Variable Ordering (Iterated Integrals)",
    DomainConstraintError: "Unspecified Domain Constraints",
    DiscontinuityError: "Discontinuity",
    VolumeFluxUnderestimateError: "Underestimation of True Volume/Flux",
    CurseOfDimensionalityError: "Curse of Dimensionality",
    CoordinateSingularityError: "Coordinate Transformation Singularity",
    BranchCutError: "Branch Cut or Vector Discontinuity",
    UnclosedPathError: "Unclosed Green/Stokes Path",
}


def error_label(error: Exception) -> str:
    for error_type, label in ERROR_LABELS.items():
        if isinstance(error, error_type):
            return label
    return type(error).__name__


class SessionRecorder:
    def __init__(self, path: Path | None) -> None:
        self.path = path

    def add(self, request: IntegrationRequest, result: IntegrationResult) -> None:
        if self.path is None:
            return
        records: list[dict[str, Any]] = []
        if self.path.exists():
            try:
                records = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                records = []
        records.append({"request": asdict(request), "result": asdict(result)})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def _prompt(label: str) -> str | None:
    try:
        answer = input(label).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nMachine deactivated.")
        return None
    return answer


def _request_interactively(mode: IntegrationMode) -> IntegrationRequest | None:
    if mode in (IntegrationMode.NORMAL, IntegrationMode.DOUBLE, IntegrationMode.TRIPLE):
        expression = _prompt("Integrand: ")
        if expression is None:
            return None
        count = {IntegrationMode.NORMAL: 1, IntegrationMode.DOUBLE: 2, IntegrationMode.TRIPLE: 3}[mode]
        variables_text = _prompt(f"Ordered variable(s) ({count}, comma-separated): ")
        if variables_text is None:
            return None
        variables = tuple(item.strip() for item in variables_text.split(",") if item.strip())
        bounds_text = _prompt("Bounds (optional, e.g. 0:1 or x=0:1,y=0:2; blank = indefinite): ")
        if bounds_text is None:
            return None
        bounds = _normalise_bounds(bounds_text, variables)
        return IntegrationRequest(mode, expression, variables, bounds)
    field = _prompt("Vector field components (e.g. x,y or x,y,z): ")
    if field is None:
        return None
    path = _prompt("Parametrization components (e.g. cos(t),sin(t)): ")
    if path is None:
        return None
    parameter_text = _prompt("Ordered parameter(s), e.g. t or u,v: ")
    if parameter_text is None:
        return None
    variables = tuple(item.strip() for item in parameter_text.split(",") if item.strip())
    bounds_text = _prompt("Bounds (e.g. 0:2*pi or u=0:1,v=0:1): ")
    if bounds_text is None:
        return None
    bounds = _normalise_bounds(bounds_text, variables)
    closed = False
    if mode is IntegrationMode.LINE:
        closed = (_prompt("Require a closed Green/Stokes path? [y/N]: ") or "").lower() in {"y", "yes"}
    return IntegrationRequest(mode, variables=variables, bounds=bounds, field=field, parametrization=path, closed=closed)


def _normalise_bounds(text: str, variables: tuple[str, ...]) -> tuple[str, ...]:
    if not text.strip():
        return ()
    entries = [item.strip() for item in text.split(",") if item.strip()]
    if any("=" in entry for entry in entries):
        mapped: dict[str, str] = {}
        for entry in entries:
            name, value = entry.split("=", 1)
            mapped[name.strip()] = value.strip()
        return tuple(mapped.get(variable, "") for variable in variables)
    return tuple(entries)


def _run_one(request: IntegrationRequest, recorder: SessionRecorder) -> None:
    try:
        result = integrate_with_timeout(request)
    except (IntegrationError, ArithmeticError, MemoryError, RecursionError, TimeoutError) as error:
        print(f"ERROR [{error_label(error)}]: {error}")
        print("Cycle halted cleanly; ready for the next operation.")
        return
    print(f"Integrated expression: {result.integrated_expression}")
    print(f"Processing time: {result.elapsed_seconds:.6f} seconds")
    recorder.add(request, result)


def run_cli(history_path: Path | None = None) -> int:
    print("Integration CLI activated.")
    print("Operators: technicians, engineers, professors")
    print("Choose normal, double, triple, line, surface, or quit.")
    recorder = SessionRecorder(history_path)
    while True:
        choice = _prompt("Mode: ")
        if choice is None or choice.lower() in {"quit", "exit", "off"}:
            print("Machine deactivated.")
            return 0
        try:
            mode = IntegrationMode(choice.lower())
        except ValueError:
            print("ERROR [Input]: choose normal, double, triple, line, surface, or quit.")
            continue
        request = _request_interactively(mode)
        if request is None:
            print("Machine deactivated.")
            return 0
        _run_one(request, recorder)


def main() -> int:
    parser = argparse.ArgumentParser(description="Timed CLI for symbolic integration.")
    parser.add_argument("--mode", choices=[mode.value for mode in IntegrationMode])
    parser.add_argument("--expression", help="Integrand for normal, double, or triple integration.")
    parser.add_argument("--variables", help="Ordered variables, comma-separated.")
    parser.add_argument("--bounds", help="Bounds, e.g. 0:1 or x=0:1,y=0:2.")
    parser.add_argument("--field", help="Comma-separated vector field for line/surface integration.")
    parser.add_argument("--parametrization", help="Comma-separated path/surface parametrization.")
    parser.add_argument("--closed", action="store_true", help="Require a closed line path.")
    parser.add_argument("--history", type=Path, help="Optional JSON session history path.")
    args = parser.parse_args()
    if not args.mode:
        return run_cli(args.history)
    mode = IntegrationMode(args.mode)
    variables = tuple(item.strip() for item in (args.variables or "x").split(",") if item.strip())
    bounds = _normalise_bounds(args.bounds or "", variables)
    request = IntegrationRequest(
        mode,
        expression=args.expression or "",
        variables=variables,
        bounds=bounds,
        field=args.field or "",
        parametrization=args.parametrization or "",
        closed=args.closed,
    )
    _run_one(request, SessionRecorder(args.history))
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
