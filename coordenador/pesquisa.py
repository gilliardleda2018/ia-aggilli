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


def consulta_automatica(texto: str) -> str | None:
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
