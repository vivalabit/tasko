export class RetryablePackError extends Error {}

export type PackStatusRecovery<T> =
  | { state: "saved"; payload: T }
  | { state: "not_found" }
  | { state: "unknown" };

export async function recoverPackStatus<T>(
  load: () => Promise<Pick<Response, "ok" | "status" | "json">>,
  maxAttempts = 3,
  sleep: (milliseconds: number) => Promise<void> = (milliseconds) => (
    new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds))
  ),
): Promise<PackStatusRecovery<T>> {
  let lastState: Exclude<PackStatusRecovery<T>, { state: "saved" }> = { state: "unknown" };
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await load();
      if (response.ok) {
        return { state: "saved", payload: await response.json() as T };
      }
      lastState = response.status === 404 ? { state: "not_found" } : { state: "unknown" };
    } catch {
      lastState = { state: "unknown" };
    }
    if (attempt < maxAttempts) await sleep(250 * (2 ** (attempt - 1)));
  }
  return lastState;
}

export async function retryPackOperation<T>(
  operation: () => Promise<T>,
  onRetry: (attempt: number) => void,
  maxAttempts = 3,
  sleep: (milliseconds: number) => Promise<void> = (milliseconds) => (
    new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds))
  ),
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      const retryable = error instanceof RetryablePackError || error instanceof TypeError;
      if (!retryable || attempt === maxAttempts) throw error;
      onRetry(attempt + 1);
      await sleep(350 * (2 ** (attempt - 1)));
    }
  }
  throw new Error("Pack operation exhausted retry attempts");
}
