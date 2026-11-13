# ANI — Compressor de Gradientes (~1000x)
from typing import List
import numpy as np
import structlog

log = structlog.get_logger()


class CompressorGradientes:
    def __init__(self, ratio: float = 0.001):
        assert 0 < ratio <= 1.0
        self.ratio = ratio

    def comprimir(self, gradientes: List[np.ndarray]) -> List[np.ndarray]:
        comprimidos = [self._comprimir_array(g) for g in gradientes]
        antes  = sum(g.nbytes for g in gradientes)
        depois = sum(g.nbytes for g in comprimidos)
        log.debug("ani.compressor", antes_kb=antes//1024,
                  depois_kb=depois//1024,
                  reducao=f"{antes/max(depois,1):.0f}x")
        return comprimidos

    def descomprimir(self, gradientes: List[np.ndarray]) -> List[np.ndarray]:
        return [g.astype(np.float32) for g in gradientes]

    def _comprimir_array(self, grad: np.ndarray) -> np.ndarray:
        forma  = grad.shape
        plano  = grad.flatten()
        k      = max(1, int(len(plano) * self.ratio))
        idx    = np.argpartition(np.abs(plano), -k)[-k:]
        mascara = np.zeros_like(plano)
        mascara[idx] = plano[idx]
        maximo  = np.max(np.abs(mascara)) + 1e-8
        return np.clip(mascara / maximo * 127, -127, 127).astype(np.int8).reshape(forma)
