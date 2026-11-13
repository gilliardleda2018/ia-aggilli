# ANI — Cliente de Nó
from typing import Dict, List, Tuple
import numpy as np
import torch
import flwr as fl
from flwr.common import NDArrays, Scalar
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import get_peft_model, LoraConfig, TaskType

from treinador_local import TreinadorLocal
from compressor import CompressorGradientes
from monitor import MonitorNo

import structlog
log = structlog.get_logger()


class NoANI(fl.client.NumPyClient):
    """
    Treina localmente e envia apenas gradientes comprimidos.
    Dados NUNCA saem desta máquina.
    """
    DOMINIOS = {"agro", "obras", "transporte", "geral"}

    def __init__(self, servidor, dominio="geral",
                 modelo_base="meta-llama/Meta-Llama-3.1-8B",
                 dados_path="./dados_locais"):
        assert dominio in self.DOMINIOS, f"Domínio inválido: {dominio}"
        self.servidor    = servidor
        self.dominio     = dominio
        self.modelo_base = modelo_base
        self.dados_path  = dados_path
        self.compressor  = CompressorGradientes(ratio=0.001)
        self.monitor     = MonitorNo()
        log.info("ani.no.init", dominio=dominio, servidor=servidor)
        self._carregar_modelo()

    def _carregar_modelo(self):
        log.info("ani.no.carregando", base=self.modelo_base)
        self.tokenizer = AutoTokenizer.from_pretrained(self.modelo_base)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        base = AutoModelForCausalLM.from_pretrained(
            self.modelo_base, torch_dtype=torch.float16, device_map="auto")
        lora = LoraConfig(task_type=TaskType.CAUSAL_LM, r=16,
                          lora_alpha=32, lora_dropout=0.05,
                          target_modules=["q_proj", "v_proj"])
        self.modelo   = get_peft_model(base, lora)
        self.treinador = TreinadorLocal(self.modelo, self.tokenizer,
                                        self.dados_path, self.dominio)
        log.info("ani.no.pronto", dominio=self.dominio)

    def get_parameters(self, config) -> NDArrays:
        return [p.detach().cpu().numpy()
                for p in self.modelo.parameters() if p.requires_grad]

    def fit(self, parameters, config):
        self._atualizar(parameters)
        amostras, loss = self.treinador.treinar(
            epochs=int(config.get("epochs", 1)),
            batch_size=int(config.get("batch_size", 4)),
            lr=float(config.get("learning_rate", 2e-5)))
        grads = self.compressor.comprimir(self.get_parameters(config))
        log.info("ani.no.contribuicao", dominio=self.dominio,
                 amostras=amostras, loss=round(loss, 4))
        self.monitor.registrar_round(loss=loss, amostras=amostras)
        return grads, amostras, {"loss": loss}

    def evaluate(self, parameters, config):
        self._atualizar(parameters)
        loss, amostras = self.treinador.avaliar()
        return loss, amostras, {"loss": loss}

    def _atualizar(self, parameters):
        treinaveis = [p for p in self.modelo.parameters() if p.requires_grad]
        for param, novo in zip(treinaveis, parameters):
            param.data = torch.tensor(novo).to(param.device)

    def iniciar(self):
        log.info("ani.no.conectando", servidor=self.servidor)
        fl.client.start_numpy_client(server_address=self.servidor, client=self)


if __name__ == "__main__":
    import typer
    cli = typer.Typer()

    @cli.command()
    def main(servidor: str = "ani.aggilli.com.br:9090",
             dominio: str  = "geral",
             dados: str    = "./dados_locais"):
        """Inicia um nó participante da rede ANI."""
        NoANI(servidor=servidor, dominio=dominio, dados_path=dados).iniciar()

    cli()
