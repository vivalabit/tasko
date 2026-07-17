import assert from "node:assert/strict";
import test from "node:test";

import { getHashForView, getRouteFromHash } from "./app-route.ts";

test("recognizes the legacy application workspace hash", () => {
  assert.deepEqual(getRouteFromHash("#application-workspace"), {
    view: "ApplicationWorkspace",
  });
});

test("adds an encoded application ID to the workspace hash", () => {
  assert.equal(
    getHashForView("ApplicationWorkspace", "application/acme role"),
    "#application-workspace/application%2Facme%20role",
  );
});

test("restores the application ID from the workspace hash", () => {
  assert.deepEqual(
    getRouteFromHash("#application-workspace/application%2Facme%20role"),
    {
      view: "ApplicationWorkspace",
      applicationId: "application/acme role",
    },
  );
});

test("keeps existing view hashes working", () => {
  assert.deepEqual(getRouteFromHash("#applications"), { view: "Applications" });
  assert.equal(getHashForView("Applications"), "#applications");
  assert.deepEqual(getRouteFromHash("#unknown"), { view: "Dashboard" });
});
