ConOps(day by day operations):

Operators:

Technicians
Engineers
Professors

Daily Operations:

* Activation
- access as CLI
- Users chooses between normal integration, double integration, triple integration, line integration, and surface integration

* Cycle
- User inputs expression
- Machine outputs

* Deactivation
- User inputs quit
- Machine closes

Exception Handling:

Floating Point Round-Off Error
Loss of Significance (Subtractive Cancellation)
Step-Size Dilemma
Sampling Errors (Aliasing)
Ill-Conditioned Functions and Singularities
Infinite Intervals
Implicit Variable Ordering (Iterated Integrals)
Unspecified Domain Constraints
Discontinuity
Underestimation of true Volume/Flux
"Curse of Dimensionality" (grid points required for accurate deterministic quadrature scales exponentially causing memory limits or time out, forcing them to switch to pseudo-random sampling)
Coordinate Transformation Singularities causing Division by Zero Errors
Branch cuts and Vector Discontinuities
Unclosed paths in Green/Stokes loops

Requirements(Testable statements for system operations and constraints):

MUST:

REQ-001: The system shall output the integrated expression.
REQ-002: When hit with any of the said errors, the system shall halt all processes and output cleanly the error then return to the cycle.
REQ-003: The system shall have a simple interface for the user.

SHOULD:

REQ-004: The system shall not exceed processing time of 15 seconds.
REQ-005: The system shall time its processing time.
REQ-006: The system shall handle all errors through a written print statement.

COULD:

REQ-007: The system shall record sessions using streamlit.
REQ-008: The system shall use its own algorithms for solving integrals.
