# ANI — Monitor do Nó
import time
from dataclasses import dataclass, field
from typing import List
import structlog

log = structlog.get_logger()


@dataclass
class EstatisticasRound:
    round_num: int
    loss:      float
    amostras:  int
    timestamp: float = field(default_factory=time.time)


class MonitorNo:
    def __init__(self):
        self.historico:  List[EstatisticasRound] = []
        self.inicio      = time.time()
        self.round_atual = 0

    def registrar_round(self, loss: float, amostras: int):
        self.round_atual += 1
        self.historico.append(
            EstatisticasRound(self.round_atual, loss, amostras))
        log.info("ani.monitor.round", round=self.round_atual,
                 loss=round(loss, 4), amostras=amostras,
                 uptime_min=round((time.time() - self.inicio) / 60, 1))

    @property
    def reputacao(self) -> float:
        if len(self.historico) < 3:
            return 0.5
        losses = [r.loss for r in self.historico[-10:]]
        media  = sum(losses) / len(losses)
        desvio = (sum((l - media)**2 for l in losses) / len(losses)) ** 0.5
        return round(max(0.0, min(1.0, 1.0 - desvio)), 3)

    def status(self) -> dict:
        return {
            "rounds_completos": self.round_atual,
            "uptime_min":       round((time.time() - self.inicio) / 60, 1),
            "reputacao":        self.reputacao,
            "loss_ultimo":      self.historico[-1].loss if self.historico else None,
            "amostras_total":   sum(r.amostras for r in self.historico),
        }
