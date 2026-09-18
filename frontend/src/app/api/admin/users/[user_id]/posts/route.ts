import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ user_id: string }> },
) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { user_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();

  const url = new URL(request.url);
  const filter = url.searchParams.get("filter") || "all";

  const resp = await fetch(
    `${baseUrl}/v1/admin/users/${encodeURIComponent(user_id)}/posts?filter=${encodeURIComponent(filter)}`,
    {
      method: "GET",
      headers: { authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    },
  );

  return forwardWorkerResponse(resp);
}

