# ANI — Validador de Gradientes
from typing import List
import numpy as np
import structlog

log = structlog.get_logger()


class ValidadorGradientes:
    def __init__(self, limite_norma: float = 1000.0):
        self.limite_norma = limite_norma
        self.rejeicoes: dict = {}

    def esta_ok(self, no_id: str, gradientes: List[np.ndarray]) -> bool:
        for g in gradientes:
            if np.any(np.isnan(g)) or np.any(np.isinf(g)):
                self._rejeitar(no_id, "nan_inf")
                return False
        norma = sum(np.linalg.norm(g) for g in gradientes)
        if norma > self.limite_norma:
            self._rejeitar(no_id, "norma_alta")
            return False
        if self.rejeicoes.get(no_id, 0) >= 5:
            log.warning("ani.no.banido", no=no_id)
            return False
        return True

    def _rejeitar(self, no_id, motivo):
        self.rejeicoes[no_id] = self.rejeicoes.get(no_id, 0) + 1
        log.warning("ani.gradiente.rejeitado", no=no_id, motivo=motivo)

    def resetar_no(self, no_id: str):
        self.rejeicoes.pop(no_id, None)
