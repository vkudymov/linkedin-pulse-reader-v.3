import {
  forwardWorkerResponse,
  getWorkerAccessToken,
  getWorkerApiBaseUrl,
  unauthorizedResponse,
} from "@/app/api/post-search/_workerApi";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ user_id: string; post_id: string }> },
) {
  const accessToken = await getWorkerAccessToken();
  if (!accessToken) return unauthorizedResponse();

  const { user_id, post_id } = await params;
  const baseUrl = getWorkerApiBaseUrl();

  const resp = await fetch(
    `${baseUrl}/v1/admin/users/${encodeURIComponent(user_id)}/posts/${encodeURIComponent(post_id)}`,
    {
      method: "DELETE",
      headers: { authorization: `Bearer ${accessToken}` },
    },
  );

  return forwardWorkerResponse(resp);
}

