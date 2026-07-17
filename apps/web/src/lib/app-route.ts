export type View =
  | "Dashboard"
  | "Jobs"
  | "ApplicationWorkspace"
  | "Applications"
  | "Calendar"
  | "Assistant"
  | "Profile"
  | "Settings"
  | "Logs";

export type AppRoute = {
  view: View;
  applicationId?: string;
};

const applicationWorkspaceHash = "#application-workspace";
const applicationWorkspacePrefix = `${applicationWorkspaceHash}/`;

const viewByHash: Record<string, View> = {
  "#profile": "Profile",
  "#settings": "Settings",
  "#logs": "Logs",
  "#applications": "Applications",
  [applicationWorkspaceHash]: "ApplicationWorkspace",
  "#calendar": "Calendar",
  "#assistant": "Assistant",
  "#jobs": "Jobs",
};

const hashByView: Record<Exclude<View, "ApplicationWorkspace">, string> = {
  Dashboard: "#dashboard",
  Jobs: "#jobs",
  Applications: "#applications",
  Calendar: "#calendar",
  Assistant: "#assistant",
  Profile: "#profile",
  Settings: "#settings",
  Logs: "#logs",
};

export function getRouteFromHash(hash: string): AppRoute {
  if (hash.startsWith(applicationWorkspacePrefix)) {
    const encodedApplicationId = hash.slice(applicationWorkspacePrefix.length);

    if (encodedApplicationId) {
      try {
        return {
          view: "ApplicationWorkspace",
          applicationId: decodeURIComponent(encodedApplicationId),
        };
      } catch {
        return {
          view: "ApplicationWorkspace",
          applicationId: encodedApplicationId,
        };
      }
    }
  }

  return { view: viewByHash[hash] ?? "Dashboard" };
}

export function getHashForView(view: View, applicationId?: string) {
  if (view === "ApplicationWorkspace") {
    return applicationId
      ? `${applicationWorkspacePrefix}${encodeURIComponent(applicationId)}`
      : applicationWorkspaceHash;
  }

  return hashByView[view];
}

export function findWorkspaceApplication<T extends { id: string }>(
  applications: readonly T[],
  applicationId: string | null | undefined,
) {
  if (!applicationId) return null;
  return (
    applications.find((application) => application.id === applicationId) ?? null
  );
}
