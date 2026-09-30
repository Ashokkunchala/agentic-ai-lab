export default {
  async fetch(request) {
    if (request.method !== "POST") {
      return new Response("Use POST", { status: 405 });
    }

    const body = await request.json().catch(() => null);
    if (!body || typeof body.goal !== "string" || body.goal.length === 0) {
      return Response.json({ error: "goal is required" }, { status: 400 });
    }

    return Response.json({
      accepted: true,
      goal: body.goal,
      next: "queue-for-agent-execution"
    });
  }
};
