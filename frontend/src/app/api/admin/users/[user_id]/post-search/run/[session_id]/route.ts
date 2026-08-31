import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ user_id: string; session_id: string }> },
) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { user_id, session_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(
    `${baseUrl}/v1/admin/users/${encodeURIComponent(user_id)}/post-search/run/${encodeURIComponent(session_id)}`,
    {
      method: "GET",
      headers: { authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    },
  );

  return forwardWorkerResponse(resp);
}

