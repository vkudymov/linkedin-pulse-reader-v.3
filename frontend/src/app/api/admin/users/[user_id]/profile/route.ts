import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ user_id: string }> },
) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { user_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(`${baseUrl}/v1/admin/users/${encodeURIComponent(user_id)}/profile`, {
    method: "GET",
    headers: { authorization: `Bearer ${accessToken}` },
  });

  return forwardWorkerResponse(resp);
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ user_id: string }> },
) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { user_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();

  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    body = null;
  }

  const resp = await fetch(`${baseUrl}/v1/admin/users/${encodeURIComponent(user_id)}/profile`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(body || {}),
  });

  return forwardWorkerResponse(resp);
}

