import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { AssistantView } from "@/components/assistant-view";

it("grants versioned server consent with a user TTL before streaming", async () => {
  const requests: Array<{ path: string; method: string; body?: unknown }> = [];
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const requestUrl = typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
    const url = new URL(requestUrl);
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(String(init.body)) as unknown : undefined;
    requests.push({ path: url.pathname, method, body });

    if (url.pathname === "/assistant/conversations" && method === "GET") {
      return Response.json([]);
    }
    if (url.pathname === "/documents" && method === "GET") {
      return Response.json([]);
    }
    if (url.pathname === "/privacy/ai-consent" && method === "GET") {
      return Response.json({
        providerName: "OpenAI",
        currentConsentVersion: "privacy-v1",
        hasCurrentConsent: false,
        retentionDays: 30,
      });
    }
    if (url.pathname === "/privacy/ai-consent" && method === "PUT") {
      return Response.json({
        providerName: "OpenAI",
        currentConsentVersion: "privacy-v1",
        hasCurrentConsent: true,
        retentionDays: (body as { retentionDays: number }).retentionDays,
      });
    }
    if (url.pathname === "/assistant/chat/stream" && method === "POST") {
      return new Response([
        "event: connected\ndata: {}",
        "event: delta\ndata: {\"text\":\"AI reply\",\"offset\":8}",
        "event: done\ndata: {\"metadata\":{}}",
        "",
      ].join("\n\n"), { headers: { "Content-Type": "text/event-stream" } });
    }
    if (url.pathname === "/privacy/ai-consent" && method === "DELETE") {
      return new Response(null, { status: 204 });
    }
    throw new Error(`Unhandled request: ${method} ${url.pathname}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: vi.fn(),
  });

  render(
    <AssistantView
      profile={{
        name: "Alex Morgan",
        current_role: "Designer",
        desired_role: "Senior Designer",
        location: "Zurich",
        headline: "Product designer",
        skills: "Research",
        experience: "Six years",
        education: "BA Design",
        resume_file_name: "resume.docx",
      }}
      jobs={[]}
      applications={[]}
      launch={null}
      onLaunchHandled={vi.fn()}
      onDocumentAttached={vi.fn()}
      onActionApplied={vi.fn()}
    />,
  );

  await screen.findByText("AI consent required");
  fireEvent.change(screen.getByPlaceholderText("Ask anything about your job search…"), {
    target: { value: "Review my profile" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));

  expect(await screen.findByRole("dialog", { name: /Send selected context/ })).toBeInTheDocument();
  fireEvent.change(screen.getByRole("spinbutton", { name: /Keep AI results/ }), {
    target: { value: "7" },
  });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Continue to AI" }));

  expect(await screen.findByText("AI reply")).toBeInTheDocument();
  expect(requests.find((request) => request.path === "/privacy/ai-consent" && request.method === "PUT")?.body).toEqual({
    version: "privacy-v1",
    retentionDays: 7,
  });

  fireEvent.click(screen.getByRole("button", { name: "Revoke AI consent" }));
  await waitFor(() => {
    expect(requests.some((request) => request.path === "/privacy/ai-consent" && request.method === "DELETE")).toBe(true);
    expect(screen.getByText("AI consent required")).toBeInTheDocument();
  });
});
