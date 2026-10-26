# Symbolic Differentiator CLI

A command-line differentiator for technicians, engineers, and professors. It supports normal and partial differentiation and prints every derivative from `f'` through the requested order.

## Run

```bash
cd /Users/macbookpro/differentiator-cli
python3 differentiator.py
```

Examples: `x^3 + 2*x`, `sin(x) * exp(x)`, and `x^2*y + sin(y)`. Use `quit` at any prompt to deactivate the program.

## Error behaviour

The program uses symbolic—not finite-difference—calculus. Therefore numerical step-size, truncation, round-off, floating-point drift, and vanishing/exploding-gradient issues do not arise during normal operation. Invalid input, zero division, known non-differentiable functions (including `abs`), overflow/arithmetic failures, simplification failures, expression swelling, and a 15-second processing deadline are reported cleanly and return to the next cycle.

## Test

```bash
python3 -m unittest -v
```
