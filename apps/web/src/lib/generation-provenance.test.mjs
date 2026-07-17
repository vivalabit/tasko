import assert from "node:assert/strict";
import test from "node:test";

import {
  createGenerationProvenance,
  isGeneratedDocumentOutdated,
} from "./generation-provenance.ts";

function inputs() {
  return {
    vacancy: { id: "job-1", title: "Designer", requirements: ["Figma"] },
    profile: { name: "Ada", skills: ["Figma", "Research"] },
    applicationGuide: { positioning: "Lead with research", version: "v3" },
    sourceDocument: {
      id: "source-1",
      title: "Main CV",
      category: "CV / Resume",
      fileName: "cv.docx",
      fileType: "application/docx",
      uploadedAt: "2026-07-17T10:00:00Z",
      dataUrl: "data:application/docx;base64,AAAA",
    },
    language: "English",
    confirmations: [
      { questionId: "q-2", response: "no", exampleText: "" },
      { questionId: "q-1", response: "yes", exampleText: "Led five studies" },
    ],
  };
}

test("creates a stable fingerprint and component input versions", async () => {
  const first = await createGenerationProvenance(inputs());
  const reordered = inputs();
  reordered.vacancy = { requirements: ["Figma"], title: "Designer", id: "job-1" };
  reordered.confirmations.reverse();
  const second = await createGenerationProvenance(reordered);

  assert.match(first.generationFingerprint, /^[a-f0-9]{64}$/);
  assert.equal(first.generationFingerprint, second.generationFingerprint);
  assert.equal(first.inputVersions.fingerprintVersion, "generation-fingerprint-v1");
  assert.equal(first.inputVersions.sourceDocument.fileName, "cv.docx");
  assert.match(first.inputVersions.sourceDocument.fingerprint, /^[a-f0-9]{64}$/);
});

test("changes when any generation input changes", async () => {
  const baseline = await createGenerationProvenance(inputs());
  const mutations = [
    (value) => { value.vacancy.title = "Staff Designer"; },
    (value) => { value.profile.name = "Grace"; },
    (value) => { value.applicationGuide.positioning = "Lead with systems"; },
    (value) => { value.sourceDocument.dataUrl += "BBBB"; },
    (value) => { value.language = "German"; },
    (value) => { value.confirmations[0].response = "partial"; },
  ];

  for (const mutate of mutations) {
    const changed = inputs();
    mutate(changed);
    const provenance = await createGenerationProvenance(changed);
    assert.notEqual(provenance.generationFingerprint, baseline.generationFingerprint);
  }
});

test("treats legacy, pending, and mismatched fingerprints as outdated", () => {
  assert.equal(isGeneratedDocumentOutdated(undefined, "a".repeat(64)), true);
  assert.equal(isGeneratedDocumentOutdated("a".repeat(64), undefined), true);
  assert.equal(isGeneratedDocumentOutdated("a".repeat(64), "b".repeat(64)), true);
  assert.equal(isGeneratedDocumentOutdated("a".repeat(64), "a".repeat(64)), false);
});
