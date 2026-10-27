import { NextRequest, NextResponse } from "next/server";
import { isChatResponse, type ChatRequest } from "@/lib/contracts";
export const runtime = "nodejs";
const demo = (answer: string) => ({ answer, mode: "demo" as const, disclaimer: "Demonstration only. This is not a verified agronomic recommendation; check local conditions and consult a qualified adviser." });
export async function POST(req: NextRequest) {
  let body: ChatRequest;
  try { body = await req.json() as ChatRequest; } catch { return NextResponse.json({ error: "Invalid JSON" }, { status: 400 }); }
  if (typeof body.message !== "string" || !body.message.trim() || body.message.length > 2000) {
    return NextResponse.json({ error: "Message must contain 1–2000 characters." }, { status: 400 });
  }
  if ((body.crop && (typeof body.crop !== "string" || body.crop.length > 100)) || (body.location && (typeof body.location !== "string" || body.location.length > 150))) {
    return NextResponse.json({ error: "Invalid context fields." }, { status: 400 });
  }
  const base = process.env.AGRIFLOW_API_BASE_URL;
  if (!base) return NextResponse.json(demo(`I can help organize a decision about “${body.message.trim()}”. In this preview, live weather, field measurements and market feeds are not connected yet. Start by identifying your crop and district, checking current field conditions, and consulting verified local information. Once the AgriFlow agent API is connected, this panel will display a sourced recommendation.`));
  try {
    const parsed = new URL(base);
    if (!(["http:","https:"].includes(parsed.protocol))) throw new Error("Unsupported API protocol");
    const path = process.env.AGRIFLOW_CHAT_PATH || "/api/v1/chat";
    if (!path.startsWith("/") || path.startsWith("//")) throw new Error("Invalid chat path");
    const url = new URL(path, parsed);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    let res: Response;
    try {
      res = await fetch(url, { method: "POST", headers: {"content-type":"application/json", ...(process.env.AGRIFLOW_API_TOKEN ? { authorization:`Bearer ${process.env.AGRIFLOW_API_TOKEN}` } : {}) }, body: JSON.stringify({ message:body.message.trim(), crop:body.crop, location:body.location, session_id:body.session_id }), signal: controller.signal, cache:"no-store" });
    } finally { clearTimeout(timeout); }
    if (!res.ok) throw new Error("Upstream API unavailable");
    const data: unknown = await res.json();
    if (!isChatResponse(data)) throw new Error("Invalid upstream schema");
    return NextResponse.json({ ...data, mode: "live" }, { headers:{ "cache-control":"no-store" } });
  } catch {
    return NextResponse.json({ error: "The AI backend is unavailable. Please try again later or switch to the offline preview." }, { status: 503 });
  }
}
