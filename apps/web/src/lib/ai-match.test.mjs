import assert from "node:assert/strict";
import test from "node:test";

import {
  getAiMatchAnalysisStatus,
  hasCurrentApplicationGuide,
  isLegacyAiMatch,
} from "./ai-match.ts";

test("recognizes ai-match-v1 as an outdated analysis", () => {
  const legacyMatch = {
    version: "ai-match-v1",
    score: 94,
  };

  assert.equal(isLegacyAiMatch(legacyMatch), true);
  assert.equal(getAiMatchAnalysisStatus(legacyMatch), "outdated");
  assert.equal(hasCurrentApplicationGuide(legacyMatch), false);
});

test("does not accept a v3 percentage without an application guide", () => {
  assert.equal(
    getAiMatchAnalysisStatus({ version: "ai-match-v3", score: 91 }),
    "outdated",
  );
  assert.equal(
    getAiMatchAnalysisStatus({ version: "ai-match-v3", applicationGuide: {} }),
    "outdated",
  );
});

test("accepts only an authoritative ai-match-v3 application guide", () => {
  const migratedMatch = {
    version: "ai-match-v3",
    revision: "match-revision",
    fingerprint: "a".repeat(64),
    score: 88,
    applicationGuide: {
      language: "English",
      positioning: "Lead with verified evidence.",
    },
  };

  assert.equal(getAiMatchAnalysisStatus(migratedMatch), "current");
  assert.equal(hasCurrentApplicationGuide(migratedMatch), true);
  assert.equal(
    getAiMatchAnalysisStatus({
      ...migratedMatch,
      revision: undefined,
      fingerprint: undefined,
    }),
    "outdated",
  );
});
