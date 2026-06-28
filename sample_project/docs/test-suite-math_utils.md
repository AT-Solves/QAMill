# Test Suite (Table) — math_utils

| ID | Title | Priority | Preconditions | Steps | Expected |
|----|-------|----------|---------------|-------|----------|
| TC-002 | Add two positive numbers | Medium | The add function should be used with valid inputs. | 1. Call add(2.0, 3.0)<br>2. Verify the result is 5.0 | The result is a sum of two input numbers. |
| TC-003 | Subtract a positive number from another positive number | Medium | The subtract function should be used with valid inputs. | 1. Call subtract(4.0, 2.0)<br>2. Verify the result is 2.0 | The result is a difference of two input numbers. |
| TC-004 | Multiply two positive numbers | Medium | The multiply function should be used with valid inputs. | 1. Call multiply(2.0, 3.0)<br>2. Verify the result is 6.0 | The result is a product of two input numbers. |
| TC-005 | Divide by zero returns None | High | The divide function should be used with invalid inputs. | 1. Call divide(4.0, 0.0)<br>2. Verify the result is None | The function correctly handles division by zero. |
| TC-006 | Factorial of 5 is 120 | Medium | The factorial function should be used with valid inputs. | 1. Call factorial(5)<br>2. Verify the result is 120 | The result is the correct factorial value. |
| TC-007 | Percentage calculation for positive values | Medium | The percentage function should be used with valid inputs. | 1. Call percentage(100, 200)<br>2. Verify the result is 50.0 | The result is a correct percentage calculation. |
| TC-008 | Send notification on account creation | High | A new account should be created. | 1. Create an account with user ID 1 and initial balance 1000.0<br>2. Verify a successful notification is sent to the user | The notification is successfully sent upon account creation. |
| TC-009 | Invalid account creation returns error | High | An invalid account should be created. | 1. Try to create an account with user ID -1 and initial balance -1000.0<br>2. Verify an error message is raised | The function correctly handles invalid account creation. |
| TC-010 | Get account balance for valid account | Medium | An existing account should be present. | 1. Get the balance of an existing account with ID 1<br>2. Verify the result is 1000.0 | The function correctly retrieves the account balance. |