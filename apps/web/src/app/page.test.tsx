import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import HomePage from "@/app/page";

it("adds a manual vacancy to Jobs, persists it, and starts AI analysis", async () => {
  window.history.replaceState(null, "", "#jobs");
  const requests: Array<{ path: string; method: string; body?: unknown }> = [];
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const requestUrl = typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
    const url = new URL(requestUrl, "http://localhost");
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(String(init.body)) as unknown : undefined;
    requests.push({ path: url.pathname, method, body });

    if (url.pathname === "/parser-search-configs.local.json") return Response.json([]);
    if (url.pathname === "/jobs" && method === "GET") return Response.json([]);
    if (url.pathname === "/jobs" && method === "PUT") return Response.json([]);
    if (url.pathname === "/applications" && method === "GET") return Response.json([]);
    if (url.pathname === "/applications/events" && method === "GET") return Response.json([]);
    if (url.pathname === "/profile" && method === "GET") return Response.json({});
    if (url.pathname === "/settings" && method === "GET") {
      return Response.json({ has_brightdata_api_key: false, brightdata_api_key_preview: "" });
    }
    if (url.pathname === "/jobs/ai-match/run" && method === "POST") {
      return Response.json({
        runId: "manual-match-run",
        status: "queued",
        total: 1,
        processed: 0,
        updatedJobs: [],
      }, { status: 202 });
    }

    throw new Error(`Unhandled request: ${method} ${url.pathname}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<HomePage />);

  fireEvent.click(await screen.findByRole("button", { name: "Add vacancy" }));
  const dialog = screen.getByRole("dialog", { name: "Add vacancy" });
  expect(dialog).toBeInTheDocument();

  fireEvent.change(within(dialog).getByLabelText("Role title *"), {
    target: { value: "Backend Engineer" },
  });
  fireEvent.change(within(dialog).getByLabelText("Company *"), {
    target: { value: "Acme" },
  });
  fireEvent.change(within(dialog).getByLabelText("Location"), {
    target: { value: "Zurich / Remote" },
  });
  fireEvent.change(within(dialog).getByLabelText("Vacancy description *"), {
    target: { value: "Build Python services and maintain PostgreSQL systems. Five years of backend experience required." },
  });
  fireEvent.click(within(dialog).getByRole("button", { name: "Add and analyze" }));

  expect(await screen.findAllByText("Backend Engineer")).not.toHaveLength(0);
  expect(screen.getByRole("button", { name: "Force AI match rerun" })).toBeDisabled();

  await waitFor(() => {
    expect(requests.some((request) => request.path === "/jobs" && request.method === "PUT")).toBe(true);
    expect(requests.some((request) => request.path === "/jobs/ai-match/run" && request.method === "POST")).toBe(true);
  });

  const persistedRequest = requests.find((request) => request.path === "/jobs" && request.method === "PUT");
  const persistedJob = (persistedRequest?.body as { jobs: Array<{ data: { title: string; logo: string } }> }).jobs[0].data;
  expect(persistedJob).toMatchObject({ title: "Backend Engineer", logo: "manual" });

  const analysisRequest = requests.find((request) => request.path === "/jobs/ai-match/run" && request.method === "POST");
  expect((analysisRequest?.body as { jobs: Array<{ data: { overview: string } }> }).jobs[0].data.overview).toContain("Python services");

  const locallyStoredJobs = JSON.parse(window.localStorage.getItem("tasko.importedJobs.v1") ?? "[]") as Array<{ title: string }>;
  expect(locallyStoredJobs.some((job) => job.title === "Backend Engineer")).toBe(true);
});

it("searches LinkedIn and Indeed together when both sources are selected", async () => {
  window.history.replaceState(null, "", "#jobs");
  const requests: Array<{ path: string; method: string }> = [];
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const requestUrl = typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
    const url = new URL(requestUrl, "http://localhost");
    const method = init?.method ?? "GET";
    requests.push({ path: url.pathname, method });

    if (url.pathname === "/parser-search-configs.local.json") return Response.json([]);
    if (url.pathname === "/jobs" && method === "GET") return Response.json([]);
    if (url.pathname === "/applications" && method === "GET") return Response.json([]);
    if (url.pathname === "/applications/events" && method === "GET") return Response.json([]);
    if (url.pathname === "/profile" && method === "GET") return Response.json({});
    if (url.pathname === "/settings" && method === "GET") {
      return Response.json({ has_brightdata_api_key: true, brightdata_api_key_preview: "test...key" });
    }
    if (url.pathname === "/parsers/linkedin/search" && method === "POST") {
      return Response.json({ parser: "linkedin", status: "completed", jobs: [] });
    }
    if (url.pathname === "/parsers/indeed/search" && method === "POST") {
      return Response.json({ parser: "indeed", status: "completed", jobs: [] });
    }

    throw new Error(`Unhandled request: ${method} ${url.pathname}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<HomePage />);

  fireEvent.click(await screen.findByRole("button", { name: "Search vacancies" }));
  const linkedinSource = screen.getByRole("button", { name: /LinkedIn/ });
  const indeedSource = screen.getByRole("button", { name: /Indeed/ });
  expect(linkedinSource).toHaveAttribute("aria-pressed", "true");
  expect(indeedSource).toHaveAttribute("aria-pressed", "false");

  fireEvent.click(indeedSource);
  expect(linkedinSource).toHaveAttribute("aria-pressed", "true");
  expect(indeedSource).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(screen.getByRole("button", { name: "Start search" }));

  await waitFor(() => {
    expect(requests).toContainEqual({ path: "/parsers/linkedin/search", method: "POST" });
    expect(requests).toContainEqual({ path: "/parsers/indeed/search", method: "POST" });
  });
  expect(await screen.findByText("No vacancies returned from LinkedIn + Indeed")).toBeInTheDocument();
});
