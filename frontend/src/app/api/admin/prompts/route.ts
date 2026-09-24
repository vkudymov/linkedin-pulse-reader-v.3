import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function GET(request: Request) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const url = new URL(request.url);
  const qs = url.searchParams.toString();
  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(`${baseUrl}/v1/admin/prompts${qs ? `?${qs}` : ""}`, {
    method: "GET",
    cache: "no-store",
    headers: { authorization: `Bearer ${accessToken}` },
  });

  return forwardWorkerResponse(resp);
}

