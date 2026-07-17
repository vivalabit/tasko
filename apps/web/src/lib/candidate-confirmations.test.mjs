import assert from "node:assert/strict";
import test from "node:test";

import {
  importLegacyCandidateConfirmations,
  isCandidateConfirmationComplete,
  isMeaningfulCandidateConfirmation,
} from "./candidate-confirmations.ts";

const questions = [
  { id: "production", requirement: "Production delivery", blocking: true },
  { id: "german", requirement: "German C1", blocking: true },
  { id: "leadership", requirement: "Leadership", blocking: false },
];

test("imports legacy localStorage answers into structured confirmations", () => {
  const imported = importLegacyCandidateConfirmations(
    {
      production: "Yes, shipped a Python service used by three teams.",
      german: "No",
      leadership: "Partial: mentored two colleagues on a project.",
    },
    questions,
    "2026-07-17T10:00:00.000Z",
  );

  assert.equal(imported.production.response, "yes");
  assert.equal(imported.production.exampleText, "shipped a Python service used by three teams.");
  assert.equal(imported.german.response, "no");
  assert.equal(imported.german.exampleText, "");
  assert.equal(imported.leadership.response, "partial");
  assert.equal(imported.production.requirement, "Production delivery");
  assert.equal(imported.production.updatedAt, "2026-07-17T10:00:00.000Z");
});

test("requires a substantive example for blocking yes and partial answers", () => {
  const shortYes = {
    questionId: "production",
    requirement: "Production delivery",
    response: "yes",
    exampleText: "yes",
    blocking: true,
    updatedAt: "",
  };
  const substantivePartial = {
    ...shortYes,
    response: "partial",
    exampleText: "Supported one production rollout with the platform team.",
  };

  assert.equal(isMeaningfulCandidateConfirmation(shortYes), false);
  assert.equal(isCandidateConfirmationComplete(questions[0], shortYes), false);
  assert.equal(isMeaningfulCandidateConfirmation(substantivePartial), true);
  assert.equal(isCandidateConfirmationComplete(questions[0], substantivePartial), true);
  assert.equal(
    isCandidateConfirmationComplete(questions[1], { ...shortYes, response: "no", exampleText: "" }),
    true,
  );
});
