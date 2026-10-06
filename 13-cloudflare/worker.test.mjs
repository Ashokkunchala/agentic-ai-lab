/**
 * Dependency-free test for worker.js.
 *
 *   node worker.test.mjs
 *
 * Why not a framework: the control plane has four gates and no dependencies.
 * A test runner would be more machinery than the thing under test.
 * Each case below maps to one gate in the Worker.
 */

import assert from "node:assert/strict";
import worker from "./worker.js";

const SECRET = "test-secret-value";
const env = { AGENT_SHARED_SECRET: SECRET };

function request(overrides = {}) {
  const { method = "POST", body, headers = {}, key = SECRET, contentType = "application/json" } = overrides;
  const merged = { "content-type": contentType, ...headers };
  if (key !== null) merged["x-agent-key"] = key;
  return new Request("https://agent.example.com/runs", {
    method,
    headers: merged,
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
}

const cases = [
  {
    name: "GET is rejected",
    run: () => worker.fetch(request({ method: "GET" }), env),
    check: async (res) => assert.equal(res.status, 405),
  },
  {
    name: "wrong content-type is rejected",
    run: () => worker.fetch(request({ contentType: "text/plain", body: "hi" }), env),
    check: async (res) => assert.equal(res.status, 415),
  },
  {
    name: "missing key is rejected",
    run: () => worker.fetch(request({ key: null, body: { goal: "x" } }), env),
    check: async (res) => assert.equal(res.status, 401),
  },
  {
    name: "wrong key is rejected",
    run: () => worker.fetch(request({ key: "nope", body: { goal: "x" } }), env),
    check: async (res) => assert.equal(res.status, 401),
  },
  {
    name: "unconfigured secret rejects everything",
    run: () => worker.fetch(request({ body: { goal: "x" } }), {}),
    check: async (res) => assert.equal(res.status, 401),
  },
  {
    name: "invalid JSON is rejected",
    run: () => worker.fetch(request({ body: "{not json" }), env),
    check: async (res) => assert.equal(res.status, 400),
  },
  {
    name: "empty goal is rejected",
    run: () => worker.fetch(request({ body: { goal: "   " } }), env),
    check: async (res) => assert.equal(res.status, 400),
  },
  {
    name: "non-boolean dry_run is rejected",
    run: () => worker.fetch(request({ body: { goal: "x", dry_run: "yes" } }), env),
    check: async (res) => assert.equal(res.status, 400),
  },
  {
    name: "oversized declared body is rejected",
    run: () => worker.fetch(request({ body: { goal: "x" }, headers: { "content-length": "99999999" } }), env),
    check: async (res) => assert.equal(res.status, 413),
  },
  {
    name: "oversized goal is rejected",
    run: () => worker.fetch(request({ body: { goal: "x".repeat(2001) } }), env),
    check: async (res) => assert.equal(res.status, 400),
  },
  {
    name: "valid dry run is accepted and defaults to dry_run true",
    run: () => worker.fetch(request({ body: { goal: "summarise the deploy log" } }), env),
    check: async (res) => {
      assert.equal(res.status, 202);
      const body = await res.json();
      assert.equal(body.accepted, true);
      assert.equal(body.dry_run, true);
      assert.equal(body.status, "queued");
      assert.match(body.execution_plane, /not this Worker/);
    },
  },
  {
    name: "explicit live run is accepted with dry_run false",
    run: () => worker.fetch(request({ body: { goal: "roll back checkout", dry_run: false } }), env),
    check: async (res) => {
      assert.equal(res.status, 202);
      assert.equal((await res.json()).dry_run, false);
    },
  },
];

let failures = 0;
for (const testCase of cases) {
  try {
    await testCase.check(await testCase.run());
    console.log(`  PASS  ${testCase.name}`);
  } catch (error) {
    failures += 1;
    console.log(`  FAIL  ${testCase.name}\n        ${error.message}`);
  }
}

console.log(`\n${cases.length - failures}/${cases.length} worker gates hold`);
process.exit(failures === 0 ? 0 : 1);