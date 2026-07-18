export function isGeneratedDocumentOutdated(
  savedFingerprint: string | null | undefined,
  currentFingerprint: string | null | undefined,
) {
  return !savedFingerprint || !currentFingerprint || savedFingerprint !== currentFingerprint;
}
