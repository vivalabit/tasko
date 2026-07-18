export async function runSequentially<T>(
  items: readonly T[],
  worker: (item: T) => Promise<boolean>,
): Promise<boolean> {
  for (const item of items) {
    if (!await worker(item)) return false;
  }
  return true;
}
