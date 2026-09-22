import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function GET() {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(`${baseUrl}/v1/admin/search-tariffs`, {
    method: "GET",
    cache: "no-store",
    headers: { authorization: `Bearer ${accessToken}` },
  });
  return forwardWorkerResponse(resp);
}

export async function POST(request: Request) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const baseUrl = getWorkerApiBaseUrl();
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    body = null;
  }

  const resp = await fetch(`${baseUrl}/v1/admin/search-tariffs`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(body || {}),
  });
  return forwardWorkerResponse(resp);
}

