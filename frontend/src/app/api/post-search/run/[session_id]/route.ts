import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "../../_workerApi";

export async function GET(_request: Request, ctx: { params: Promise<{ session_id: string }> }) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) {
    return unauthorizedResponse();
  }

  const { session_id } = await ctx.params;
  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(`${baseUrl}/v1/post-search/run/${encodeURIComponent(session_id)}`, {
    headers: { authorization: `Bearer ${accessToken}` },
  });

  return forwardWorkerResponse(resp);
}

