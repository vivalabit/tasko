import assert from "node:assert/strict";
import test from "node:test";

import { isGeneratedDocumentOutdated } from "./generation-provenance.ts";

test("treats legacy, pending, and mismatched fingerprints as outdated", () => {
  assert.equal(isGeneratedDocumentOutdated(undefined, "a".repeat(64)), true);
  assert.equal(isGeneratedDocumentOutdated("a".repeat(64), undefined), true);
  assert.equal(isGeneratedDocumentOutdated("a".repeat(64), "b".repeat(64)), true);
  assert.equal(isGeneratedDocumentOutdated("a".repeat(64), "a".repeat(64)), false);
});
