import os
import httpx
from backend.utils.logging import logger
from .base import CoachModelProvider, ModelProviderError


PRIMARY_OLLAMA = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
LOCAL_FALLBACK = 'http://localhost:11434'


class OllamaCoachProvider(CoachModelProvider):
    name = "ollama"

    async def generate(self, *, prompt: str, model: str, fast: bool) -> str:
        last_error = None
        # Adaptive timeouts based on fast flag
        # More aggressive timeouts for fast mode to prevent long blocking calls
        req_timeout = lambda: httpx.Timeout(
            25 if fast else 180,   # total
            connect=3 if fast else 8,
            read=20 if fast else 170,
        )
        # Prefer explicit host; if it looks like a docker hostname and fails DNS quickly, we'll continue to localhost
        hosts = [PRIMARY_OLLAMA, LOCAL_FALLBACK]
        # If PRIMARY_OLLAMA already equals localhost variant, avoid duplicate
        if PRIMARY_OLLAMA.startswith('http://localhost'):
            hosts = [PRIMARY_OLLAMA]
        for host in hosts:
            try:
                async with httpx.AsyncClient(timeout=req_timeout()) as client:
                    # connectivity check
                    try:
                        tags = await client.get(f"{host}/api/tags")
                        if tags.status_code >= 400:
                            raise ModelProviderError(f"tags {tags.status_code}")
                    except Exception as e:  # connectivity failure  # noqa: BLE001
                        last_error = f"tags:{e}"
                        logger.warning("ollama_tags_failed", host=host, error=str(e))
                        continue
                    try:
                        r = await client.post(
                            f"{host}/api/generate",
                            json={
                                "model": model,
                                "prompt": prompt,
                                "stream": False,
                                "keep_alive": "5m",
                                "options": {
                                    "temperature": 0.4 if fast else 0.6,
                                    "top_p": 0.85 if fast else 0.9,
                                    "num_predict": 160 if fast else 512,  # shorten fast responses
                                },
                            },
                        )
                        r.raise_for_status()
                        data = r.json()
                        text = (data.get('response') or '').strip()
                        logger.info("ollama_generate_success", host=host, model=model, chars=len(text), fast=fast)
                        return text
                    except httpx.TimeoutException as te:
                        last_error = f"timeout:{te}"
                        logger.warning("ollama_generate_timeout", host=host, error=str(te))
                        continue
                    except Exception as e:  # other request errors  # noqa: BLE001
                        last_error = str(e)
                        logger.warning("ollama_generate_failed", host=host, error=last_error)
                        continue
            except Exception as outer:  # noqa: BLE001
                last_error = str(outer)
                continue
        # After exhausting hosts without return
        raise ModelProviderError(last_error or "model backend unavailable (ollama)")
