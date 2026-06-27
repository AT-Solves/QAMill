const { add, subtract, multiply, isGreater, isEqual, isAdult, hasCredentials, isEnabled, greet } = require("./calculator");

describe("Calculator", () => {
  it("adds 2 + 3 = 5", () => expect(add(2, 3)).toBe(5));
  it("adds 5 + 0 = 5", () => expect(add(5, 0)).toBe(5));
  it("subtracts 5 - 3 = 2", () => expect(subtract(5, 3)).toBe(2));
  it("multiplies 3 * 4 = 12", () => expect(multiply(3, 4)).toBe(12));
  it("multiplies 5 * 0 = 0", () => expect(multiply(5, 0)).toBe(0));
  it("isGreater(5, 3) = true", () => expect(isGreater(5, 3)).toBe(true));
  it("isGreater(2, 5) = false", () => expect(isGreater(2, 5)).toBe(false));
  it("isEqual(5, 5) = true", () => expect(isEqual(5, 5)).toBe(true));
  it("isEqual(5, 3) = false", () => expect(isEqual(5, 3)).toBe(false));
  it("isAdult(25) = true", () => expect(isAdult(25)).toBe(true));
  it("isAdult(17) = false", () => expect(isAdult(17)).toBe(false));
  it("isAdult(121) = false", () => expect(isAdult(121)).toBe(false));
  it("hasCredentials('john', 'pass') = true", () => expect(hasCredentials("john", "pass")).toBe(true));
  it("hasCredentials('', 'pass') = false", () => expect(hasCredentials("", "pass")).toBe(false));
  it("isEnabled() = true", () => expect(isEnabled()).toBe(true));
  it("greet('Alice') = 'Hello, Alice!'", () => expect(greet("Alice")).toBe("Hello, Alice!"));
  it("greet('') = 'Hello, stranger!'", () => expect(greet("")).toBe("Hello, stranger!"));
});
