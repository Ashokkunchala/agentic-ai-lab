"""Optional Amazon Bedrock adapter for the shared model protocol.

Install the optional ``aws`` extra before importing this module. Credentials
come from the standard AWS SDK provider chain; keys never belong in source or
the project's .env file.
"""

from __future__ import annotations

from typing import Any

from .model import TranscriptModel


class BedrockModel(TranscriptModel):
    """Use Bedrock Converse while keeping the lab's validated Action boundary."""

    name = "bedrock"

    def __init__(
        self,
        model_id: str = "amazon.nova-micro-v1:0",
        region_name: str = "us-east-1",
        max_tokens: int = 512,
        client: Any | None = None,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must not be empty")
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")

        if client is None:
            try:
                import boto3
                from botocore.config import Config
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    'Amazon Bedrock support is optional; install it with `python -m pip install -e ".[aws]"`.'
                ) from exc

            client = boto3.client(
                "bedrock-runtime",
                region_name=region_name,
                config=Config(
                    retries={"max_attempts": 4, "mode": "adaptive"},
                    connect_timeout=5,
                    read_timeout=60,
                ),
            )

        self.model_id = model_id
        self.max_tokens = max_tokens
        self.client = client

    def call(self, prompt: str) -> str:
        response = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": self.max_tokens, "temperature": 0.0},
        )
        output = response.get("output")
        if not isinstance(output, dict):
            raise TypeError(f"Bedrock Converse output has unexpected type: {type(output).__name__}")
        message = output.get("message")
        if not isinstance(message, dict):
            raise TypeError(f"Bedrock Converse message has unexpected type: {type(message).__name__}")
        blocks = message.get("content", [])
        if isinstance(blocks, str):
            return blocks
        text_blocks = []
        for block in blocks:
            if isinstance(block, str):
                text_blocks.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                text_blocks.append(block["text"])
        return "\n".join(text_blocks)
