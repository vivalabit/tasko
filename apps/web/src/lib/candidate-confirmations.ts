export type CandidateConfirmationResponse = "yes" | "no" | "partial";

export type CandidateConfirmation = {
  questionId: string;
  requirement: string;
  response: CandidateConfirmationResponse;
  exampleText: string;
  blocking: boolean;
  updatedAt: string;
};

export type CandidateConfirmationQuestion = {
  id: string;
  requirement: string;
  blocking: boolean;
};

export function isMeaningfulCandidateConfirmation(
  confirmation: CandidateConfirmation | undefined,
) {
  if (!confirmation) return false;
  if (confirmation.response === "no") return true;

  const normalized = confirmation.exampleText.trim().replace(/\s+/g, " ");
  const words = normalized.split(" ").filter((word) => /[\p{L}\p{N}]/u.test(word));
  return normalized.length >= 10 && words.length >= 2;
}

export function isCandidateConfirmationComplete(
  question: CandidateConfirmationQuestion,
  confirmation: CandidateConfirmation | undefined,
) {
  if (!confirmation) return !question.blocking;
  return !question.blocking || isMeaningfulCandidateConfirmation(confirmation);
}

export function importLegacyCandidateConfirmations(
  value: unknown,
  questions: CandidateConfirmationQuestion[],
  importedAt = new Date().toISOString(),
) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {} as Record<string, CandidateConfirmation>;
  }

  const legacyAnswers = value as Record<string, unknown>;
  const confirmations: Record<string, CandidateConfirmation> = {};

  for (const question of questions) {
    const legacyAnswer = legacyAnswers[question.id];
    if (typeof legacyAnswer !== "string" || !legacyAnswer.trim()) continue;

    const { response, exampleText } = parseLegacyAnswer(legacyAnswer);
    confirmations[question.id] = {
      questionId: question.id,
      requirement: question.requirement,
      response,
      exampleText,
      blocking: question.blocking,
      updatedAt: importedAt,
    };
  }

  return confirmations;
}

function parseLegacyAnswer(value: string): {
  response: CandidateConfirmationResponse;
  exampleText: string;
} {
  const answer = value.trim();
  const noMatch = answer.match(/^(?:no|нет|nein)\b[\s,:;.-]*/iu);
  if (noMatch) {
    return { response: "no", exampleText: answer.slice(noMatch[0].length).trim() };
  }

  const partialMatch = answer.match(/^(?:partial(?:ly)?|partly|частично|teilweise)\b[\s,:;.-]*/iu);
  if (partialMatch) {
    return { response: "partial", exampleText: answer.slice(partialMatch[0].length).trim() };
  }

  const yesMatch = answer.match(/^(?:yes|да|ja)\b[\s,:;.-]*/iu);
  return {
    response: "yes",
    exampleText: yesMatch ? answer.slice(yesMatch[0].length).trim() : answer,
  };
}
