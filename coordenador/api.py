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
import httpx
from coordenador.pesquisa import consulta_automatica, ler_artigo, pedido_de_pesquisa, pesquisar, pesquisar_inteligente
from coordenador.piloto import router as piloto_router

log = structlog.get_logger()
import os, sys
sys.path.insert(0, '/app')

_modelo_ani = None
_tokenizer_ani = None

def carregar_modelo_ani():
    global _modelo_ani, _tokenizer_ani
    if _modelo_ani is not None:
        return _modelo_ani, _tokenizer_ani
    checkpoint = '/app/checkpoints/ani-v5'
    if not os.path.exists(checkpoint):
        return None, None
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        _tokenizer_ani = AutoTokenizer.from_pretrained(checkpoint)
        _tokenizer_ani.pad_token = _tokenizer_ani.eos_token
        _modelo_ani = AutoModelForCausalLM.from_pretrained(
            checkpoint,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map='auto'
        )
        _modelo_ani.eval()
        print('ANI-v5 carregada!')
        return _modelo_ani, _tokenizer_ani
    except Exception as e:
        print(f'Erro ao carregar ANI-v5: {e}')
        return None, None


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
    pesquisar_web: bool | None = None

class RespostaChat(BaseModel):
    content: str
    model: str    = "ani-v1"
    confianca: float
    tokens_usados: int
    custo: float  = 0.0
    fontes: list[dict[str, str]] = []


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
    pediu_pesquisa, assunto = pedido_de_pesquisa(ultima)
    if pediu_pesquisa and not assunto:
        return RespostaChat(
            content="Sim, posso pesquisar na Wikipédia em português e trazer links para as fontes. "
                    "Qual assunto você quer pesquisar? Por exemplo: “Pesquise sobre energia solar”.",
            confianca=0.0, tokens_usados=0,
        )
    consulta = None
    if req.pesquisar_web is True:
        consulta = consulta_automatica(ultima) or ultima.strip()
    elif req.pesquisar_web is None:
        consulta = consulta_automatica(ultima)
    if consulta is not None:
        if not 2 <= len(consulta) <= 240:
            raise HTTPException(422, "Use de 2 a 240 caracteres para pesquisar.")
        try:
            fontes = await pesquisar_inteligente(consulta)
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, "A Wikipédia está indisponível. Tente novamente.")
        texto = "Segundo a Wikipédia em português, " + fontes[0]["trecho"] if fontes else ""
        if not fontes:
            texto = "Não encontrei artigos para essa busca. Tente um termo mais específico."
        return RespostaChat(content=texto, fontes=fontes, confianca=0.0, tokens_usados=0)
    # Resposta inteligente sem pesquisa
    ultima_norm = ultima.lower().strip()

    if any(x in ultima_norm for x in ["quem e voce", "quem é você", "o que e a ani",
                                       "o que você faz", "o que voce faz"]):
        resposta = (
            "Sou a ANI — Aggilli Native Intelligence. 🌱\n\n"
            "Sou uma inteligência artificial livre e distribuída, "
            "criada pela Aggilli Intelligence e treinada pela humanidade "
            "via Federated Learning.\n\n"
            "Posso responder perguntas sobre qualquer assunto consultando "
            "a Wikipedia em português e inglês, sem custo por resposta.\n\n"
            "Experimente me perguntar: *O que é fotossíntese?* ou "
            "*O que é machine learning?*"
        )
    elif any(x in ultima_norm for x in ["ola", "oi", "bom dia", "boa tarde",
                                         "boa noite", "tudo bem", "como vai"]):
        resposta = (
            "Olá! Sou a ANI — IA livre da Aggilli. 🌱\n\n"
            "Posso pesquisar qualquer assunto para você na Wikipedia. "
            "O que você gostaria de saber hoje?"
        )
    else:
        resposta = (
            f"Sou a ANI — IA livre e distribuída da Aggilli. 🌱\n\n"
            f"Você perguntou: *{ultima[:100]}*\n\n"
            f"Para pesquisar um assunto específico, tente: "
            f"*O que é [tema]?* ou *Explique [tema]*"
        )

    return RespostaChat(
        content=resposta,
        model=_estado["versao"],
        confianca=0.95,
        tokens_usados=len(resposta.split()),
        custo=0.0,
    )

@app.get("/api/chat/fontes/{pageid}")
async def fonte_do_chat(pageid: int):
    if not 1 <= pageid <= 2_147_483_647:
        raise HTTPException(404, "Artigo não encontrado.")
    try:
        artigo = await ler_artigo(pageid)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "A Wikipédia está indisponível.")
    if artigo is None:
        raise HTTPException(404, "Artigo não encontrado.")
    return artigo


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
