# Manual Test Suite — math_utils

## TC-002 — Add two positive numbers
**Priority:** Low
**Preconditions:** Both input values are positive
**Steps:**
1. Enter a and b as 2.5 and 3.5 respectively
2. Click the 'Add' button
**Expected:** The result is 6.0

## TC-003 — Divide by zero raises an error
**Priority:** High
**Preconditions:** Numerator and denominator are not zero
**Steps:**
1. Enter a as 5.0 and b as 0.0
2. Click the 'Divide' button
**Expected:** A ZeroDivisionError is raised

## TC-004 — Get account balance returns correct value
**Priority:** Medium
**Preconditions:** Account exists and has a balance
**Steps:**
1. Enter account ID as 1
2. Click the 'Get Account Balance' button
**Expected:** The result is 1000.0

## TC-005 — Transfer funds between accounts
**Priority:** High
**Preconditions:** Both source and destination accounts exist
**Steps:**
1. Enter the from account as 1, to account as 2, and amount as 500.0
2. Click the 'Transfer Funds' button
**Expected:** The result is a success message

## TC-006 — Safe divide returns correct value
**Priority:** Medium
**Preconditions:** Denominator is not zero
**Steps:**
1. Enter numerator as 10.0 and denominator as 2.0
2. Click the 'Safe Divide' button
**Expected:** The result is 5.0

## TC-007 — Get user status returns correct value
**Priority:** Medium
**Preconditions:** User ID exists and has a valid status
**Steps:**
1. Enter the user ID as 1
2. Click the 'Get User Status' button
**Expected:** The result is 'active'

## TC-008 — Create account returns correct values
**Priority:** High
**Preconditions:** User ID exists and has a valid initial balance
**Steps:**
1. Enter the user ID as 1, initial balance as 1000.0, and account type as 'checking'
2. Click the 'Create Account' button
**Expected:** The result is a new account dictionary with correct values

## TC-009 — Process payment between accounts
**Priority:** High
**Preconditions:** Both sender and receiver accounts exist and have valid balances
**Steps:**
1. Enter the sender ID as 1, receiver ID as 2, and amount as 500.0
2. Click the 'Process Payment' button
**Expected:** The result is True

## TC-010 — Find first positive number in list returns correct value
**Priority:** Medium
**Preconditions:** List contains at least one positive number
**Steps:**
1. Enter the following numbers: -1, 2, -3, 4
2. Click the 'Find First Positive' button
**Expected:** The result is 2
