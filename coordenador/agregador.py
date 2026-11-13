# ANI — Agregador FedAvg customizado
from typing import Dict, List, Optional, Tuple
import numpy as np
from flwr.common import FitRes, Parameters, Scalar, parameters_to_ndarrays
from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy import FedAvg
import structlog

log = structlog.get_logger()


class AgregadorANI(FedAvg):
    def aggregate_fit(self, server_round, results, failures):
        if not results:
            return None, {}
        validos = self._filtrar(results)
        log.info("ani.agregacao", round=server_round,
                 total=len(results), validos=len(validos))
        if not validos:
            return None, {}
        return super().aggregate_fit(server_round, validos, failures)

    def _filtrar(self, results):
        normas = []
        for _, r in results:
            arrays = parameters_to_ndarrays(r.parameters)
            normas.append(sum(np.linalg.norm(a) for a in arrays))
        normas = np.array(normas)
        limite = np.mean(normas) + 3 * np.std(normas)
        return [(p, r) for (p, r), n in zip(results, normas) if n <= limite]

    def avaliar(self, parameters):
        from flwr.common import parameters_to_ndarrays
        arrays = parameters_to_ndarrays(parameters)
        norma  = sum(np.linalg.norm(a) for a in arrays)
        loss   = 1.0 / (1.0 + norma * 0.001)
        return loss, {"loss": loss}
