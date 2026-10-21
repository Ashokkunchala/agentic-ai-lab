import test from "node:test";
import assert from "node:assert/strict";
import worker from "./worker.js";
const env = {
  JARVIS_ACCESS_KEY: "test-key-for-tests-only",
  AI: { run: async (_model, input) => ({ response: "Test answer for: " + input.messages.at(-1).content }) }
};
function req(path, options = {}) { return new Request("https://jarvis.test" + path, options); }

test("health reports service status without revealing the secret", async () => {
  const response = await worker.fetch(req("/api/health"), env);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.service, "jarvis");
  assert.equal(body.access_key_configured, true);
  assert.equal(JSON.stringify(body).includes(env.JARVIS_ACCESS_KEY), false);
});
test("chat rejects missing key", async () => {
  const response = await worker.fetch(req("/api/chat", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ message: "Explain Terraform plan" }) }), env);
  assert.equal(response.status, 401);
});
test("chat requires JSON content type", async () => {
  const response = await worker.fetch(req("/api/chat", { method: "POST", headers: { "x-jarvis-key": env.JARVIS_ACCESS_KEY, "content-type": "text/plain" }, body: "hello" }), env);
  assert.equal(response.status, 415);
});
test("authenticated chat returns model answer", async () => {
  const response = await worker.fetch(req("/api/chat", { method: "POST", headers: { "x-jarvis-key": env.JARVIS_ACCESS_KEY, "content-type": "application/json" }, body: JSON.stringify({ message: "Explain terraform plan" }) }), env);
  assert.equal(response.status, 200);
  assert.match((await response.json()).answer, /Explain terraform plan/);
});
test("chat rejects blank messages", async () => {
  const response = await worker.fetch(req("/api/chat", { method: "POST", headers: { "x-jarvis-key": env.JARVIS_ACCESS_KEY, "content-type": "application/json" }, body: JSON.stringify({ message: "  " }) }), env);
  assert.equal(response.status, 400);
});
test("chat rejects oversized messages", async () => {
  const response = await worker.fetch(req("/api/chat", { method: "POST", headers: { "x-jarvis-key": env.JARVIS_ACCESS_KEY, "content-type": "application/json" }, body: JSON.stringify({ message: "x".repeat(4001) }) }), env);
  assert.equal(response.status, 400);
});
test("unknown API routes return 404", async () => {
  const response = await worker.fetch(req("/api/nope"), env);
  assert.equal(response.status, 404);
});