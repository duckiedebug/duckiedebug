ConOps(day by day operations):

Operators:

Technicians
Engineers
Professors

Daily Operations:

* Activation
- access as CLI
- Users chooses between partial differentiation and normal differentiation

* Cycle
- User inputs amount of times expression will be differentiated
- User inputs expression
- Machine outputs f', f'', f''', ... n number of times (n being the number of times the user chooses to have the expression differentiated)

* Deactivation
- User inputs quit
- Machine closes

Exception Handling:

Zero Division Error
Truncation Error
Round Off Error
Step Size Dilemma
Expression Swelling
Underflow/Overflow
Simplification Error
Accumulation Of Floating Point Drift
Discontinuity and Non-Differentiable Points
Vanishing and Exploding Gradients

Requirements(Testable statements for system operations and constraints):

MUST:

REQ-001: The system shall output the differentiated expression along with the general solution.
REQ-002: When hit with any of the said errors, the system shall halt all processes and output cleanly the error then return to the cycle.
REQ-003: The system shall have a simple interface for the user.

SHOULD:

REQ-004: The system shall not exceed processing time of 15 seconds.
REQ-005: The system shall time its processing time.
REQ-006: The system shall handle all errors through a written print statement.

COULD:

REQ-007: The system shall record sessions using streamlit.
REQ-008: The system shall use its own algorithms for solving derivatives.
