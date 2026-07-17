export const generationFingerprintVersion = "generation-fingerprint-v1" as const;

export type GenerationFingerprintInputs = {
  vacancy: unknown;
  profile: unknown;
  applicationGuide: unknown;
  sourceDocument: {
    id: string;
    title: string;
    category: string;
    fileName: string;
    fileType: string;
    uploadedAt: string;
    dataUrl: string;
  };
  language: string;
  confirmations: unknown[];
};

export type GenerationInputVersions = {
  fingerprintVersion: typeof generationFingerprintVersion;
  vacancy: string;
  profile: string;
  applicationGuide: string;
  sourceDocument: {
    id: string;
    title: string;
    category: string;
    fileName: string;
    fileType: string;
    uploadedAt: string;
    fingerprint: string;
  };
  language: string;
  confirmations: string;
};

function canonicalize(value: unknown): unknown {
  if (value === undefined || (typeof value === "number" && !Number.isFinite(value))) return null;
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
        .map(([key, nestedValue]) => [key, canonicalize(nestedValue)]),
    );
  }
  return value;
}

function canonicalJson(value: unknown) {
  return JSON.stringify(canonicalize(value));
}

async function sha256(value: unknown) {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function normalizeConfirmations(confirmations: unknown[]) {
  return confirmations
    .map((confirmation) => canonicalize(confirmation))
    .sort((left, right) => {
      const leftJson = canonicalJson(left);
      const rightJson = canonicalJson(right);
      return leftJson < rightJson ? -1 : leftJson > rightJson ? 1 : 0;
    });
}

export async function createGenerationProvenance(inputs: GenerationFingerprintInputs) {
  const normalizedInputs = {
    vacancy: inputs.vacancy,
    profile: inputs.profile,
    applicationGuide: inputs.applicationGuide,
    sourceDocument: {
      id: inputs.sourceDocument.id,
      title: inputs.sourceDocument.title,
      category: inputs.sourceDocument.category,
      fileName: inputs.sourceDocument.fileName,
      dataUrl: inputs.sourceDocument.dataUrl,
    },
    language: inputs.language.trim(),
    confirmations: normalizeConfirmations(inputs.confirmations),
  };
  const [generationFingerprint, vacancy, profile, applicationGuide, sourceDocument, language, confirmations] = await Promise.all([
    sha256(normalizedInputs),
    sha256(normalizedInputs.vacancy),
    sha256(normalizedInputs.profile),
    sha256(normalizedInputs.applicationGuide),
    sha256(normalizedInputs.sourceDocument),
    sha256(normalizedInputs.language),
    sha256(normalizedInputs.confirmations),
  ]);

  return {
    generationFingerprint,
    inputVersions: {
      fingerprintVersion: generationFingerprintVersion,
      vacancy,
      profile,
      applicationGuide,
      sourceDocument: {
        id: inputs.sourceDocument.id,
        title: inputs.sourceDocument.title,
        category: inputs.sourceDocument.category,
        fileName: inputs.sourceDocument.fileName,
        fileType: inputs.sourceDocument.fileType,
        uploadedAt: inputs.sourceDocument.uploadedAt,
        fingerprint: sourceDocument,
      },
      language,
      confirmations,
    } satisfies GenerationInputVersions,
  };
}

export function isGeneratedDocumentOutdated(
  savedFingerprint: string | null | undefined,
  currentFingerprint: string | null | undefined,
) {
  return !savedFingerprint || !currentFingerprint || savedFingerprint !== currentFingerprint;
}
