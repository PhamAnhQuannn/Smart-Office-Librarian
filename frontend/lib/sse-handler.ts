/**
 * Lightweight SSE frame parser for use outside React components (e.g. Next.js
 * Route Handlers acting as a BFF proxy). Each chunk from `response.body` is
 * passed to `onLine`; complete `data:` lines are collected and emitted as JSON
 * objects. A blank line flushes the accumulated `data:` lines.
 */
export type SSEFrameCallback = (json: unknown) => void;

/**
 * Read an SSE `Response` and call `onFrame` for each complete event payload.
 * Returns when the stream ends or `signal` fires.
 */
export async function consumeSSEResponse(
  response: Response,
  onFrame: SSEFrameCallback,
  signal?: AbortSignal,
): Promise<void> {
  if (!response.body) return;

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let carry = "";
  let dataLines: string[] = [];

  const flush = () => {
    if (dataLines.length === 0) return;
    const raw = dataLines.join("\n");
    dataLines = [];
    try {
      onFrame(JSON.parse(raw));
    } catch {
      // malformed frame — skip
    }
  };

  try {
    while (true) {
      if (signal?.aborted) break;
      const { done, value } = await reader.read();
      if (done) break;

      const text = carry + decoder.decode(value, { stream: true });
      const lines = text.split("\n");

      // The last segment may be incomplete — carry it over.
      carry = lines.pop() ?? "";

      for (const line of lines) {
        if (line === "") {
          // Blank line = end of SSE event
          flush();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trimStart());
        }
        // comment / id / event fields are intentionally ignored
      }
    }
  } finally {
    reader.releaseLock();
  }

  // Flush anything remaining
  flush();
}
