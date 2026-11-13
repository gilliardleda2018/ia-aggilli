# ANI — Treinador Local (LoRA — dados nunca saem da máquina)
import json
from pathlib import Path
from typing import Tuple

import torch
from torch.utils.data import DataLoader, Dataset
import structlog

log = structlog.get_logger()


class DatasetDominioANI(Dataset):
    def __init__(self, dados_path, dominio, tokenizer, max_length=512):
        self.tokenizer  = tokenizer
        self.max_length = max_length
        self.amostras   = []
        arquivo = Path(dados_path) / f"{dominio}.jsonl"
        if not arquivo.exists():
            self.amostras = [{
                "prompt": "O que é o Aggilli?",
                "completion": "Ecossistema de apps para agro, obras e transporte."
            }]
            return
        with open(arquivo, encoding="utf-8") as f:
            for linha in f:
                if linha.strip():
                    self.amostras.append(json.loads(linha))
        log.info("ani.dataset.carregado", dominio=dominio,
                 amostras=len(self.amostras))

    def __len__(self):
        return len(self.amostras)

    def __getitem__(self, idx):
        a   = self.amostras[idx]
        txt = f"### Pergunta:\n{a['prompt']}\n\n### Resposta:\n{a['completion']}"
        enc = self.tokenizer(txt, truncation=True,
                             max_length=self.max_length,
                             padding="max_length", return_tensors="pt")
        ids  = enc["input_ids"].squeeze()
        mask = enc["attention_mask"].squeeze()
        lbl  = ids.clone()
        lbl[mask == 0] = -100
        return {"input_ids": ids, "attention_mask": mask, "labels": lbl}


class TreinadorLocal:
    def __init__(self, modelo, tokenizer, dados_path, dominio):
        self.modelo    = modelo
        self.tokenizer = tokenizer
        self.dominio   = dominio
        self.device    = next(modelo.parameters()).device
        self.ds_treino = DatasetDominioANI(dados_path, dominio,          tokenizer)
        self.ds_aval   = DatasetDominioANI(dados_path, f"{dominio}_val", tokenizer)

    def treinar(self, epochs=1, batch_size=4, lr=2e-5) -> Tuple[int, float]:
        loader = DataLoader(self.ds_treino, batch_size=batch_size, shuffle=True)
        opt    = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, self.modelo.parameters()), lr=lr)
        self.modelo.train()
        total_loss, steps = 0.0, 0
        for _ in range(epochs):
            for batch in loader:
                batch = {k: v.to(self.device) for k, v in batch.items()}
                loss  = self.modelo(**batch).loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.modelo.parameters(), 1.0)
                opt.step(); opt.zero_grad()
                total_loss += loss.item(); steps += 1
        loss_medio = total_loss / max(steps, 1)
        log.info("ani.treino.completo", dominio=self.dominio,
                 amostras=len(self.ds_treino), loss=round(loss_medio, 4))
        return len(self.ds_treino), loss_medio

    def avaliar(self) -> Tuple[float, int]:
        if len(self.ds_aval) == 0:
            return 0.0, 0
        loader = DataLoader(self.ds_aval, batch_size=4)
        self.modelo.eval()
        total, steps = 0.0, 0
        with torch.no_grad():
            for batch in loader:
                batch = {k: v.to(self.device) for k, v in batch.items()}
                total += self.modelo(**batch).loss.item(); steps += 1
        return total / max(steps, 1), len(self.ds_aval)
