import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AutoSearchDialog,
  type JobSearchConfig,
  type JobSearchSchedule,
} from "@/components/auto-search-dialog";

const config: JobSearchConfig = {
  id: "config-1",
  name: "Zurich engineering",
  filters: {
    keywords: "Software Engineer",
    location: "Zurich",
    resultsLimit: 40,
    deduplicate: true,
  },
  createdAt: "2026-07-23T08:00:00Z",
  updatedAt: "2026-07-23T08:00:00Z",
};

const schedule: JobSearchSchedule = {
  id: "schedule-1",
  name: "LinkedIn · 13:00",
  configId: config.id,
  sources: ["linkedin"],
  frequency: "weekdays",
  weekdays: [],
  localTime: "13:00:00",
  timezone: "Europe/Zurich",
  aiAnalysisEnabled: true,
  enabled: true,
  nextRunAt: "2026-07-24T11:00:00Z",
  lastRunAt: null,
  createdAt: "2026-07-23T08:00:00Z",
  updatedAt: "2026-07-23T08:00:00Z",
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("AutoSearchDialog", () => {
  it("shows persisted rules and runs one immediately", async () => {
    const requests: Array<{ path: string; method: string }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = new URL(String(input)).pathname;
        const method = init?.method ?? "GET";
        requests.push({ path, method });

        if (path === "/job-search/configs") return response([config]);
        if (path === "/job-search/schedules" && method === "GET") {
          return response([schedule]);
        }
        if (path === `/job-search/schedules/${schedule.id}/run`) {
          return response({
            status: "completed",
            jobsFound: 12,
            jobsAdded: 7,
            warning: null,
          });
        }
        throw new Error(`Unexpected request: ${method} ${path}`);
      }),
    );

    render(<AutoSearchDialog open onClose={vi.fn()} />);

    expect(await screen.findByText(schedule.name)).toBeInTheDocument();
    expect(screen.getByText("LinkedIn")).toBeInTheDocument();
    expect(screen.getByText(config.name)).toBeInTheDocument();
    expect(screen.getByText("Weekdays · 13:00")).toBeInTheDocument();
    expect(screen.getByText("Enabled")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: `Run ${schedule.name} now` }),
    );

    await waitFor(() => {
      expect(requests).toContainEqual({
        path: `/job-search/schedules/${schedule.id}/run`,
        method: "POST",
      });
    });
    expect(
      await screen.findByText(/12 found · 7 added/),
    ).toBeInTheDocument();
  });

  it("duplicates a rule with a different source and time", async () => {
    const schedulePayloads: Array<Record<string, unknown>> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = new URL(String(input)).pathname;
        const method = init?.method ?? "GET";

        if (path === "/job-search/configs") return response([config]);
        if (path === "/job-search/schedules" && method === "GET") {
          return response([schedule]);
        }
        if (path === "/job-search/schedules" && method === "POST") {
          schedulePayloads.push(JSON.parse(String(init?.body)));
          return response({
            ...schedule,
            ...schedulePayloads.at(-1),
            id: "schedule-2",
          });
        }
        throw new Error(`Unexpected request: ${method} ${path}`);
      }),
    );

    render(<AutoSearchDialog open onClose={vi.fn()} />);
    await screen.findByText(schedule.name);

    fireEvent.click(
      screen.getByRole("button", { name: `Duplicate ${schedule.name}` }),
    );
    expect(
      screen.getByRole("dialog", { name: "Duplicate auto-search" }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Rule name"), {
      target: { value: "Indeed · 15:00" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "LinkedIn" }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Indeed" }),
    );
    fireEvent.change(screen.getByLabelText("Local time"), {
      target: { value: "15:00" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Create duplicate" }),
    );

    await waitFor(() => expect(schedulePayloads).toHaveLength(1));
    expect(schedulePayloads[0]).toMatchObject({
      name: "Indeed · 15:00",
      configId: config.id,
      sources: ["indeed"],
      frequency: "weekdays",
      localTime: "15:00:00",
      timezone: "Europe/Zurich",
      aiAnalysisEnabled: true,
      enabled: true,
    });
  });

  it("creates a reusable config together with a new rule", async () => {
    const writes: Array<{
      path: string;
      body: Record<string, unknown>;
    }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = new URL(String(input)).pathname;
        const method = init?.method ?? "GET";

        if (method === "GET" && path === "/job-search/configs") {
          return response([]);
        }
        if (method === "GET" && path === "/job-search/schedules") {
          return response([]);
        }
        if (method === "POST" && path === "/job-search/configs") {
          const body = JSON.parse(String(init?.body));
          writes.push({ path, body });
          return response({ ...config, ...body });
        }
        if (method === "POST" && path === "/job-search/schedules") {
          const body = JSON.parse(String(init?.body));
          writes.push({ path, body });
          return response({ ...schedule, ...body });
        }
        throw new Error(`Unexpected request: ${method} ${path}`);
      }),
    );

    render(<AutoSearchDialog open onClose={vi.fn()} />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Create first rule" }),
    );

    fireEvent.change(screen.getByLabelText("Rule name"), {
      target: { value: "Daily backend roles" },
    });
    fireEvent.change(screen.getByLabelText("Config name"), {
      target: { value: "Backend roles" },
    });
    fireEvent.change(screen.getByLabelText("Keywords"), {
      target: { value: "Backend Engineer" },
    });
    fireEvent.change(screen.getByLabelText("Location"), {
      target: { value: "Remote" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Create auto-search" }),
    );

    await waitFor(() => expect(writes).toHaveLength(2));
    expect(writes[0]).toEqual({
      path: "/job-search/configs",
      body: {
        name: "Backend roles",
        filters: {
          keywords: "Backend Engineer",
          location: "Remote",
          resultsLimit: 50,
          deduplicate: true,
        },
      },
    });
    expect(writes[1]).toMatchObject({
      path: "/job-search/schedules",
      body: {
        name: "Daily backend roles",
        configId: config.id,
        sources: ["linkedin"],
      },
    });
  });
});

function response(payload: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}
