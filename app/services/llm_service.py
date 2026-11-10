"""Talk to the locally running Ollama server (free, no API key)."""
import re

import requests

from config import Config


class LLMUnavailable(Exception):
    pass


def chat(messages):
    try:
        resp = requests.post(
            f"{Config.OLLAMA_URL}/api/chat",
            json={
                "model": Config.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.1, "num_ctx": 4096},
            },
            timeout=Config.LLM_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.ConnectionError:
        raise LLMUnavailable("The AI model is not running. Start Ollama and try again.")
    except requests.RequestException as exc:
        raise LLMUnavailable(f"The AI model returned an error: {exc}")
    text = resp.json()["message"]["content"]
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
