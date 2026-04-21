import json
import os
import urllib.request


LLM_ENABLED = os.getenv("SLATE808_ENABLE_LLM", "false").strip().lower() == "true"
MODEL_NAME = "smollm2:1.7b"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def is_llm_enabled() -> bool:
    return LLM_ENABLED


def build_prompt(request: str) -> str:
    return f"""
You are helping a reasoning engine generate candidate plan steps.

Task:
Generate a short list of 5 steps for this request:
{request}

Rules:
- Return ONLY valid JSON
- Use this exact format:
{{"steps": ["step 1", "step 2", "step 3", "step 4", "step 5"]}}
- Each step must be actionable
- Keep steps concise
- Do not include explanations
- Do not add markdown
- Do not add code fences
- Do not add line breaks inside step text
"""


def repair_model_json(text: str) -> str:
    """
    Repair common small-model JSON mistakes.
    """
    cleaned = text.strip()

    if cleaned.startswith('{"steps": [') and cleaned.endswith('"}'):
        cleaned = cleaned[:-1] + ']}'

    return cleaned


def generate_with_llm(request: str) -> list | None:
    """
    Call Ollama's local API with fast-fail + single retry.
    Returns a list of steps or None.
    """

    if not LLM_ENABLED:
        return None

    prompt = build_prompt(request)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    def call_api(timeout: int) -> list | None:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")

        data = json.loads(raw)
        model_output = data.get("response", "").strip()
        repaired_output = repair_model_json(model_output)
        parsed = json.loads(repaired_output)

        steps = parsed.get("steps")
        if isinstance(steps, list) and all(isinstance(step, str) for step in steps):
            return steps

        return None

    try:
        return call_api(timeout=30)
    except Exception:
        try:
            return call_api(timeout=120)
        except Exception:
            return None