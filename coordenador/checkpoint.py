# ANI — Checkpoint Manager
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from flwr.common import Parameters, ndarrays_to_parameters, parameters_to_ndarrays
import structlog

log = structlog.get_logger()


class CheckpointManager:
    def __init__(self, base_path: str = "./checkpoints"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def salvar(self, parameters: Parameters, round_num: int,
               metrics: Optional[Dict] = None) -> str:
        ts    = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        nome  = f"ani_r{round_num:06d}_{ts}"
        pasta = self.base_path / nome
        pasta.mkdir(parents=True, exist_ok=True)
        arrays = parameters_to_ndarrays(parameters)
        np.savez_compressed(str(pasta / "model.npz"), *arrays)
        with open(pasta / "meta.json", "w") as f:
            json.dump({"round": round_num, "timestamp": ts,
                       "metrics": metrics or {}, "versao": "1.0"}, f, indent=2)
        latest = self.base_path / "latest"
        if latest.is_symlink():
            latest.unlink()
        latest.symlink_to(nome)
        log.info("ani.checkpoint.salvo", nome=nome, round=round_num)
        return str(pasta)

    def carregar_ultimo(self) -> Optional[Parameters]:
        latest = self.base_path / "latest"
        if not latest.exists():
            return None
        data   = np.load(str(latest.resolve() / "model.npz"))
        arrays = [data[k] for k in data.files]
        return ndarrays_to_parameters(arrays)

    def listar(self) -> list:
        return sorted([d.name for d in self.base_path.iterdir()
                       if d.is_dir() and d.name.startswith("ani_r")])
