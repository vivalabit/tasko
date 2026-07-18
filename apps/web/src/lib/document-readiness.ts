type GeneratedDocumentVersionLike = {
  version: number;
  factualValidation?: { status?: string };
  visualValidation?: { status?: string };
  hasRenderedDocx?: boolean;
};

type GeneratedDocumentLike = {
  currentVersion: number;
  versions: GeneratedDocumentVersionLike[];
};

export function getDocumentVersionDownloadWarnings(
  version: GeneratedDocumentVersionLike | undefined,
  isOutdated = false,
) {
  const warnings: string[] = [];

  if (isOutdated) warnings.push("its generation fingerprint is outdated");
  if (version?.factualValidation?.status !== "passed") {
    warnings.push("factual validation has not passed");
  }
  if (version?.visualValidation?.status !== "passed") {
    warnings.push("visual validation has not passed");
  }
  if (version?.hasRenderedDocx !== true) {
    warnings.push("a rendered DOCX is not available");
  }

  return warnings;
}

export function getGeneratedDocumentReadiness(
  document: GeneratedDocumentLike | null | undefined,
  isOutdated: boolean,
) {
  if (!document) {
    return {
      ready: false,
      label: "Not generated",
      currentVersion: undefined,
      warnings: ["the document has not been generated"],
    };
  }

  const currentVersion = document.versions.find(
    (version) => version.version === document.currentVersion,
  );
  const warnings = getDocumentVersionDownloadWarnings(
    currentVersion,
    isOutdated,
  );
  const label = isOutdated
    ? "Outdated"
    : currentVersion?.factualValidation?.status !== "passed" ||
        currentVersion?.visualValidation?.status !== "passed"
      ? "Unvalidated"
      : currentVersion?.hasRenderedDocx !== true
        ? "DOCX missing"
        : "Ready";

  return {
    ready: warnings.length === 0,
    label,
    currentVersion,
    warnings,
  };
}
