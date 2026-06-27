/**
 * Calculator - Sample JavaScript module for mutation testing
 */

function add(a, b) { return a + b; }
function subtract(a, b) { return a - b; }
function multiply(a, b) { return a * b; }
function isGreater(a, b) { return a > b; }
function isEqual(a, b) { return a === b; }
function isAdult(age) { return age >= 18 && age <= 120; }
function hasCredentials(username, password) { return username !== "" && password !== ""; }
function isEnabled() { return true; }
function greet(name) { return name === "" ? "Hello, stranger!" : "Hello, " + name + "!"; }

module.exports = { add, subtract, multiply, isGreater, isEqual, isAdult, hasCredentials, isEnabled, greet };
