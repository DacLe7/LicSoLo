import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { RUNNER_EVENT, RUNNER_LABEL } from "../src/config";

describe("capacitor.config.ts khớp src/config.ts", () => {
  const cfg = readFileSync(new URL("../capacitor.config.ts", import.meta.url), "utf8");
  it("nhãn và sự kiện của runner nền", () => {
    expect(cfg).toContain(`label: "${RUNNER_LABEL}"`);
    expect(cfg).toContain(`event: "${RUNNER_EVENT}"`);
    expect(cfg).toContain('src: "runners/runner.js"');
  });
});
