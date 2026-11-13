# ANI — Coordenador Central
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import flwr as fl
from flwr.common import Metrics, Parameters
from flwr.server import ServerConfig

import structlog
from prometheus_client import Counter, Gauge, start_http_server

from agregador import AgregadorANI
from validador import ValidadorGradientes
from checkpoint import CheckpointManager

log = structlog.get_logger()

ROUNDS_COMPLETOS  = Counter("ani_rounds_completos_total", "Rounds completos")
NOS_ATIVOS        = Gauge("ani_nos_ativos", "Nós ativos agora")
PERDA_MEDIA       = Gauge("ani_perda_media", "Loss médio atual")


class CoordenadorANI:
    def __init__(self, host="0.0.0.0", port=9090,
                 rounds=10_000, nos_minimos=2):
        self.host        = host
        self.port        = port
        self.rounds      = rounds
        self.nos_minimos = nos_minimos
        self.agregador   = AgregadorANI()
        self.validador   = ValidadorGradientes()
        self.checkpoint  = CheckpointManager("./checkpoints")
        self.rounds_ok   = 0
        log.info("ani.coordenador.init", host=host, port=port)

    def ao_finalizar_round(self, rnd, parameters, metrics):
        loss = metrics.get("loss", 0.0)
        PERDA_MEDIA.set(loss)
        ROUNDS_COMPLETOS.inc()
        self.rounds_ok += 1
        if rnd % 100 == 0:
            self.checkpoint.salvar(parameters, rnd, metrics)
        log.info("ani.round.fim", round=rnd, loss=loss)
        return parameters

    def construir_estrategia(self):
        return AgregadorANI(
            fraction_fit=0.1,
            fraction_evaluate=0.05,
            min_fit_clients=self.nos_minimos,
            min_evaluate_clients=self.nos_minimos,
            min_available_clients=self.nos_minimos,
            on_fit_config_fn=lambda r: {
                "round": r, "epochs": 1,
                "batch_size": 4, "learning_rate": 2e-5,
            },
            fit_metrics_aggregation_fn=lambda m: {
                "loss": sum(n*x["loss"] for n,x in m) / sum(n for n,_ in m)
            },
        )

    def iniciar(self):
        start_http_server(8000)
        log.info("🌱 ANI acordando...")
        log.info(f"🌐 Aguardando nós em {self.host}:{self.port}")
        fl.server.start_server(
            server_address=f"{self.host}:{self.port}",
            config=ServerConfig(num_rounds=self.rounds),
            strategy=self.construir_estrategia(),
        )


if __name__ == "__main__":
    import typer
    app = typer.Typer()

    @app.command()
    def main(host: str = "0.0.0.0", port: int = 9090,
             rounds: int = 10_000, nos_minimos: int = 2):
        """Inicia o Coordenador Central da ANI."""
        CoordenadorANI(host, port, rounds, nos_minimos).iniciar()

    app()
