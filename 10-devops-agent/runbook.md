# ECS Incident Runbook

## Observe
Identify cluster/service, desired/running/pending counts, deployment history, task stop reasons, target health, application logs, image tag and task definition.

## Hypothesize
Possible causes include startup failure, image pull failure, secret/config mismatch, port mismatch, health-check failure or unavailable dependency.

## Validate
Collect evidence that can falsify the hypothesis.

## Propose
Explain change, reason, risk, rollback and verification.

## Approval
Require explicit approval for production mutation.

## Verify
Check stabilization, task health, target health, logs and user-facing behavior.

A green command exit code is not proof that the goal succeeded.