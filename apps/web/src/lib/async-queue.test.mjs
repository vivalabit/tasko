import assert from "node:assert/strict";
import test from "node:test";

import { runSequentially } from "./async-queue.ts";

test("runs queued work one item at a time in insertion order", async () => {
  const events = [];
  let active = 0;
  let maxActive = 0;

  const completed = await runSequentially(["first", "second", "third"], async (item) => {
    active += 1;
    maxActive = Math.max(maxActive, active);
    events.push(`start:${item}`);
    await Promise.resolve();
    events.push(`finish:${item}`);
    active -= 1;
    return true;
  });

  assert.equal(completed, true);
  assert.equal(maxActive, 1);
  assert.deepEqual(events, [
    "start:first", "finish:first",
    "start:second", "finish:second",
    "start:third", "finish:third",
  ]);
});

test("stops the queue after the first failed item", async () => {
  const processed = [];

  const completed = await runSequentially([1, 2, 3], async (item) => {
    processed.push(item);
    return item !== 2;
  });

  assert.equal(completed, false);
  assert.deepEqual(processed, [1, 2]);
});
