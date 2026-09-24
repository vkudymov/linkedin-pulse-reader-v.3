import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ prompt_id: string }> },
) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { prompt_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();

  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    body = null;
  }

  const resp = await fetch(`${baseUrl}/v1/admin/prompts/${encodeURIComponent(prompt_id)}`, {
    method: "PATCH",
    cache: "no-store",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(body || {}),
  });

  return forwardWorkerResponse(resp);
}

