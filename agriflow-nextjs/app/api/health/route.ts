import { NextResponse } from "next/server";
export async function GET() {
  return NextResponse.json({ status: "ok", frontend: "agriflow-nextjs", backendConfigured: Boolean(process.env.AGRIFLOW_API_BASE_URL) });
}
