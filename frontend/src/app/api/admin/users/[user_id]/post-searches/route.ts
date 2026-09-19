import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function GET(_request: Request, ctx: { params: Promise<{ user_id: string }> }) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { user_id } = await ctx.params;
  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(`${baseUrl}/v1/admin/users/${encodeURIComponent(user_id)}/post-searches`, {
    method: "GET",
    cache: "no-store",
    headers: { authorization: `Bearer ${accessToken}` },
  });

  return forwardWorkerResponse(resp);
}
