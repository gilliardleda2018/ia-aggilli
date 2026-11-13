"""Consulta enciclopédica em português para o chat da ANI."""

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
