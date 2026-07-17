export class RetryablePackError extends Error {}

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
