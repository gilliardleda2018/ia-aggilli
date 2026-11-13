"""Piloto público de aprendizado federado com um classificador de temas."""
from contextlib import closing
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel, Field, FiniteFloat

router = APIRouter(prefix="/api/piloto")
DIM = 128
MINIMO = 3
# Exemplos escritos para o piloto. A avaliação fica separada dos lotes.
LOTES = (
    (("irrigação da lavoura na estação seca", "plantio de milho e soja"),
     ("ônibus no terminal urbano", "horários de trem e metrô")),
    (("colheita de milho na fazenda", "irrigação de horta e solo"),
     ("ônibus e metrô na cidade", "viagem de trem e transporte urbano")),
    (("plantio e colheita de soja", "lavoura com irrigação e adubo"),
     ("terminal de ônibus e passagens", "transporte urbano por trem")),
)
AVALIACAO = (
    ("plantio de soja na lavoura", 1), ("colheita de milho com irrigação", 1),
    ("transporte urbano de ônibus", 0), ("viagem de trem pelo terminal", 0),
)


def atributos(texto):
    indices = {
        int.from_bytes(sha256(palavra.encode()).digest()[:4], "big") % DIM
        for palavra in re.findall(r"[^\W\d_]+", texto.casefold())
    }
    return sorted(indices)


def perda(pesos):
    total = 0.0
    for texto, classe in AVALIACAO:
        logito = sum(pesos[i] for i in atributos(texto))
        total += math.log1p(math.exp(-logito if classe else logito))
    return total / len(AVALIACAO)


def banco():
    caminho = os.environ.get("ANI_PILOTO_DB")
    if not caminho:
        raise HTTPException(503, "Piloto ainda indisponível.")
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(caminho, timeout=5)
    db.execute("""CREATE TABLE IF NOT EXISTS modelo
               (versao INTEGER PRIMARY KEY, pesos TEXT, antes REAL, depois REAL, adotado INTEGER)""")
    db.execute("""CREATE TABLE IF NOT EXISTS lotes
               (versao INTEGER, convite TEXT, ticket TEXT UNIQUE, expira REAL, delta TEXT,
                PRIMARY KEY (versao, convite))""")
    db.execute("INSERT OR IGNORE INTO modelo VALUES (0, ?, NULL, NULL, NULL)", (json.dumps([0] * DIM),))
    db.commit()
    return db


class Entrega(BaseModel):
    ticket: str = Field(min_length=32, max_length=64)
    delta: list[FiniteFloat] = Field(min_length=DIM, max_length=DIM)


@router.post("/lote")
def reservar(resposta: Response, ani_participante: str | None = Cookie(default=None)):
    participante = ani_participante or ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", participante):
        participante = secrets.token_urlsafe(32)
    resposta.set_cookie("ani_participante", participante, max_age=86400 * 30,
                       httponly=True, secure=True, samesite="strict", path="/api/piloto")
    identificador = sha256(participante.encode()).hexdigest()
    with closing(banco()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        versao, pesos = db.execute("SELECT versao, pesos FROM modelo ORDER BY versao DESC LIMIT 1").fetchone()
        anterior = db.execute("SELECT delta FROM lotes WHERE versao=? AND convite=?", (versao, identificador)).fetchone()
        if anterior and anterior[0] is not None:
            raise HTTPException(409, "Sua contribuição já foi recebida nesta rodada.")
        agora = time.time()
        db.execute("DELETE FROM lotes WHERE delta IS NULL AND expira < ?", (agora,))
        ocupados = db.execute(
            "SELECT COUNT(*) FROM lotes WHERE versao=? AND convite<>?", (versao, identificador)
        ).fetchone()[0]
        ticket = secrets.token_urlsafe(32)
        db.execute("INSERT OR REPLACE INTO lotes VALUES (?, ?, ?, ?, NULL)",
                   (versao, identificador, ticket, agora + 300))
    lote = LOTES[ocupados % len(LOTES)]
    exemplos = [[atributos(texto), classe] for classe, textos in zip((1, 0), lote) for texto in textos]
    return {"ticket": ticket, "pesos": json.loads(pesos), "exemplos": exemplos}


@router.post("/entrega")
def entregar(dados: Entrega):
    if max(map(abs, dados.delta)) > 2 or not any(dados.delta):
        raise HTTPException(422, "Atualização fora dos limites do piloto.")
    with closing(banco()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        lote = db.execute("SELECT versao, expira, delta FROM lotes WHERE ticket=?", (dados.ticket,)).fetchone()
        if not lote:
            raise HTTPException(404, "Lote desconhecido.")
        versao, expira, anterior = lote
        atual, pesos = db.execute("SELECT versao, pesos FROM modelo ORDER BY versao DESC LIMIT 1").fetchone()
        if anterior is None:
            if versao != atual or time.time() > expira:
                raise HTTPException(409, "Lote expirado ou rodada encerrada. Inicie novamente.")
            db.execute("UPDATE lotes SET delta=? WHERE ticket=?", (json.dumps(dados.delta), dados.ticket))
            deltas = [json.loads(row[0]) for row in db.execute(
                "SELECT delta FROM lotes WHERE versao=? AND delta IS NOT NULL", (versao,))]
            if len(deltas) >= MINIMO:
                base = json.loads(pesos)
                candidato = [max(-4, min(4, peso + sum(coluna) / len(deltas)))
                             for peso, coluna in zip(base, zip(*deltas))]
                antes, depois = perda(base), perda(candidato)
                adotado = depois < antes
                db.execute("INSERT INTO modelo VALUES (?, ?, ?, ?, ?)",
                           (versao + 1, json.dumps(candidato if adotado else base), antes, depois, adotado))
    return {"rodada": versao + 1}


@router.get("/resultado")
def resultado():
    with closing(banco()) as db:
        versao, antes, depois, adotado = db.execute(
            "SELECT versao, antes, depois, adotado FROM modelo ORDER BY versao DESC LIMIT 1").fetchone()
        pendentes = db.execute(
            "SELECT COUNT(*) FROM lotes WHERE versao=? AND delta IS NOT NULL", (versao,)
        ).fetchone()[0]
    return {"rodadas": versao, "contribuicoes": pendentes, "meta": MINIMO, "perda_antes": antes, "perda_candidata": depois,
            "adotado": bool(adotado) if versao else None}
