# ANI — Preparador de Dados (LGPD-safe)
import hashlib, json, re
from pathlib import Path
from typing import Dict, List
import structlog

log = structlog.get_logger()


class PreparadorDadosANI:
    SENSIVEIS = [
        r"\d{3}[\.\-]?\d{3}[\.\-]?\d{3}[\-\.]?\d{2}",
        r"\d{2}[\.\-]?\d{3}[\.\-]?\d{3}[\/\-]?\d{4}[\-\.]?\d{2}",
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        r"\(\d{2}\)\s*\d{4,5}[\-\s]?\d{4}",
    ]

    def __init__(self, saida_path="./dados_treino"):
        self.saida = Path(saida_path)
        self.saida.mkdir(parents=True, exist_ok=True)

    def preparar_agro(self, registros: List[Dict]) -> int:
        pares = []
        for r in registros:
            h = self._hash(str(r.get("fazenda_id", "")))
            pares.append({
                "prompt": (
                    f"Fazenda {h[:8]}, lote {r.get('lote','A')}: "
                    f"{r.get('qtd_animais',0)} animais, "
                    f"peso médio {r.get('peso_medio',0):.1f} kg. GMD esperado?"
                ),
                "completion": (
                    f"GMD estimado: {r.get('gmd_estimado',0):.3f} kg/dia. "
                    f"Recomendação: {r.get('recomendacao','manter manejo atual')}."
                ),
            })
        return self._salvar("agro", pares)

    def preparar_obras(self, registros: List[Dict]) -> int:
        pares = []
        for r in registros:
            h  = self._hash(str(r.get("obra_id", "")))
            ap = r.get("avanco_previsto", 0)
            ar = r.get("avanco_real", 0)
            pares.append({
                "prompt": (
                    f"Obra {h[:8]}: previsto {ap:.1f}%, real {ar:.1f}%. Status?"
                ),
                "completion": (
                    f"Obra {'adiantada' if ar>=ap else 'atrasada'}. "
                    f"Desvio: {abs(ar-ap):.1f}pp. "
                    f"Ação: {r.get('acao','revisar cronograma')}."
                ),
            })
        return self._salvar("obras", pares)

    def preparar_transporte(self, registros: List[Dict]) -> int:
        pares = []
        for r in registros:
            h = self._hash(str(r.get("transportadora_id", "")))
            pares.append({
                "prompt": (
                    f"Transportadora {h[:8]}: "
                    f"{r.get('origem','?')} -> {r.get('destino','?')}, "
                    f"{r.get('peso_kg',0)} kg. Custo e prazo?"
                ),
                "completion": (
                    f"Custo: R$ {r.get('custo_estimado',0):.2f}. "
                    f"Prazo: {r.get('prazo_dias',1)} dia(s)."
                ),
            })
        return self._salvar("transporte", pares)

    def _salvar(self, dominio: str, pares: List[Dict]) -> int:
        arq = self.saida / f"{dominio}.jsonl"
        with open(arq, "w", encoding="utf-8") as f:
            for p in pares:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        log.info("ani.dados.salvos", dominio=dominio, pares=len(pares))
        return len(pares)

    def _hash(self, v: str) -> str:
        return hashlib.sha256(v.encode()).hexdigest()

    def limpar(self, texto: str) -> str:
        for p in self.SENSIVEIS:
            texto = re.sub(p, "[REMOVIDO]", texto)
        return texto
