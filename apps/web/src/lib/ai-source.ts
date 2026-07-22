export type AiSource = "openclaw_codex" | "openai_api" | "local";
export type AiBackend = Exclude<AiSource, "local">;

export function getAiSourceLabel(source: AiSource | null | undefined): string {
  if (source === "openclaw_codex") return "Codex credits via OpenClaw";
  if (source === "openai_api") return "OpenAI Responses API";
  if (source === "local") return "Local fallback";
  return "Unknown AI route";
}
