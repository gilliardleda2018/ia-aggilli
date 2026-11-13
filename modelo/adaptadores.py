# ANI — Adaptadores LoRA por Domínio
from dataclasses import dataclass
from typing import Dict, Optional
from peft import LoraConfig, TaskType, get_peft_model, PeftModel
from transformers import AutoModelForCausalLM
import torch
import structlog

log = structlog.get_logger()


@dataclass
class ConfigAdaptador:
    dominio: str
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: tuple = ("q_proj", "v_proj")
    descricao: str = ""


DOMINIOS: Dict[str, ConfigAdaptador] = {
    "agro":       ConfigAdaptador("agro",       descricao="Pecuária: RFID, pesagens, GMD, Aggilli Agro."),
    "obras":      ConfigAdaptador("obras",      descricao="Construção: avanço físico, diário, Em Obras."),
    "transporte": ConfigAdaptador("transporte", descricao="TMS: fretes, viagens, MG Transportes."),
    "geral":      ConfigAdaptador("geral", r=8, lora_alpha=16,
                                  descricao="Ecossistema Aggilli geral."),
}


class GerenciadorAdaptadores:
    def __init__(self, modelo_base="meta-llama/Meta-Llama-3.1-8B"):
        self.modelo_base  = modelo_base
        self._base        = None
        self._adaptadores: Dict[str, PeftModel] = {}

    def carregar_base(self):
        if self._base is not None:
            return
        log.info("ani.adaptadores.carregando_base", modelo=self.modelo_base)
        self._base = AutoModelForCausalLM.from_pretrained(
            self.modelo_base, torch_dtype=torch.float16, device_map="auto")

    def obter(self, dominio: str) -> PeftModel:
        if dominio not in DOMINIOS:
            dominio = "geral"
        if dominio in self._adaptadores:
            return self._adaptadores[dominio]
        self.carregar_base()
        c = DOMINIOS[dominio]
        modelo = get_peft_model(self._base, LoraConfig(
            task_type=TaskType.CAUSAL_LM, r=c.r,
            lora_alpha=c.lora_alpha, lora_dropout=c.lora_dropout,
            target_modules=list(c.target_modules)))
        self._adaptadores[dominio] = modelo
        log.info("ani.adaptadores.criado", dominio=dominio)
        return modelo

    def listar(self) -> Dict[str, str]:
        return {k: v.descricao for k, v in DOMINIOS.items()}
