# ANI — Validador LGPD
import re
from typing import Dict, List, Tuple
import structlog

log = structlog.get_logger()


class ValidadorLGPD:
    PROIBIDOS = {
        "CPF":      r"\d{3}[\.\-]?\d{3}[\.\-]?\d{3}[\-\.]?\d{2}",
        "CNPJ":     r"\d{2}[\.\-]?\d{3}[\.\-]?\d{3}[\/\-]?\d{4}[\-\.]?\d{2}",
        "EMAIL":    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "TELEFONE": r"\(\d{2}\)\s*\d{4,5}[\-\s]?\d{4}",
    }

    def __init__(self):
        self.violacoes: List[str] = []

    def validar(self, registro: Dict, idx: int = 0) -> Tuple[bool, List[str]]:
        texto    = " ".join(str(v) for v in registro.values())
        encontrados = [
            f"{tipo} no registro {idx}"
            for tipo, p in self.PROIBIDOS.items()
            if re.search(p, texto)
        ]
        return len(encontrados) == 0, encontrados

    def filtrar(self, registros: List[Dict]) -> List[Dict]:
        limpos = [r for i, r in enumerate(registros)
                  if self.validar(r, i)[0]]
        removidos = len(registros) - len(limpos)
        if removidos:
            log.warning("ani.lgpd.removidos", count=removidos)
        return limpos
