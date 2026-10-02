"""Ollama router: proxies chat requests to a locally running Ollama server.

The backend talks to Ollama's HTTP API (`/api/chat`) and re-streams the reply
to the frontend as plain text chunks.
"""

import json
import os
from collections.abc import AsyncIterator
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Windows Ollama is reachable from WSL via localhost; from Docker use
# host.docker.internal (set OLLAMA_BASE_URL in the compose environment).
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

router = APIRouter(prefix="/ollama", tags=["ollama"])


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model: str | None = None


@router.get("/models")
async def list_models():
    """List models available on the Ollama server."""
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=5) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Ollama unreachable at {OLLAMA_BASE_URL}") from exc
    return {
        "default": OLLAMA_MODEL,
        "models": [m["name"] for m in response.json()["models"]],
    }


@router.post("/chat")
async def chat(request: ChatRequest):
    """Stream the model's reply to the given conversation as plain text."""
    payload = {
        "model": request.model or OLLAMA_MODEL,
        "messages": [m.model_dump() for m in request.messages],
        "stream": True,
        # reasoning models (e.g. qwen3.5) would otherwise spend the reply on thinking
        "think": False,
    }
    client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=httpx.Timeout(300, connect=5))

    # open the upstream request before streaming so failures become real HTTP errors
    try:
        upstream = await client.send(
            client.build_request("POST", "/api/chat", json=payload), stream=True
        )
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(502, f"Ollama unreachable at {OLLAMA_BASE_URL}") from exc

    if upstream.status_code != 200:
        detail = (await upstream.aread()).decode(errors="replace")
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(502, f"Ollama error {upstream.status_code}: {detail}")

    async def stream() -> AsyncIterator[str]:
        try:
            async for line in upstream.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if content := data.get("message", {}).get("content"):
                    yield content
                if data.get("done"):
                    break
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")
