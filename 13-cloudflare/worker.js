/**
 * Lesson 13: the Cloudflare edge as a CONTROL PLANE, not an execution plane.
 *
 * The decision this file encodes: a Worker validates, authorises, queues and
 * dispatches. It never runs `terraform`, `kubectl` or `aws`. A Worker is a
 * short-lived isolate, not a general-purpose Linux box, and pretending
 * otherwise is how people end up with an SSRF-shaped incident.
 *
 * ```text
 * Browser -> Worker (validate, auth, rate limit)
 *                      -> Queue (durable async work)
 *                      -> Authenticated executor (Terraform, kubectl, AWS)
 *                      -> Durable Object (per-tenant run state)
 * ```
 *
 * Four controls in the code below, each mapping to a lesson:
 *   1. method + content-type gate          -> lesson 02, validate before you trust
 *   2. shared-secret auth, timing-safe     -> lesson 12, authenticated boundary
 *   3. body size cap                       -> lesson 04, bounded context
 *   4. dry_run default on the mutation     -> lesson 10, dry run first
 *
 * Local test:  node worker.test.mjs
 * Deploy:      npx wrangler deploy     (see wrangler.toml.example)
 */

const MAX_BODY_BYTES = 8 * 1024;
const MAX_GOAL_CHARS = 2000;

/** Constant-time comparison. A plain `===` leaks the secret through timing. */
function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

export default {
  async fetch(request, env) {
    const startedAt = Date.now();

    // --- 1. transport gate -------------------------------------------------
    if (request.method !== "POST") {
      return json({ error: "method_not_allowed", hint: "POST a JSON goal" }, 405);
    }
    if (!request.headers.get("content-type")?.includes("application/json")) {
      return json({ error: "unsupported_media_type", hint: "content-type: application/json" }, 415);
    }

    // --- 2. authentication -------------------------------------------------
    // The Worker is the trust boundary. Everything downstream trusts this check.
    const provided = request.headers.get("x-agent-key") ?? "";
    const expected = env.AGENT_SHARED_SECRET ?? "";
    if (!expected || !safeEqual(provided, expected)) {
      // Same shape as a success response would give away nothing.
      return json({ error: "unauthorized" }, 401);
    }

    // --- 3. bounded input --------------------------------------------------
    const declaredLength = Number(request.headers.get("content-length") ?? "0");
    if (declaredLength > MAX_BODY_BYTES) {
      return json({ error: "payload_too_large", limit_bytes: MAX_BODY_BYTES }, 413);
    }
    const raw = await request.text();
    if (raw.length > MAX_BODY_BYTES) {
      return json({ error: "payload_too_large", limit_bytes: MAX_BODY_BYTES }, 413);
    }

    let body;
    try {
      body = JSON.parse(raw);
    } catch {
      return json({ error: "invalid_json" }, 400);
    }

    if (!body || typeof body.goal !== "string" || body.goal.trim().length === 0) {
      return json({ error: "goal_required" }, 400);
    }
    if (body.goal.length > MAX_GOAL_CHARS) {
      return json({ error: "goal_too_long", limit_chars: MAX_GOAL_CHARS }, 400);
    }
    if (body.dry_run !== undefined && typeof body.dry_run !== "boolean") {
      return json({ error: "dry_run_must_be_boolean" }, 400);
    }

    // Default to dry run. A live mutation must be asked for explicitly.
    const dryRun = body.dry_run !== false;
    const runId = crypto.randomUUID();

    // --- 4. hand off; never execute here ----------------------------------
    if (env.AGENT_QUEUE) {
      await env.AGENT_QUEUE.send({
        runId,
        goal: body.goal.trim(),
        dryRun,
        requestedAt: new Date().toISOString(),
        // No credentials travel through the queue. The executor mints its own.
        requestedBy: "worker-control-plane",
      });
    }

    console.log(
      JSON.stringify({
        event: "agent.run.accepted",
        runId,
        dryRun,
        goal_chars: body.goal.length,
        latency_ms: Date.now() - startedAt,
      })
    );

    return json(
      {
        accepted: true,
        run_id: runId,
        dry_run: dryRun,
        status: "queued",
        poll: `/runs/${runId}`,
        // Being explicit here prevents the classic mistake: assuming the Worker
        // ran anything. It did not, and it cannot.
        execution_plane: "separate authenticated executor; not this Worker",
      },
      202
    );
  },
};