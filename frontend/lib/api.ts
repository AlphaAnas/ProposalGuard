const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SSECallbacks {
  onThreadId: (threadId: string) => void;
  onNodeComplete: (node: string, data: Record<string, any>) => void;
  onInterrupt: (data: any) => void;
  onComplete: (data: any) => void;
  onError: (error: string) => void;
}

export async function startPipeline(
  jobDescription: string,
  callbacks: SSECallbacks
) {
  const response = await fetch(`${API_BASE}/proposals/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription }),
  });

  if (!response.ok) {
    callbacks.onError(`Server error: ${response.status}`);
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split("\n");
    buffer = lines.pop() || ""; // Keep incomplete line in buffer

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ") && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));

          switch (currentEvent) {
            case "thread_id":
              callbacks.onThreadId(data.thread_id);
              break;
            case "node_complete":
              callbacks.onNodeComplete(data.node, data.data);
              break;
            case "interrupt":
              callbacks.onInterrupt(data);
              break;
            case "complete":
              callbacks.onComplete(data);
              break;
            case "error":
              callbacks.onError(data.error);
              break;
          }
        } catch (e) {
          console.error("Failed to parse SSE data:", line, e);
        }
        currentEvent = "";
      }
    }
  }
}

export async function resumePipeline(
  threadId: string,
  action: "approve" | "reject",
  feedback?: string
) {
  const response = await fetch(`${API_BASE}/proposals/${threadId}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, feedback: feedback || null }),
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "Failed to resume pipeline");
  }

  return response.json();
}
