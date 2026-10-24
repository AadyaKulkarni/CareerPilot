import httpx
from app.services.crypto import decrypt

DEFAULTS = {"openai": "gpt-4o-mini", "openai-compatible": "gpt-4o-mini", "gemini": "gemini-2.5-flash", "anthropic": "claude-sonnet-5-5"}


async def chat(provider: str, model: str, encrypted_key: str, system: str, prompt: str, temperature: float = 0.3, json_mode: bool = False) -> str:
    """Single provider-agnostic completion. API keys stay server-side."""
    key = decrypt(encrypted_key); p = provider.lower(); model = model or DEFAULTS.get(p, "")
    async with httpx.AsyncClient(timeout=60) as client:
        if p in ("openai", "openai-compatible"):
            body = {"model": model, "temperature": temperature, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
            if json_mode: body["response_format"] = {"type": "json_object"}
            r = await client.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body)
            r.raise_for_status(); return r.json()["choices"][0]["message"]["content"]
        if p == "gemini":
            body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temperature}}
            if json_mode: body["generationConfig"]["responseMimeType"] = "application/json"
            r = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", headers={"x-goog-api-key": key}, json=body)
            r.raise_for_status(); return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        if p == "anthropic":
            body = {"model": model, "max_tokens": 2000, "temperature": temperature, "system": system, "messages": [{"role": "user", "content": prompt}]}
            r = await client.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, json=body)
            r.raise_for_status(); return "".join(b.get("text", "") for b in r.json()["content"])
    raise ValueError("Unsupported provider. Use OpenAI, Gemini or Anthropic.")


async def enhance(provider: str, model: str, encrypted_key: str, section: str, text: str):
    prompt = (f"Rewrite this resume {section} professionally, concisely and ATS-friendly. Preserve facts exactly; "
              f"do not invent metrics, technologies or achievements. Text: {text}")
    return await chat(provider, model, encrypted_key, "You are a truthful resume editor.", prompt)
