import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function GET(_request: Request, { params }: { params: Promise<{ user_id: string }> }) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { user_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(`${baseUrl}/v1/admin/users/${encodeURIComponent(user_id)}/job-searches`, {
    method: "GET",
    headers: { authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });

  return forwardWorkerResponse(resp);
}

