from buscador import BuscadorANI
import requests, json
from pathlib import Path
import structlog
log = structlog.get_logger()

class FontesANI:
    def __init__(self):
        self.buscador = BuscadorANI()

    def buscar_tudo(self, query: str) -> dict:
        return self.buscador.buscar_e_aprender(query)
