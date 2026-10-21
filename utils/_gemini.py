"""Google Gemini client, replacing the retired LongCat API.

Uses the native generateContent endpoint rather than Gemini's OpenAI
compatibility layer, so the model id is a path segment and the system prompt is
sent as system_instruction rather than a message with role "system".

The model id is read from the environment so a rename upstream is a Vercel
setting change rather than a redeploy.
"""

import requests

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODEL

BASE = "https://generativelanguage.googleapis.com/v1beta"
# Two attempts at this budget cap the AI path at ~20s, well inside the
# function limit that the much slower NBA每日預測 path already needs.
# 8s proved too tight: it cut off calls that were still in flight.
TIMEOUT = 10
# Load shedding and rate limiting, as opposed to a bad request or model id.
RETRYABLE = (429, 500, 502, 503, 504)

# The bot's persona is deliberately crude and this is a private friend group, so
# the filters are relaxed as far as the API allows. Responses are still checked
# for a block below, because these settings are a request, not a guarantee.
SAFETY_SETTINGS = [
    {"category": category, "threshold": "BLOCK_NONE"}
    for category in (
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
    )
]


class GeminiError(Exception):
    pass


def generate(
    systemPrompt: str,
    userPrompt: str,
    maxTokens: int,
    temperature: float,
    responseSchema: dict = None,
):
    """Single-turn completion, falling back to a second model on 503.

    With responseSchema the model is constrained to JSON matching it, and the
    raw JSON text is returned for the caller to parse.

    Raises GeminiError with a readable message.
    """
    models = [GEMINI_MODEL]
    if GEMINI_FALLBACK_MODEL and GEMINI_FALLBACK_MODEL != GEMINI_MODEL:
        models.append(GEMINI_FALLBACK_MODEL)

    lastError = None
    for model in models:
        try:
            return _generate_once(
                model, systemPrompt, userPrompt, maxTokens, temperature, responseSchema
            )
        except GeminiError as err:
            lastError = err
            if not getattr(err, "retryable", False):
                raise
    raise lastError


def _generate_once(
    model: str,
    systemPrompt: str,
    userPrompt: str,
    maxTokens: int,
    temperature: float,
    responseSchema: dict = None,
):
    if not GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY 未設定")

    payload = {
        "system_instruction": {"parts": [{"text": systemPrompt}]},
        "contents": [{"role": "user", "parts": [{"text": userPrompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": maxTokens,
        },
        "safetySettings": SAFETY_SETTINGS,
    }
    if responseSchema:
        payload["generationConfig"]["responseMimeType"] = "application/json"
        payload["generationConfig"]["responseSchema"] = responseSchema

    try:
        response = requests.post(
            f"{BASE}/models/{model}:generateContent",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY,
            },
            json=payload,
            timeout=TIMEOUT,
        )
    except requests.RequestException as err:
        error = GeminiError(f"連線失敗: {type(err).__name__}")
        error.retryable = True
        raise error

    if response.status_code == 404:
        raise GeminiError(f"找不到模型 {model}，請確認 GEMINI_MODEL 環境變數")
    if response.status_code != 200:
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = response.text[:200]
        error = GeminiError(f"HTTP {response.status_code}: {detail}")
        error.retryable = response.status_code in RETRYABLE
        raise error

    data = response.json()

    blocked = (data.get("promptFeedback") or {}).get("blockReason")
    if blocked:
        raise GeminiError(f"提示被安全機制擋下 ({blocked})")

    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiError("沒有回應內容")

    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()

    if not text:
        reason = candidate.get("finishReason", "UNKNOWN")
        if reason == "MAX_TOKENS":
            # Usually a thinking model consuming the budget before emitting text;
            # worth trying the other model rather than failing outright.
            error = GeminiError("回應超過長度限制")
            error.retryable = True
            raise error
        raise GeminiError(f"回應是空的 (finishReason={reason})")

    return text


def list_models():
    """Diagnostic helper: which model ids this key can actually use."""
    if not GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY 未設定")
    response = requests.get(
        f"{BASE}/models",
        headers={"x-goog-api-key": GEMINI_API_KEY},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return [
        model["name"].replace("models/", "")
        for model in response.json().get("models", [])
        if "generateContent" in model.get("supportedGenerationMethods", [])
    ]
