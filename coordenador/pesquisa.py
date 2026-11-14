"""Consulta enciclopédica em português para o chat da ANI."""

import re
import unicodedata

import httpx

ORIGEM = "https://pt.wikipedia.org"


async def pesquisar(consulta: str) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=6, follow_redirects=False) as cliente:
        resposta = await cliente.get(
            f"{ORIGEM}/w/api.php",
            headers={"User-Agent": "ANI/1.0 (https://ani.aggillintelligence.com.br/)"},
            params={
                "action": "query", "format": "json", "formatversion": 2,
                "generator": "search", "gsrsearch": consulta, "gsrlimit": 3,
                "gsrnamespace": 0, "prop": "extracts", "exintro": 1,
                "explaintext": 1, "exchars": 420, "exlimit": 3,
            },
        )
        resposta.raise_for_status()
        dados = resposta.json()
        if "error" in dados:
            raise ValueError("Consulta recusada pela Wikipédia")
    paginas = sorted(dados.get("query", {}).get("pages", []), key=lambda p: p["index"])
    return [
        {"titulo": pagina["title"], "trecho": pagina["extract"].strip(),
         "url": f"{ORIGEM}/?curid={int(pagina['pageid'])}"}
        for pagina in paginas if pagina.get("extract", "").strip()
    ]


def normalizar(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if not unicodedata.combining(c))


PEDIDO = re.compile(
    r"^(?:(?:voce (?:consegue|pode|sabe) |(?:consegue|pode|sabe) )?"
    r"(?:pesquis(?:e|ar|a|er)|busqu(?:e|ar)|busca|procur(?:e|ar|a)))\b"
)
CANAL = r"(?:na (?:web|internet|wikipedia)|online)"
SAUDACAO = re.compile(r"^(?:oi|ola|bom dia|boa tarde|boa noite)[,!]\s*")


def pedido_de_pesquisa(texto: str) -> tuple[bool, str]:
    texto = " ".join(texto.split())
    saudacao = SAUDACAO.match(normalizar(texto))
    if saudacao:
        texto = texto[saudacao.end():]
    pedido = PEDIDO.match(normalizar(texto))
    if not pedido:
        return False, texto
    assunto = texto[pedido.end():].strip(" ?!.:,")
    normalizado = normalizar(assunto)
    tema = re.search(r"\bsobre\s+|[:]", normalizado)
    if tema:
        return True, assunto[tema.end():].strip(" ?!.:,")
    generico = re.fullmatch(
        rf"(?:coi(?:sas?|ss)|algo|informacoes)?\s*(?:{CANAL})?", normalizado
    )
    if generico:
        return True, ""
    canal = re.match(rf"^{CANAL}\s+", normalizado)
    return True, assunto[canal.end():].strip(" ?!.:,") if canal else assunto


# ORIGINAL SUBSTITUIDO
def _consulta_automatica_original(texto: str) -> str | None:
    explicito, texto = pedido_de_pesquisa(texto)
    if explicito:
        return texto if 2 <= len(texto) <= 240 else None
    normalizado = normalizar(texto)
    palavras = re.findall(r"[a-z0-9]+", normalizado)
    if not palavras or len(texto) > 240:
        return None
    if " ".join(palavras) in {"oi", "ola", "bom dia", "boa tarde", "boa noite",
                              "obrigado", "obrigada", "tudo bem"}:
        return None
    if re.search(r"\b(ani|aggilli|voce|seu treino)\b", normalizado) and not re.match(
        r"^(pesquise|busque|procure)\b", normalizado
    ):
        return None
    prefixo = re.match(
        r"^(?:(?:pesquise|busque|procure)(?: na web)?(?: sobre)?|"
        r"(?:explique|fale)(?: sobre)?|o que (?:e|sao)|qual (?:e|a|o)|"
        r"quem (?:foi|e)|como funciona)\s+", normalizado,
    )
    consulta = texto[prefixo.end():] if prefixo else texto
    consulta = consulta.strip(" ?!.:,")
    return consulta if len(consulta) >= 2 else None

async def ler_artigo(pageid: int) -> dict[str, str] | None:
    async with httpx.AsyncClient(timeout=6, follow_redirects=False) as cliente:
        resposta = await cliente.get(
            f"{ORIGEM}/w/api.php",
            headers={"User-Agent": "ANI/1.0 (https://ani.aggillintelligence.com.br/)"},
            params={
                "action": "query", "format": "json", "formatversion": 2,
                "pageids": pageid, "prop": "extracts", "explaintext": 1,
            },
        )
        resposta.raise_for_status()
        dados = resposta.json()
        if "error" in dados:
            raise ValueError("Consulta recusada pela Wikipédia")
    for pagina in dados.get("query", {}).get("pages", []):
        texto = pagina.get("extract", "").strip()
        if pagina.get("ns") == 0 and texto:
            return {"texto": texto}
    return None


def consulta_automatica(texto: str) -> str | None:
    explicito, assunto = pedido_de_pesquisa(texto)
    if explicito:
        return assunto if 2 <= len(assunto) <= 240 else None
    normalizado = normalizar(texto)
    # Nao pesquisa saudacoes simples
    if normalizado.strip() in {'oi', 'ola', 'bom dia', 'boa tarde', 'boa noite',
                                'obrigado', 'obrigada', 'tudo bem', 'ok', 'sim', 'nao'}:
        return None
    # Nao pesquisa frases muito curtas
    if len(texto.strip()) < 5:
        return None
    # Remove prefixos de pergunta
    prefixo = re.match(
        r'^(?:(?:pesquise|busque|procure)(?: na web)?(?: sobre)?|'
        r'(?:explique|fale)(?: sobre)?|o que (?:e|sao|eh)|qual (?:e|a|o)|'
        r'quem (?:foi|e)|como funciona|me fale sobre|me explique)\s+',
        normalizado,
    )
    consulta = texto[prefixo.end():] if prefixo else texto
    consulta = consulta.strip(' ?!.:,')
    return consulta if 2 <= len(consulta) <= 240 else None


async def pesquisar_en(consulta: str) -> list[dict[str, str]]:
    """Busca na Wikipedia EN como fallback."""
    origem_en = "https://en.wikipedia.org"
    async with httpx.AsyncClient(timeout=6, follow_redirects=False) as cliente:
        resposta = await cliente.get(
            f"{origem_en}/w/api.php",
            headers={"User-Agent": "ANI/1.0 (https://ani.aggillintelligence.com.br/)"},
            params={
                "action": "query", "format": "json", "formatversion": 2,
                "generator": "search", "gsrsearch": consulta, "gsrlimit": 3,
                "gsrnamespace": 0, "prop": "extracts", "exintro": 1,
                "explaintext": 1, "exchars": 420, "exlimit": 3,
            },
        )
        resposta.raise_for_status()
        dados = resposta.json()
    paginas = sorted(dados.get("query", {}).get("pages", []), key=lambda p: p["index"])
    return [
        {"titulo": pagina["title"], "trecho": pagina["extract"].strip(),
         "url": f"{origem_en}/?curid={int(pagina['pageid'])}"}
        for pagina in paginas if pagina.get("extract", "").strip()
    ]


TERMOS_SEM_PT_REDIRECT = {
    'fotossintese':          'fotossíntese',
    'gravitacao universal':  'gravitação universal',
    'gravitacao':            'gravitação',
    'eletromagnetismo':      'electromagnetismo',
    'termodinamica':         'termodinâmica',
    'mecanica quantica':     'mecânica quântica',
}

TERMOS_SEM_PT_REDIRECT = {
    'fotossintese':          'fotossíntese',
    'gravitacao universal':  'gravitação universal',
    'gravitacao':            'gravitação',
    'eletromagnetismo':      'electromagnetismo',
    'termodinamica':         'termodinâmica',
    'mecanica quantica':     'mecânica quântica',
}

TERMOS_SEM_PT = {
    "federated learning", "machine learning", "deep learning",
    "reinforcement learning", "backpropagation", "transformer model",
    "gradient descent", "neural network", "large language model",
    "kubernetes", "docker swarm", "microservices",
}


async def pesquisar_inteligente(consulta: str) -> list[dict[str, str]]:
    """Busca PT primeiro, EN como fallback para termos tecnicos."""
    consulta_lower = consulta.lower().strip()
    
    # Redireciona termos sem acento para versao com acento
    if consulta_lower in TERMOS_SEM_PT_REDIRECT:
        consulta = TERMOS_SEM_PT_REDIRECT[consulta_lower]
        consulta_lower = consulta.lower()

    # Redireciona termos sem acento para versao com acento
    if consulta_lower in TERMOS_SEM_PT_REDIRECT:
        consulta = TERMOS_SEM_PT_REDIRECT[consulta_lower]
        consulta_lower = consulta.lower()

    # Termos tecnicos — vai direto para EN
    if consulta_lower in TERMOS_SEM_PT:
        return await pesquisar_en(consulta)
    
    # Tenta PT primeiro
    resultados_pt = await pesquisar(consulta)
    
    # Verifica se PT retornou algo relevante
    # (nao apenas resultados com "federal" ou palavras aleatórias)
    if resultados_pt:
        primeiro = resultados_pt[0]
        titulo_lower = primeiro["titulo"].lower()
        consulta_palavras = set(consulta_lower.split())
        titulo_palavras   = set(titulo_lower.split())
        
        # Se nenhuma palavra da consulta aparece no titulo → resultado irrelevante
        if not consulta_palavras & titulo_palavras:
            # Tenta EN
            resultados_en = await pesquisar_en(consulta)
            if resultados_en:
                return resultados_en
    
    return resultados_pt
