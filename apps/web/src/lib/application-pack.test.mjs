import assert from "node:assert/strict";
import test from "node:test";

import {
  RetryablePackError,
  recoverPackStatus,
  retryPackOperation,
} from "./application-pack.ts";

test("retries transient pack failures with exponential backoff", async () => {
  const retries = [];
  const delays = [];
  let attempts = 0;

  const result = await retryPackOperation(
    async () => {
      attempts += 1;
      if (attempts < 3) throw new RetryablePackError("temporary failure");
      return "saved";
    },
    (attempt) => retries.push(attempt),
    3,
    async (milliseconds) => { delays.push(milliseconds); },
  );

  assert.equal(result, "saved");
  assert.equal(attempts, 3);
  assert.deepEqual(retries, [2, 3]);
  assert.deepEqual(delays, [350, 700]);
});

test("does not retry validation failures", async () => {
  let attempts = 0;

  await assert.rejects(
    retryPackOperation(
      async () => {
        attempts += 1;
        throw new Error("unsupported claim");
      },
      () => assert.fail("validation errors must not retry"),
      3,
      async () => {},
    ),
    /unsupported claim/,
  );

  assert.equal(attempts, 1);
});

test("stops after the configured retry budget", async () => {
  let attempts = 0;

  await assert.rejects(
    retryPackOperation(
      async () => {
        attempts += 1;
        throw new TypeError("network unavailable");
      },
      () => {},
      3,
      async () => {},
    ),
    /network unavailable/,
  );

  assert.equal(attempts, 3);
});

test("recovers a committed pack after the save response was lost", async () => {
  const payload = { packJobId: "pack-1", status: "completed" };
  const recovery = await recoverPackStatus(async () => Response.json(payload));

  assert.deepEqual(recovery, { state: "saved", payload });
});

test("polls through a transient missing status while the commit finishes", async () => {
  let attempts = 0;
  const recovery = await recoverPackStatus(
    async () => {
      attempts += 1;
      return attempts === 1
        ? new Response(null, { status: 404 })
        : Response.json({ status: "completed" });
    },
    3,
    async () => {},
  );

  assert.deepEqual(recovery, {
    state: "saved",
    payload: { status: "completed" },
  });
  assert.equal(attempts, 2);
});

test("distinguishes a missing pack from an unknown recovery state", async () => {
  assert.deepEqual(
    await recoverPackStatus(async () => new Response(null, { status: 404 }), 1),
    { state: "not_found" },
  );
  assert.deepEqual(
    await recoverPackStatus(
      async () => { throw new TypeError("network unavailable"); },
      1,
    ),
    { state: "unknown" },
  );
});
