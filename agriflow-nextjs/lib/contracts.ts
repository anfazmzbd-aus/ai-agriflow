export type ChatSource = { title: string; url?: string };
export type ChatRequest = { message: string; location?: string; crop?: string; session_id?: string };
export type ChatResponse = { answer: string; mode: "live" | "demo"; sources?: ChatSource[]; confidence?: string; disclaimer?: string };
export function isChatResponse(input: unknown): input is Omit<ChatResponse,"mode"> {
  if (!input || typeof input !== "object") return false;
  const obj = input as Record<string,unknown>;
  return typeof obj.answer === "string" && obj.answer.length > 0 &&
    (obj.sources === undefined || (Array.isArray(obj.sources) && obj.sources.every(item => !!item && typeof item.title === "string" && (item.url === undefined || typeof item.url === "string"))));
}
