import os

import httpx

from app.agent.ollama_client import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_URL


def configured_model() -> str:
    return os.getenv("TENDERGUARD_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()


def _tags_url() -> str:
    chat_url = os.getenv("TENDERGUARD_OLLAMA_URL", DEFAULT_OLLAMA_URL).strip()
    if chat_url.endswith("/api/chat"):
        return f"{chat_url[:-len('/api/chat')]}/api/tags"
    return f"{chat_url.rstrip('/')}/api/tags"


async def ollama_model_status() -> str:
    model = configured_model()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(_tags_url())
            response.raise_for_status()
            installed = {
                str(item.get("name", ""))
                for item in response.json().get("models", [])
                if isinstance(item, dict)
            }
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return "UNAVAILABLE"
    return "AVAILABLE" if model in installed else "MODEL_MISSING"
