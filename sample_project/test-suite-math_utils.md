# Test Suite (Table) — math_utils

| ID | Title | Priority | Preconditions | Steps | Expected |
|----|-------|----------|---------------|-------|----------|
| TC-002 | Verify addition of two positive numbers | High | No specific setup required | 1. Enter 2 and 3 as input<br>2. Click the 'Add' button | The result should be 5.0 |
| TC-003 | Verify subtraction of two positive numbers | High | No specific setup required | 1. Enter 4 and 2 as input<br>2. Click the 'Subtract' button | The result should be 2.0 |
| TC-004 | Verify multiplication of two positive numbers | High | No specific setup required | 1. Enter 5 and 3 as input<br>2. Click the 'Multiply' button | The result should be 15.0 |
| TC-005 | Verify division of two positive numbers | High | No specific setup required | 1. Enter 10 and 2 as input<br>2. Click the 'Divide' button | The result should be 5.0 |
| TC-006 | Verify invalid division by zero | High | No specific setup required | 1. Enter 10 and 0 as input<br>2. Click the 'Divide' button | An error message should appear indicating division by zero is not allowed |
| TC-007 | Verify creating a new account with valid user ID and initial balance | High | No specific setup required | 1. Enter a valid user ID and an initial balance greater than 0<br>2. Click the 'Create Account' button | A success message should appear indicating account created successfully |
| TC-008 | Verify processing a payment with sufficient sender balance | High | No specific setup required | 1. Enter a valid sender ID, receiver ID, and an amount greater than 0<br>2. Click the 'Process Payment' button | A success message should appear indicating payment processed successfully |
| TC-009 | Verify getting a letter grade for score above 90 | High | No specific setup required | 1. Enter a score greater than 90<br>2. Click the 'Get Grade' button | The result should be an A letter grade |