# 14 — AWS Bedrock

This lesson connects the local agent loop to a real model through Amazon Bedrock. The goal, state, typed tool registry, policy checks, and verification still run in this repository; Bedrock only proposes `Action` objects. The model never receives AWS credentials and cannot execute tools directly.

## Local setup

Use the existing local Python environment and install the optional AWS dependency:

```powershell
python -m pip install -e ".[aws]"
```

The AWS SDK uses its standard credential chain. Do not copy AWS keys into `.env`. Set `AWS_PROFILE` in your shell if you use a named profile. `.env` may set the non-secret values `AWS_REGION`, `BEDROCK_MODEL_ID`, and `BEDROCK_MAX_TOKENS`.

Check that the selected identity and region are right:

```powershell
aws sts get-caller-identity
aws bedrock get-foundation-model --region us-east-1 --model-identifier amazon.nova-micro-v1:0
```

The default model is Amazon Nova Micro in `us-east-1`; change it with `BEDROCK_MODEL_ID` and `AWS_REGION` if your account uses another available model or region. The identity needs `bedrock:InvokeModel` for that model. The first request can also depend on model-specific access requirements.

## Run

```powershell
python 14-aws/agent.py
```

The agent asks Bedrock to choose between one read-only project-facts tool and `finish`. It prints the model's rationale, tool observations, and the runtime's independent verification result. Output is bounded by `BEDROCK_MAX_TOKENS` (default 256). Each model call is metered by Bedrock; this lesson creates no AWS infrastructure.

The request sends the goal, available tool schemas, and prior observations to the selected Bedrock model. Do not include secrets or sensitive data in prompts or tool output.

## What to inspect

1. Compare `shared/bedrock.py` with `TranscriptModel` in `shared/model.py`.
2. Find where Bedrock's text response becomes a validated `Action`.
3. Confirm `AgentLoop` still validates tool arguments and checks the declared risk before execution.
4. Notice that success depends on an observed tool result, not the model saying it succeeded.

This is a local runtime calling a cloud model. It is not an internet-facing service deployment; the credentials remain on the local machine.
