// Supabase Edge Function: send-search-report
//
// Receives:
//   { to, subject, body, filename, mime_type, content_base64 }
// Requires:
//   header: x-search-report-secret == SEARCH_REPORT_FUNCTION_SECRET
// Env:
//   RESEND_API_KEY, REPORTS_FROM_EMAIL
//
// Uses Resend for sending email with attachments.

type Payload = {
  to: string;
  subject: string;
  body: string;
  filename: string;
  mime_type: string;
  content_base64: string;
};

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

Deno.serve(async (req) => {
  const secret = req.headers.get("x-search-report-secret") || "";
  const expected = Deno.env.get("SEARCH_REPORT_FUNCTION_SECRET") || "";
  if (!expected || secret !== expected) {
    return json(401, { ok: false, error: "unauthorized" });
  }

  let payload: Payload | null = null;
  try {
    payload = (await req.json()) as Payload;
  } catch {
    payload = null;
  }
  if (
    !payload ||
    typeof payload.to !== "string" ||
    typeof payload.subject !== "string" ||
    typeof payload.body !== "string" ||
    typeof payload.filename !== "string" ||
    typeof payload.mime_type !== "string" ||
    typeof payload.content_base64 !== "string"
  ) {
    return json(400, { ok: false, error: "invalid payload" });
  }

  const apiKey = Deno.env.get("RESEND_API_KEY") || "";
  const fromEmail = Deno.env.get("REPORTS_FROM_EMAIL") || "";
  if (!apiKey || !fromEmail) {
    return json(500, { ok: false, error: "email provider is not configured" });
  }

  const resendResp = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      authorization: `Bearer ${apiKey}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      from: fromEmail,
      to: [payload.to],
      subject: payload.subject,
      text: payload.body,
      attachments: [
        {
          filename: payload.filename,
          content: payload.content_base64,
          content_type: payload.mime_type,
        },
      ],
    }),
  });

  const text = await resendResp.text().catch(() => "");
  if (!resendResp.ok) {
    return json(502, { ok: false, error: "resend failed", detail: text });
  }

  let out: unknown = null;
  try {
    out = JSON.parse(text);
  } catch {
    out = { raw: text };
  }

  return json(200, { ok: true, provider: "resend", response: out });
});

