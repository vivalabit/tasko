import { describe, expect, it } from "vitest";

import { getAiSourceLabel } from "@/lib/ai-source";

describe("AI source labels", () => {
  it("uses the selected route in matching and assistant provenance", () => {
    expect(getAiSourceLabel("openclaw_codex")).toBe("Codex credits via OpenClaw");
    expect(getAiSourceLabel("openai_api")).toBe("OpenAI Responses API");
    expect(getAiSourceLabel("local")).toBe("Local fallback");
  });
});
