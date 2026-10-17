import { NextResponse } from "next/server";

/**
 * Server-side proxy to the C05 QC service.
 *
 * The shared runtime binds to loopback and rejects cross-origin and
 * non-loopback Host headers, so the browser must never call it directly.
 * Keeping the hop server-side also means no credential ever reaches the client.
 */
const UPSTREAM = process.env.C05_API_BASE_URL ?? "http://127.0.0.1:8000";


async function forward(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const url = new URL(request.url);
  const target = new URL(`${UPSTREAM}/${path.join("/")}`);
  target.search = url.search;

  const headers: Record<string, string> = { "content-type": "application/json" };
  const method = request.method.toUpperCase();
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();

  try {
    const upstream = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
    });
    // Pass bytes through untouched so binary responses (inspection photos) survive.
    const payload = await upstream.arrayBuffer();
    return new NextResponse(payload, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "QC service unreachable. Start it with: python projects/common/C05-visual-defect-detection/src/c05_entry.py",
      },
      { status: 503 },
    );
  }
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;