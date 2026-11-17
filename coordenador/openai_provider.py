"""Provedor OpenAI opcional para o chat ANI. Nunca exponha a chave ao frontend."""
import os
import httpx

async def responder_openai(messages, max_tokens=512, temperature=0.7):
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY não configurada")
    model = os.getenv("ANI_OPENAI_MODEL", "gpt-4.1-mini")
    allowed = {"system", "user", "assistant"}
    payload = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content[:12000]}
                     for m in messages[-20:] if m.role in allowed],
        "max_completion_tokens": min(max(1, max_tokens), 1024),
    }
    # Alguns modelos não aceitam temperature; deixar a configuração padrão.
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    choice = data["choices"][0]["message"]["content"] or ""
    usage = data.get("usage", {})
    return choice, data.get("model", model), int(usage.get("total_tokens", 0))
