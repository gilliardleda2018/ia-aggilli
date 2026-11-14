#!/usr/bin/env python3
import sys, time, schedule
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from buscador import BuscadorANI
import structlog
log = structlog.get_logger()

TOPICOS = [
    "inteligência artificial", "machine learning",
    "computação distribuída", "federated learning",
    "história do Brasil", "filosofia", "física quântica",
    "biologia", "matemática", "astronomia", "economia",
    "literatura", "música", "arte", "tecnologia",
]

class AutoTreinoANI:
    def __init__(self):
        self.buscador     = BuscadorANI()
        self.topico_atual = 0
        self.aprendidos   = 0

    def estudar(self):
        t = TOPICOS[self.topico_atual % len(TOPICOS)]
        r = self.buscador.buscar_e_aprender(t)
        if r["contexto"]:
            self.aprendidos += 1
            print(f"🧠 [{self.aprendidos}] {t} ✅ ({len(r['contexto'])} chars)")
        self.topico_atual += 1

    def iniciar(self, intervalo=30):
        print(f"🌱 Auto-treino — {len(TOPICOS)} tópicos — {intervalo}min/ciclo")
        self.estudar()
        schedule.every(intervalo).minutes.do(self.estudar)
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    AutoTreinoANI().iniciar(30)
