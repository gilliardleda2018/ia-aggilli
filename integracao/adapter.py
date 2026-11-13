# ANI — Adapter para o Aggilli Chat
# Substitui Claude/GPT pela ANI de forma transparente
import httpx, time
from typing import Dict, List, Optional
import structlog

log = structlog.get_logger()


class ANIAdapter:
    """
    Transição suave:
    - ANI confiante  → responde (custo zero)
    - ANI aprendendo → fallback externo temporário
    """
    def __init__(self, ani_url="http://ani.aggilli.com.br",
                 ani_token="",
                 fallback_model="claude-3-5-sonnet-20241022",
                 confianca_minima=0.85):
        self.ani_url          = ani_url.rstrip("/")
        self.ani_token        = ani_token
        self.fallback_model   = fallback_model
        self.confianca_minima = confianca_minima
        self._total = self._ani = self._fallback = 0
        self._inicio = time.time()

    async def completar(self, messages: List[Dict],
                        dominio: Optional[str] = None,
                        max_tokens: int = 2048,
                        temperatura: float = 0.7) -> Dict:
        self._total += 1
        r = await self._tentar_ani(messages, dominio, max_tokens, temperatura)
        if r and r.get("confianca", 0) >= self.confianca_minima:
            self._ani += 1
            log.info("ani.adapter.ani", confianca=r["confianca"])
            return {"content": r["content"], "model": "ani-v1",
                    "custo": 0.0, "fonte": "ani"}
        self._fallback += 1
        log.info("ani.adapter.fallback", modelo=self.fallback_model)
        return await self._usar_fallback(messages)

    async def _tentar_ani(self, messages, dominio, max_tokens, temperatura):
        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(
                    f"{self.ani_url}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.ani_token}"},
                    json={"messages": messages, "dominio": dominio,
                          "max_tokens": max_tokens, "temperature": temperatura})
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.warning("ani.adapter.falhou", erro=str(e))
            return None

    async def _usar_fallback(self, messages) -> Dict:
        # TODO: integrar Anthropic SDK
        return {"content": "[Fallback — ANI aprendendo]",
                "model": self.fallback_model,
                "custo": 0.001, "fonte": "externo"}

    def stats(self) -> Dict:
        pct = self._ani / self._total * 100 if self._total else 0
        return {
            "total": self._total,
            "ani": self._ani,
            "fallback": self._fallback,
            "pct_ani": round(pct, 1),
            "meta": 90.0,
            "status": "✅ Meta atingida" if pct >= 90 else f"🔄 {pct:.1f}% — evoluindo",
            "uptime_h": round((time.time() - self._inicio) / 3600, 1),
        }
