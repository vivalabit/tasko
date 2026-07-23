"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowLeft,
  CalendarClock,
  Check,
  Copy,
  Edit3,
  LoaderCircle,
  Play,
  Plus,
  Power,
  Trash2,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const sourceOptions = [
  { id: "linkedin", label: "LinkedIn" },
  { id: "indeed", label: "Indeed" },
  { id: "jobs_ch", label: "jobs.ch" },
] as const;
const weekdayOptions = [
  { id: 0, short: "Mon", label: "Monday" },
  { id: 1, short: "Tue", label: "Tuesday" },
  { id: 2, short: "Wed", label: "Wednesday" },
  { id: 3, short: "Thu", label: "Thursday" },
  { id: 4, short: "Fri", label: "Friday" },
  { id: 5, short: "Sat", label: "Saturday" },
  { id: 6, short: "Sun", label: "Sunday" },
] as const;
const timezoneSuggestions = [
  "Europe/Zurich",
  "Europe/Berlin",
  "Europe/London",
  "America/New_York",
  "America/Los_Angeles",
  "Asia/Singapore",
  "UTC",
];

type JobSearchSource = (typeof sourceOptions)[number]["id"];
type JobSearchFrequency = "daily" | "weekdays" | "selected_days";

export type JobSearchConfig = {
  id: string;
  name: string;
  filters: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
};

export type JobSearchSchedule = {
  id: string;
  name: string;
  configId: string;
  sources: JobSearchSource[];
  frequency: JobSearchFrequency;
  weekdays: number[];
  localTime: string;
  timezone: string;
  aiAnalysisEnabled: boolean;
  enabled: boolean;
  nextRunAt: string | null;
  lastRunAt: string | null;
  createdAt: string;
  updatedAt: string;
};

type AutoSearchDialogProps = {
  open: boolean;
  onClose: () => void;
};

type EditorMode = "create" | "edit" | "duplicate";

type ScheduleDraft = {
  id: string;
  mode: EditorMode;
  name: string;
  sources: JobSearchSource[];
  configId: string;
  createConfig: boolean;
  configName: string;
  keywords: string;
  location: string;
  frequency: JobSearchFrequency;
  weekdays: number[];
  localTime: string;
  timezone: string;
  resultsLimit: string;
  deduplicate: boolean;
  aiAnalysisEnabled: boolean;
  enabled: boolean;
};

function defaultDraft(): ScheduleDraft {
  return {
    id: "",
    mode: "create",
    name: "",
    sources: ["linkedin"],
    configId: "",
    createConfig: true,
    configName: "",
    keywords: "",
    location: "",
    frequency: "weekdays",
    weekdays: [0, 1, 2, 3, 4],
    localTime: "09:00",
    timezone: localTimezone(),
    resultsLimit: "50",
    deduplicate: true,
    aiAnalysisEnabled: true,
    enabled: true,
  };
}

export function AutoSearchDialog({
  open,
  onClose,
}: AutoSearchDialogProps) {
  const [view, setView] = useState<"list" | "form">("list");
  const [configs, setConfigs] = useState<JobSearchConfig[]>([]);
  const [schedules, setSchedules] = useState<JobSearchSchedule[]>([]);
  const [draft, setDraft] = useState<ScheduleDraft>(defaultDraft);
  const [status, setStatus] = useState<"idle" | "loading" | "saving" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");
  const [runningScheduleId, setRunningScheduleId] = useState("");
  const [busyScheduleId, setBusyScheduleId] = useState("");

  const configById = useMemo(
    () => new Map(configs.map((config) => [config.id, config])),
    [configs],
  );

  useEffect(() => {
    if (!open) return;
    setView("list");
    setMessage("");
    void loadSearchData();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (view === "form") {
        setView("list");
        setMessage("");
      } else {
        onClose();
      }
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose, open, view]);

  if (!open) return null;

  async function loadSearchData() {
    setStatus("loading");
    try {
      const [nextConfigs, nextSchedules] = await Promise.all([
        requestJson<JobSearchConfig[]>("/job-search/configs"),
        requestJson<JobSearchSchedule[]>("/job-search/schedules"),
      ]);
      setConfigs(nextConfigs);
      setSchedules(nextSchedules);
      setStatus("idle");
    } catch (error) {
      setStatus("error");
      setMessage(errorMessage(error));
    }
  }

  function openCreate() {
    const next = defaultDraft();
    if (configs.length > 0) {
      applyConfigToDraft(next, configs[0]);
      next.createConfig = false;
    }
    setDraft(next);
    setMessage("");
    setView("form");
  }

  function openEdit(schedule: JobSearchSchedule) {
    const config = configById.get(schedule.configId);
    setDraft(draftFromSchedule(schedule, config, "edit"));
    setMessage("");
    setView("form");
  }

  function openDuplicate(schedule: JobSearchSchedule) {
    const config = configById.get(schedule.configId);
    setDraft({
      ...draftFromSchedule(schedule, config, "duplicate"),
      id: "",
      name: `${schedule.name} copy`,
      enabled: true,
    });
    setMessage("");
    setView("form");
  }

  async function saveRule() {
    const validation = validateDraft(draft);
    if (validation) {
      setStatus("error");
      setMessage(validation);
      return;
    }

    setStatus("saving");
    setMessage("");
    try {
      const configId = await saveConfigForDraft(draft, configById);
      const schedulePayload = {
        name: draft.name.trim(),
        configId,
        sources: draft.sources,
        frequency: draft.frequency,
        weekdays:
          draft.frequency === "selected_days" ? draft.weekdays : [],
        localTime: withSeconds(draft.localTime),
        timezone: draft.timezone.trim(),
        aiAnalysisEnabled: draft.aiAnalysisEnabled,
        enabled: draft.enabled,
      };
      if (draft.mode === "edit" && draft.id) {
        await requestJson<JobSearchSchedule>(
          `/job-search/schedules/${encodeURIComponent(draft.id)}`,
          {
            method: "PATCH",
            headers: jsonHeaders,
            body: JSON.stringify(schedulePayload),
          },
        );
      } else {
        await requestJson<JobSearchSchedule>("/job-search/schedules", {
          method: "POST",
          headers: jsonHeaders,
          body: JSON.stringify(schedulePayload),
        });
      }
      setView("list");
      setMessage(
        draft.mode === "edit"
          ? "Auto-search updated"
          : draft.mode === "duplicate"
            ? "Auto-search duplicated"
            : "Auto-search created",
      );
      await loadSearchData();
    } catch (error) {
      setStatus("error");
      setMessage(errorMessage(error));
    }
  }

  async function toggleEnabled(schedule: JobSearchSchedule) {
    setBusyScheduleId(schedule.id);
    setMessage("");
    try {
      const updated = await requestJson<JobSearchSchedule>(
        `/job-search/schedules/${encodeURIComponent(schedule.id)}`,
        {
          method: "PATCH",
          headers: jsonHeaders,
          body: JSON.stringify({ enabled: !schedule.enabled }),
        },
      );
      setSchedules((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusyScheduleId("");
    }
  }

  async function runNow(schedule: JobSearchSchedule) {
    setRunningScheduleId(schedule.id);
    setMessage("");
    try {
      const run = await requestJson<{
        status: string;
        jobsFound: number;
        jobsAdded: number;
        warning?: string | null;
      }>(`/job-search/schedules/${encodeURIComponent(schedule.id)}/run`, {
        method: "POST",
      });
      setMessage(
        [
          `${schedule.name}: ${run.status}`,
          `${run.jobsFound} found`,
          `${run.jobsAdded} added`,
          run.warning,
        ]
          .filter(Boolean)
          .join(" · "),
      );
      await loadSearchData();
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setRunningScheduleId("");
    }
  }

  async function deleteRule(schedule: JobSearchSchedule) {
    if (!window.confirm(`Delete auto-search “${schedule.name}”?`)) return;
    setBusyScheduleId(schedule.id);
    setMessage("");
    try {
      await requestJson<void>(
        `/job-search/schedules/${encodeURIComponent(schedule.id)}`,
        { method: "DELETE" },
      );
      setSchedules((current) =>
        current.filter((item) => item.id !== schedule.id),
      );
      setMessage("Auto-search deleted");
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusyScheduleId("");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/75 p-3 backdrop-blur-sm sm:p-5"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="auto-search-dialog-title"
        className="panel flex max-h-[calc(100vh-24px)] w-full max-w-[1040px] flex-col overflow-hidden border-white/[0.11] bg-[#101720]/98 shadow-[0_28px_90px_rgba(0,0,0,0.62)] sm:max-h-[calc(100vh-40px)]"
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-4 py-4 sm:px-6">
          <div className="flex min-w-0 items-start gap-3">
            {view === "form" ? (
              <button
                type="button"
                aria-label="Back to auto-searches"
                onClick={() => {
                  setView("list");
                  setMessage("");
                }}
                className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-border text-muted transition hover:bg-white/[0.06] hover:text-white"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            ) : (
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-500/15 text-violet-300">
                <CalendarClock className="h-5 w-5" />
              </div>
            )}
            <div className="min-w-0">
              <h2
                id="auto-search-dialog-title"
                className="truncate text-xl font-bold text-white sm:text-2xl"
              >
                {view === "list"
                  ? "Automatic searches"
                  : draft.mode === "edit"
                    ? "Edit auto-search"
                    : draft.mode === "duplicate"
                      ? "Duplicate auto-search"
                      : "New auto-search"}
              </h2>
              <p className="mt-1 text-xs font-medium text-muted sm:text-sm">
                {view === "list"
                  ? "Run vacancy searches on your schedule."
                  : "Each rule has one local run time. Duplicate it to add another time."}
              </p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Close automatic searches"
            onClick={onClose}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted transition hover:bg-white/[0.08] hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        {view === "list" ? (
          <AutoSearchList
            configs={configById}
            schedules={schedules}
            loading={status === "loading"}
            runningScheduleId={runningScheduleId}
            busyScheduleId={busyScheduleId}
            onCreate={openCreate}
            onEdit={openEdit}
            onDuplicate={openDuplicate}
            onRunNow={(schedule) => void runNow(schedule)}
            onDelete={(schedule) => void deleteRule(schedule)}
            onToggleEnabled={(schedule) => void toggleEnabled(schedule)}
          />
        ) : (
          <AutoSearchForm
            draft={draft}
            configs={configs}
            saving={status === "saving"}
            onChange={setDraft}
            onCancel={() => {
              setView("list");
              setMessage("");
            }}
            onSave={() => void saveRule()}
          />
        )}

        {message ? (
          <div
            role={status === "error" ? "alert" : "status"}
            className={cn(
              "shrink-0 border-t border-border px-4 py-2.5 text-xs font-semibold sm:px-6",
              status === "error"
                ? "bg-red-500/8 text-red-200"
                : "bg-white/[0.025] text-[#cbd3df]",
            )}
          >
            {message}
          </div>
        ) : null}
      </section>
    </div>
  );
}

function AutoSearchList({
  configs,
  schedules,
  loading,
  runningScheduleId,
  busyScheduleId,
  onCreate,
  onEdit,
  onDuplicate,
  onRunNow,
  onDelete,
  onToggleEnabled,
}: {
  configs: Map<string, JobSearchConfig>;
  schedules: JobSearchSchedule[];
  loading: boolean;
  runningScheduleId: string;
  busyScheduleId: string;
  onCreate: () => void;
  onEdit: (schedule: JobSearchSchedule) => void;
  onDuplicate: (schedule: JobSearchSchedule) => void;
  onRunNow: (schedule: JobSearchSchedule) => void;
  onDelete: (schedule: JobSearchSchedule) => void;
  onToggleEnabled: (schedule: JobSearchSchedule) => void;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <p className="text-xs font-semibold text-muted">
          {schedules.length} {schedules.length === 1 ? "rule" : "rules"}
        </p>
        <Button size="sm" onClick={onCreate}>
          <Plus className="h-4 w-4" />
          New auto-search
        </Button>
      </div>

      <div className="job-scroll min-h-0 flex-1 overflow-y-auto px-4 pb-5 sm:px-6">
        {loading ? (
          <div className="grid min-h-[280px] place-items-center text-muted">
            <LoaderCircle className="h-6 w-6 animate-spin" />
          </div>
        ) : schedules.length === 0 ? (
          <div className="grid min-h-[300px] place-items-center rounded-xl border border-dashed border-border bg-white/[0.018] p-6 text-center">
            <div>
              <CalendarClock className="mx-auto h-9 w-9 text-muted" />
              <h3 className="mt-3 text-lg font-bold text-white">
                No automatic searches yet
              </h3>
              <p className="mt-1 max-w-md text-sm text-muted">
                Create a rule for each source and local run time you need.
              </p>
              <Button className="mt-5" onClick={onCreate}>
                <Plus className="h-4 w-4" />
                Create first rule
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid gap-3">
            {schedules.map((schedule) => {
              const config = configs.get(schedule.configId);
              const isRunning = runningScheduleId === schedule.id;
              const isBusy = busyScheduleId === schedule.id;
              return (
                <article
                  key={schedule.id}
                  className="rounded-xl border border-border bg-white/[0.025] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.025)]"
                >
                  <div className="grid gap-4 xl:grid-cols-[minmax(180px,1.2fr)_minmax(130px,.8fr)_minmax(150px,1fr)_minmax(170px,1fr)_minmax(165px,1fr)_auto] xl:items-center">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "h-2 w-2 shrink-0 rounded-full",
                            schedule.enabled
                              ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.7)]"
                              : "bg-slate-500",
                          )}
                        />
                        <h3 className="truncate text-sm font-bold text-white">
                          {schedule.name}
                        </h3>
                      </div>
                      <p className="mt-1 text-[11px] text-muted">
                        {schedule.enabled ? "Enabled" : "Paused"}
                      </p>
                    </div>
                    <ListField label="Sources">
                      <div className="flex flex-wrap gap-1">
                        {schedule.sources.map((source) => (
                          <span
                            key={source}
                            className="rounded-md border border-white/[0.08] bg-white/[0.035] px-2 py-1 text-[10px] font-bold text-[#d9e0ea]"
                          >
                            {sourceLabel(source)}
                          </span>
                        ))}
                      </div>
                    </ListField>
                    <ListField label="Config">
                      <span className="line-clamp-2 text-xs font-semibold text-[#d9e0ea]">
                        {config?.name ?? "Missing config"}
                      </span>
                    </ListField>
                    <ListField label="Schedule">
                      <span className="text-xs font-semibold text-[#d9e0ea]">
                        {scheduleLabel(schedule)}
                      </span>
                      <span className="mt-0.5 block text-[10px] text-muted">
                        {schedule.timezone}
                      </span>
                    </ListField>
                    <ListField label="Next run">
                      <span className="text-xs font-semibold text-[#d9e0ea]">
                        {formatNextRun(schedule)}
                      </span>
                    </ListField>
                    <div className="flex flex-wrap items-center gap-1.5 xl:justify-end">
                      <IconAction
                        label={`${schedule.enabled ? "Disable" : "Enable"} ${schedule.name}`}
                        disabled={isBusy}
                        onClick={() => onToggleEnabled(schedule)}
                      >
                        <Power className="h-3.5 w-3.5" />
                      </IconAction>
                      <IconAction
                        label={`Edit ${schedule.name}`}
                        onClick={() => onEdit(schedule)}
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </IconAction>
                      <IconAction
                        label={`Duplicate ${schedule.name}`}
                        onClick={() => onDuplicate(schedule)}
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </IconAction>
                      <IconAction
                        label={`Run ${schedule.name} now`}
                        disabled={isRunning}
                        onClick={() => onRunNow(schedule)}
                      >
                        {isRunning ? (
                          <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Play className="h-3.5 w-3.5" />
                        )}
                      </IconAction>
                      <IconAction
                        label={`Delete ${schedule.name}`}
                        danger
                        disabled={isBusy}
                        onClick={() => onDelete(schedule)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </IconAction>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function AutoSearchForm({
  draft,
  configs,
  saving,
  onChange,
  onCancel,
  onSave,
}: {
  draft: ScheduleDraft;
  configs: JobSearchConfig[];
  saving: boolean;
  onChange: (draft: ScheduleDraft) => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  function patch(update: Partial<ScheduleDraft>) {
    onChange({ ...draft, ...update });
  }

  return (
    <form
      className="job-scroll min-h-0 flex-1 overflow-y-auto"
      onSubmit={(event) => {
        event.preventDefault();
        onSave();
      }}
    >
      <div className="grid gap-5 px-4 py-5 sm:px-6 lg:grid-cols-2">
        <FormSection title="Rule">
          <Field label="Rule name">
            <input
              autoFocus
              aria-label="Rule name"
              value={draft.name}
              onChange={(event) => patch({ name: event.target.value })}
              className={inputClass}
              placeholder="LinkedIn lunchtime search"
            />
          </Field>

          <Field label="Sources">
            <div className="grid grid-cols-3 gap-2">
              {sourceOptions.map((source) => {
                const selected = draft.sources.includes(source.id);
                return (
                  <button
                    key={source.id}
                    type="button"
                    aria-pressed={selected}
                    onClick={() =>
                      patch({
                        sources: selected
                          ? draft.sources.filter((item) => item !== source.id)
                          : [...draft.sources, source.id],
                      })
                    }
                    className={cn(
                      "h-10 rounded-lg border text-xs font-bold transition",
                      selected
                        ? "border-violet-400/70 bg-violet-500/15 text-white"
                        : "border-border bg-white/[0.025] text-muted hover:bg-white/[0.06] hover:text-white",
                    )}
                  >
                    {selected ? <Check className="mr-1 inline h-3.5 w-3.5" /> : null}
                    {source.label}
                  </button>
                );
              })}
            </div>
          </Field>

          <Field label="Enabled">
            <button
              type="button"
              role="switch"
              aria-label="Enabled"
              aria-checked={draft.enabled}
              onClick={() => patch({ enabled: !draft.enabled })}
              className="flex h-10 w-full items-center justify-between rounded-lg border border-border bg-white/[0.025] px-3 text-xs font-bold text-[#dce3ec]"
            >
              Run this rule automatically
              <Toggle enabled={draft.enabled} />
            </button>
          </Field>
        </FormSection>

        <FormSection title="Search config">
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              aria-pressed={!draft.createConfig}
              disabled={configs.length === 0}
              onClick={() => {
                const config =
                  configs.find((item) => item.id === draft.configId) ?? configs[0];
                if (!config) return;
                const next = { ...draft, createConfig: false };
                applyConfigToDraft(next, config);
                onChange(next);
              }}
              className={choiceClass(!draft.createConfig)}
            >
              Existing config
            </button>
            <button
              type="button"
              aria-pressed={draft.createConfig}
              onClick={() => patch({ createConfig: true, configId: "" })}
              className={choiceClass(draft.createConfig)}
            >
              New config
            </button>
          </div>

          {draft.createConfig ? (
            <>
              <Field label="Config name">
                <input
                  aria-label="Config name"
                  value={draft.configName}
                  onChange={(event) => patch({ configName: event.target.value })}
                  className={inputClass}
                  placeholder="Zurich engineering roles"
                />
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Keywords">
                  <input
                    aria-label="Keywords"
                    value={draft.keywords}
                    onChange={(event) => patch({ keywords: event.target.value })}
                    className={inputClass}
                    placeholder="Software Engineer"
                  />
                </Field>
                <Field label="Location">
                  <input
                    aria-label="Location"
                    value={draft.location}
                    onChange={(event) => patch({ location: event.target.value })}
                    className={inputClass}
                    placeholder="Zurich"
                  />
                </Field>
              </div>
            </>
          ) : (
            <Field label="Config">
              <select
                aria-label="Config"
                value={draft.configId}
                onChange={(event) => {
                  const config = configs.find(
                    (item) => item.id === event.target.value,
                  );
                  if (!config) return;
                  const next = { ...draft };
                  applyConfigToDraft(next, config);
                  onChange(next);
                }}
                className={inputClass}
              >
                {configs.map((config) => (
                  <option key={config.id} value={config.id}>
                    {config.name}
                  </option>
                ))}
              </select>
            </Field>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Results limit">
              <input
                type="number"
                aria-label="Results limit"
                min={1}
                max={1000}
                value={draft.resultsLimit}
                onChange={(event) => patch({ resultsLimit: event.target.value })}
                className={inputClass}
              />
            </Field>
            <Field label="Deduplication">
              <button
                type="button"
                role="switch"
                aria-label="Deduplication"
                aria-checked={draft.deduplicate}
                onClick={() => patch({ deduplicate: !draft.deduplicate })}
                className="flex h-10 w-full items-center justify-between rounded-lg border border-border bg-white/[0.025] px-3 text-xs font-bold text-[#dce3ec]"
              >
                Remove repeats
                <Toggle enabled={draft.deduplicate} />
              </button>
            </Field>
          </div>
          {!draft.createConfig ? (
            <p className="text-[10px] leading-4 text-muted">
              Limit and deduplication belong to this config and apply to every rule
              that uses it.
            </p>
          ) : null}
        </FormSection>

        <FormSection title="Days and time">
          <Field label="Frequency">
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  ["daily", "Daily"],
                  ["weekdays", "Weekdays"],
                  ["selected_days", "Custom"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={draft.frequency === value}
                  onClick={() =>
                    patch({
                      frequency: value,
                      weekdays:
                        value === "weekdays"
                          ? [0, 1, 2, 3, 4]
                          : draft.weekdays,
                    })
                  }
                  className={choiceClass(draft.frequency === value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </Field>

          {draft.frequency === "selected_days" ? (
            <Field label="Run on">
              <div className="grid grid-cols-7 gap-1.5">
                {weekdayOptions.map((day) => {
                  const selected = draft.weekdays.includes(day.id);
                  return (
                    <button
                      key={day.id}
                      type="button"
                      title={day.label}
                      aria-pressed={selected}
                      onClick={() =>
                        patch({
                          weekdays: selected
                            ? draft.weekdays.filter((item) => item !== day.id)
                            : [...draft.weekdays, day.id].sort(),
                        })
                      }
                      className={cn(
                        "h-9 rounded-lg border text-[10px] font-bold transition",
                        selected
                          ? "border-violet-400/70 bg-violet-500/15 text-white"
                          : "border-border bg-white/[0.025] text-muted",
                      )}
                    >
                      {day.short}
                    </button>
                  );
                })}
              </div>
            </Field>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Local time">
              <input
                type="time"
                aria-label="Local time"
                value={draft.localTime}
                onChange={(event) => patch({ localTime: event.target.value })}
                className={inputClass}
              />
            </Field>
            <Field label="Timezone">
              <input
                list="auto-search-timezones"
                aria-label="Timezone"
                value={draft.timezone}
                onChange={(event) => patch({ timezone: event.target.value })}
                className={inputClass}
                placeholder="Europe/Zurich"
              />
              <datalist id="auto-search-timezones">
                {timezoneSuggestions.map((timezone) => (
                  <option key={timezone} value={timezone} />
                ))}
              </datalist>
            </Field>
          </div>
          <p className="text-[10px] leading-4 text-muted">
            Need another run time? Duplicate this rule and change its source or
            time.
          </p>
        </FormSection>

        <FormSection title="Analysis">
          <Field label="AI Match">
            <button
              type="button"
              role="switch"
              aria-label="AI Match"
              aria-checked={draft.aiAnalysisEnabled}
              onClick={() =>
                patch({ aiAnalysisEnabled: !draft.aiAnalysisEnabled })
              }
              className="flex min-h-12 w-full items-center justify-between rounded-lg border border-border bg-white/[0.025] px-3 text-left"
            >
              <span>
                <span className="block text-xs font-bold text-[#dce3ec]">
                  Analyze new vacancies
                </span>
                <span className="mt-0.5 block text-[10px] text-muted">
                  Requires current AI data-processing consent.
                </span>
              </span>
              <Toggle enabled={draft.aiAnalysisEnabled} />
            </button>
          </Field>

          <div className="rounded-lg border border-violet-400/15 bg-violet-500/[0.055] p-3 text-[11px] leading-5 text-[#c9c3db]">
            Example: duplicate “LinkedIn · 13:00”, select Indeed, set 15:00, and
            save. Each time remains an independent rule.
          </div>
        </FormSection>
      </div>

      <footer className="sticky bottom-0 flex justify-end gap-2 border-t border-border bg-[#101720]/95 px-4 py-3 backdrop-blur sm:px-6">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
          {draft.mode === "edit"
            ? "Save changes"
            : draft.mode === "duplicate"
              ? "Create duplicate"
              : "Create auto-search"}
        </Button>
      </footer>
    </form>
  );
}

function FormSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="grid content-start gap-3 rounded-xl border border-border bg-white/[0.018] p-4">
      <h3 className="text-sm font-bold text-white">{title}</h3>
      {children}
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <span className="text-[11px] font-bold text-[#cbd3df]">{label}</span>
      {children}
    </div>
  );
}

function ListField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="min-w-0">
      <span className="mb-1 block text-[9px] font-bold uppercase tracking-[0.08em] text-muted">
        {label}
      </span>
      {children}
    </div>
  );
}

function IconAction({
  label,
  danger = false,
  disabled = false,
  onClick,
  children,
}: {
  label: string;
  danger?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "grid h-8 w-8 place-items-center rounded-lg border border-border text-muted transition hover:bg-white/[0.07] hover:text-white disabled:cursor-not-allowed disabled:opacity-45",
        danger && "hover:border-red-400/30 hover:bg-red-500/10 hover:text-red-200",
      )}
    >
      {children}
    </button>
  );
}

function Toggle({ enabled }: { enabled: boolean }) {
  return (
    <span
      className={cn(
        "flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition",
        enabled ? "justify-end bg-violet-500" : "justify-start bg-slate-700",
      )}
    >
      <span className="h-4 w-4 rounded-full bg-white shadow" />
    </span>
  );
}

function draftFromSchedule(
  schedule: JobSearchSchedule,
  config: JobSearchConfig | undefined,
  mode: EditorMode,
): ScheduleDraft {
  const draft = defaultDraft();
  draft.id = schedule.id;
  draft.mode = mode;
  draft.name = schedule.name;
  draft.sources = [...schedule.sources];
  draft.frequency = schedule.frequency;
  draft.weekdays = [...schedule.weekdays];
  draft.localTime = schedule.localTime.slice(0, 5);
  draft.timezone = schedule.timezone;
  draft.aiAnalysisEnabled = schedule.aiAnalysisEnabled;
  draft.enabled = schedule.enabled;
  if (config) {
    applyConfigToDraft(draft, config);
    draft.createConfig = false;
  }
  return draft;
}

function applyConfigToDraft(
  draft: ScheduleDraft,
  config: JobSearchConfig,
) {
  draft.configId = config.id;
  draft.configName = config.name;
  draft.keywords = stringFilter(config.filters, "keywords", "query");
  draft.location = stringFilter(config.filters, "location");
  draft.resultsLimit = String(
    numberFilter(config.filters, "resultsLimit", "results_limit") ?? 50,
  );
  draft.deduplicate =
    booleanFilter(config.filters, "deduplicate") ?? true;
}

async function saveConfigForDraft(
  draft: ScheduleDraft,
  configs: Map<string, JobSearchConfig>,
): Promise<string> {
  const limit = Number.parseInt(draft.resultsLimit, 10);
  if (draft.createConfig) {
    const config = await requestJson<JobSearchConfig>("/job-search/configs", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        name: draft.configName.trim(),
        filters: {
          keywords: draft.keywords.trim(),
          location: draft.location.trim(),
          resultsLimit: limit,
          deduplicate: draft.deduplicate,
        },
      }),
    });
    return config.id;
  }

  const config = configs.get(draft.configId);
  if (!config) throw new Error("Select an available search config");
  const nextFilters = {
    ...config.filters,
    resultsLimit: limit,
    deduplicate: draft.deduplicate,
  };
  if (JSON.stringify(nextFilters) !== JSON.stringify(config.filters)) {
    await requestJson<JobSearchConfig>(
      `/job-search/configs/${encodeURIComponent(config.id)}`,
      {
        method: "PATCH",
        headers: jsonHeaders,
        body: JSON.stringify({ filters: nextFilters }),
      },
    );
  }
  return config.id;
}

function validateDraft(draft: ScheduleDraft): string {
  if (!draft.name.trim()) return "Rule name is required";
  if (draft.sources.length === 0) return "Select at least one source";
  if (draft.createConfig && !draft.configName.trim()) {
    return "Config name is required";
  }
  if (!draft.createConfig && !draft.configId) return "Select a search config";
  if (
    draft.frequency === "selected_days" &&
    draft.weekdays.length === 0
  ) {
    return "Select at least one day";
  }
  if (!draft.localTime) return "Local time is required";
  if (!draft.timezone.trim()) return "Timezone is required";
  const limit = Number.parseInt(draft.resultsLimit, 10);
  if (!Number.isFinite(limit) || limit < 1 || limit > 1000) {
    return "Results limit must be between 1 and 1000";
  }
  return "";
}

function scheduleLabel(schedule: JobSearchSchedule): string {
  const time = schedule.localTime.slice(0, 5);
  if (schedule.frequency === "daily") return `Daily · ${time}`;
  if (schedule.frequency === "weekdays") return `Weekdays · ${time}`;
  const days = schedule.weekdays
    .map((weekday) => weekdayOptions.find((item) => item.id === weekday)?.short)
    .filter(Boolean)
    .join(", ");
  return `${days || "Custom"} · ${time}`;
}

function formatNextRun(schedule: JobSearchSchedule): string {
  if (!schedule.enabled) return "Paused";
  if (!schedule.nextRunAt) return "Not scheduled";
  const value = new Date(schedule.nextRunAt);
  if (Number.isNaN(value.getTime())) return "Not scheduled";
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: schedule.timezone,
      timeZoneName: "short",
    }).format(value);
  } catch {
    return value.toLocaleString();
  }
}

function sourceLabel(source: JobSearchSource): string {
  return sourceOptions.find((item) => item.id === source)?.label ?? source;
}

function localTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Zurich";
}

function withSeconds(value: string): string {
  return value.length === 5 ? `${value}:00` : value;
}

function stringFilter(
  filters: Record<string, unknown>,
  ...keys: string[]
): string {
  for (const key of keys) {
    if (typeof filters[key] === "string") return filters[key] as string;
  }
  return "";
}

function numberFilter(
  filters: Record<string, unknown>,
  ...keys: string[]
): number | null {
  for (const key of keys) {
    const value = filters[key];
    if (typeof value === "number") return value;
    if (typeof value === "string" && Number.isFinite(Number(value))) {
      return Number(value);
    }
  }
  return null;
}

function booleanFilter(
  filters: Record<string, unknown>,
  key: string,
): boolean | null {
  return typeof filters[key] === "boolean" ? filters[key] : null;
}

const jsonHeaders = { "Content-Type": "application/json" };
const inputClass =
  "h-10 w-full rounded-lg border border-border bg-[#0b1118] px-3 text-xs font-semibold text-white outline-none placeholder:text-muted/60 focus:border-violet-400/70";

function choiceClass(selected: boolean): string {
  return cn(
    "h-9 rounded-lg border text-xs font-bold transition disabled:cursor-not-allowed disabled:opacity-40",
    selected
      ? "border-violet-400/70 bg-violet-500/15 text-white"
      : "border-border bg-white/[0.025] text-muted hover:bg-white/[0.06] hover:text-white",
  );
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as {
        detail?: string | { message?: string };
      };
      detail =
        typeof payload.detail === "string"
          ? payload.detail
          : payload.detail?.message ?? detail;
    } catch {
      // Keep the HTTP fallback when the response is not JSON.
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Automatic search request failed";
}
