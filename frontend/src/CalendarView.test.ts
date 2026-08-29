import { describe, expect, it } from "vitest";

import { monthlyPdfSelection } from "./CalendarView";

describe("monthlyPdfSelection", () => {
  it("uses the currently displayed Calendar month", () => {
    expect(monthlyPdfSelection(new Date(2026, 8, 1))).toEqual([2026, 9]);
    expect(monthlyPdfSelection(new Date(2027, 0, 1))).toEqual([2027, 1]);
  });
});
