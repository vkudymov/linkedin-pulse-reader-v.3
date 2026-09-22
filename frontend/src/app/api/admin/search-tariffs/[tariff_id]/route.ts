import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ tariff_id: string }> },
) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { tariff_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();

  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    body = null;
  }

  const resp = await fetch(`${baseUrl}/v1/admin/search-tariffs/${encodeURIComponent(tariff_id)}`, {
    method: "PATCH",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(body || {}),
  });
  return forwardWorkerResponse(resp);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ tariff_id: string }> },
) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { tariff_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();

  const resp = await fetch(`${baseUrl}/v1/admin/search-tariffs/${encodeURIComponent(tariff_id)}`, {
    method: "DELETE",
    headers: { authorization: `Bearer ${accessToken}` },
  });
  return forwardWorkerResponse(resp);
}

