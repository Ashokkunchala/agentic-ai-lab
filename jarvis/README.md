# JARVIS — Personal DevOps Assistant MVP

Android-first, cloud-hosted, free-first starter. This installable Progressive Web App (PWA) is served by a Cloudflare Worker with a Workers AI chat endpoint.

## MVP scope

- Mobile-first chat UI, installable from Android Chrome using Add to Home screen.
- DevOps/coding assistant prompt and bounded conversation history.
- Cloudflare Workers AI binding; no third-party model key is required by this starter.
- Private chat API protected by a secret access key.
- Request size/message limits, JSON validation, safe errors and no-store API responses.
- Unit tests for authentication, validation, health and mocked model calls.
- No command execution, GitHub write access, AWS credentials, Terraform apply, kubectl mutation, email or background tasks in this MVP.

The static PWA shell is public by URL; chat API calls require your secret. Treat the deployed URL as discoverable, keep the access key private, and add Cloudflare Access/rate limiting before broader sharing. A shared secret is not suitable as multi-user authentication.

## Repository integration

- The learning modules for agent loops, tools, memory, MCP, coding agents, DevOps agents and Cloudflare remain the foundation.
- AI-answer-Agent is a separate Cloudflare model-routing project and may be integrated later behind an authenticated provider adapter. This MVP does not duplicate its Electron desktop client.
- Work is intended for the main branch, per project preference.

## Costs (free-first, not a guarantee of zero cost)

- Cloudflare Workers has a free plan with usage/CPU/request limits that can change.
- Workers AI has account-specific free allocation/usage limits subject to Cloudflare's current terms, model availability and account settings. Usage beyond the free allocation may be billed.
- A custom domain is optional; workers.dev avoids a domain purchase.
- No paid API is required by this code. Check the current Cloudflare dashboard and pricing before production use; do not assume unlimited free inference.

## Deploy

Prerequisites: a Cloudflare account, Node.js 20+ and npm on a computer for initial deployment. After deployment, use it from Android; no local server is needed on the phone.

1. Clone the repo and enter this folder:

   ~~~bash
   git clone https://github.com/Ashokkunchala/agentic-ai-lab.git
   cd agentic-ai-lab/jarvis
   npm install
   npx wrangler login
   ~~~

2. Generate a strong access key. PowerShell:

   ~~~powershell
   $bytes = New-Object byte[] 32
   $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
   $rng.GetBytes($bytes)
   $JARVIS_KEY = [Convert]::ToBase64String($bytes)
   $rng.Dispose()
   $JARVIS_KEY
   ~~~

   macOS/Linux:

   ~~~bash
   openssl rand -base64 32
   ~~~

   Keep the key private. Do not put it in source code, screenshots, or Git.

3. Add it as a Worker secret; paste the generated key when prompted:

   ~~~bash
   npx wrangler secret put JARVIS_ACCESS_KEY
   ~~~

4. Run tests and local preview:

   ~~~bash
   npm test
   npx wrangler dev
   ~~~

   If the local Workers AI binding is unavailable, deploy first and test the hosted health endpoint and chat. Tests use a mocked AI binding and do not call a paid API.

5. Deploy:

   ~~~bash
   npx wrangler deploy
   ~~~

   Save the HTTPS workers.dev URL printed by Wrangler. Check /api/health reports ok=true, ai_configured=true and access_key_configured=true. If Workers AI is not enabled, check account availability and limits.

6. Open the deployed URL in Chrome on Android. Menu ⋮ → Add to Home screen (label may vary). Enter the secret key in JARVIS. It is held in tab session storage, not localStorage; avoid shared devices.

## API

- GET /api/health: public service status only; never returns the secret.
- POST /api/chat: requires Content-Type: application/json and X-Jarvis-Key: your secret. JSON body example: {"message":"Explain Terraform plan","history":[]}.
- Other /api/* routes return 404.
- The Worker calls the configured model. It does not execute shell commands or cloud operations.

## Tests

Run npm test from this folder. Tests use a mocked AI binding and do not deploy anything.

## Security checklist before real cloud automation

- Require human approval before any write/destructive action.
- Use a separate executor with short-lived, least-privilege credentials; never give the public Worker shell access.
- Start with read-only GitHub/AWS/Kubernetes tools and allowlist commands.
- Add per-user authentication, rate limiting, abuse monitoring and quotas before sharing the URL.
- Redact secrets from logs; never send secrets into model prompts.
- Add persistent memory only after defining retention/export/delete policy.
- Add integration tests and independent review before production use.

## Roadmap

1. MVP: mobile chat, Workers AI, access-key gate and tests.
2. Authenticated GitHub read-only repository/status tools and safe code review.
3. Read-only AWS/EKS/Terraform diagnostics via MCP or a separate executor.
4. Approval queue for proposed changes; plan/diff output before execution.
5. Optional voice I/O, durable memory, notifications and productivity tools.

This is a working starter implementation, not yet a fully autonomous JARVIS. Cloud deployment still requires your Cloudflare account action and secret setup.
