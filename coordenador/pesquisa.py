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


def consulta_automatica(texto: str) -> str | None:
    texto = " ".join(texto.split())
    normalizado = "".join(c for c in unicodedata.normalize("NFD", texto.casefold())
                          if not unicodedata.combining(c))
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
