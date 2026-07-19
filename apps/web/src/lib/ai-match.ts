export const currentAiMatchVersion = "ai-match-v3";
export const legacyAiMatchVersion = "ai-match-v1";

type AiMatchLike = {
  version?: unknown;
  revision?: unknown;
  fingerprint?: unknown;
  applicationGuide?: unknown;
} | null | undefined;

export type AiMatchAnalysisStatus = "missing" | "outdated" | "current";

export function getAiMatchAnalysisStatus(aiMatch: AiMatchLike): AiMatchAnalysisStatus {
  if (!aiMatch) return "missing";

  return aiMatch.version === currentAiMatchVersion
    && isAuthoritativeRevision(aiMatch.revision, aiMatch.fingerprint)
    && isApplicationGuide(aiMatch.applicationGuide)
    ? "current"
    : "outdated";
}

export function isLegacyAiMatch(aiMatch: AiMatchLike) {
  return aiMatch?.version === legacyAiMatchVersion;
}

export function hasCurrentApplicationGuide(aiMatch: AiMatchLike) {
  return getAiMatchAnalysisStatus(aiMatch) === "current";
}

function isApplicationGuide(value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;

  const guide = value as { language?: unknown; positioning?: unknown };
  return (
    (guide.language === "English" || guide.language === "German") &&
    typeof guide.positioning === "string" &&
    Boolean(guide.positioning.trim())
  );
}

function isAuthoritativeRevision(revision: unknown, fingerprint: unknown) {
  return (
    typeof revision === "string"
    && Boolean(revision.trim())
    && typeof fingerprint === "string"
    && /^[a-f0-9]{64}$/i.test(fingerprint)
  );
}
