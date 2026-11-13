# ANI — API REST (FastAPI)
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import structlog
from coordenador.piloto import router as piloto_router

log = structlog.get_logger()

app = FastAPI(
    title="ANI — Aggilli Native Intelligence",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"])

app.include_router(piloto_router)

_inicio = time.time()
_estado = {
    "nos_ativos": 0,
    "rounds_completos": 0,
    "versao": "ani-v1.0",
    "confianca_media": 0.0,
}


class MensagemChat(BaseModel):
    role: str
    content: str

class RequisicaoChat(BaseModel):
    messages: List[MensagemChat]
    max_tokens: int = 2048
    temperature: float = 0.7
    dominio: Optional[str] = None

class RespostaChat(BaseModel):
    content: str
    model: str    = "ani-v1"
    confianca: float
    tokens_usados: int
    custo: float  = 0.0


async def verificar_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido")
    return authorization.split(" ")[1]


@app.get("/status")
async def status():
    return {
        **_estado,
        "uptime_segundos": round(time.time() - _inicio, 1)
    }

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/v1/chat/completions", response_model=RespostaChat)
async def completar(
    req: RequisicaoChat,
    token: str = Depends(verificar_token)
):
    ultima   = req.messages[-1].content if req.messages else ""
    resposta = (
        f"Olá! Sou a ANI — Aggilli Native Intelligence. "
        f"Domínio: {req.dominio or 'geral'}. "
        f"Você perguntou: {ultima[:100]}. "
        f"Ainda estou aprendendo, mas já estou viva! 🌱"
    )
    return RespostaChat(
        content=resposta,
        model=_estado["versao"],
        confianca=0.92,
        tokens_usados=len(resposta.split()),
        custo=0.0,
    )

static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(os.path.join(static_path, "index.html"))


@app.get("/chat", include_in_schema=False)
async def chat_ui():
    return FileResponse(os.path.join(static_path, "chat.html"))


@app.get("/colaborar", include_in_schema=False)
async def colaborar_ui():
    return FileResponse(os.path.join(static_path, "colaborar.html"))
