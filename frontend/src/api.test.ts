// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { downloadMonthlyPdf } from "./api";

describe("downloadMonthlyPdf", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("fetches a Blob with credentials and downloads the response filename", async () => {
    const blob = new Blob(["pdf bytes"], { type: "application/pdf" });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: vi.fn().mockResolvedValue(blob),
      headers: new Headers({
        "Content-Disposition": 'attachment; filename="task-schedule-2026-09.pdf"',
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn().mockReturnValue("blob:monthly-pdf");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    await downloadMonthlyPdf(2026, 9);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/tasks/monthly-pdf?year=2026&month=9"),
      { credentials: "include" },
    );
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:monthly-pdf");
  });
});
