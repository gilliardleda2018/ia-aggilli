import requests, json, time
from pathlib import Path
from datetime import datetime
import structlog

log = structlog.get_logger()


class BuscadorANI:

    TRADUCOES = {
        "federated learning": "aprendizado federado",
        "machine learning": "machine learning",
        "deep learning": "aprendizado profundo",
        "neural network": "rede neural",
        "reinforcement learning": "aprendizado por reforco",
    }

    def __init__(self, cache_path='./cache_busca'):
        self.cache = Path(cache_path)
        self.cache.mkdir(exist_ok=True)

    def _buscar_por_titulo(self, titulo, lang):
        try:
            url = 'https://{}.wikipedia.org/api/rest_v1/page/summary/{}'.format(
                lang, requests.utils.quote(titulo))
            r = requests.get(url, timeout=8, headers={'User-Agent': 'ANI/1.0'})
            if r.status_code == 200:
                d = r.json()
                resumo = d.get('extract', '')
                if len(resumo) > 50:
                    return {
                        'titulo': d.get('title', titulo),
                        'resumo': resumo[:800],
                        'url': d.get('content_urls', {}).get('desktop', {}).get('page', ''),
                        'fonte': 'wikipedia_{}'.format(lang),
                    }
        except Exception as e:
            log.warning('ani.busca.erro', erro=str(e))
        return {}

    def _opensearch(self, termo, lang):
        try:
            url = 'https://{}.wikipedia.org/w/api.php'.format(lang)
            r = requests.get(url, params={
                'action': 'opensearch', 'search': termo,
                'limit': 3, 'format': 'json',
            }, timeout=8, headers={'User-Agent': 'ANI/1.0'})
            if r.status_code == 200:
                d = r.json()
                return d[1] if d[1] else []
        except Exception:
            pass
        return []

    def buscar_wikipedia(self, termo, lang='pt'):
        result = self._buscar_por_titulo(termo, lang)
        if result:
            return result
        titulos = self._opensearch(termo, lang)
        for titulo in titulos[:2]:
            result = self._buscar_por_titulo(titulo, lang)
            if result:
                return result
            time.sleep(0.3)
        return {}

    def buscar_e_aprender(self, query):
        log.info('ani.busca.iniciando', query=query)
        contexto = []
        fontes   = []
        query_lower = query.lower().strip()
        query_pt = self.TRADUCOES.get(query_lower, query)
        for termo_pt in [query_pt, query]:
            wiki_pt = self.buscar_wikipedia(termo_pt, 'pt')
            if wiki_pt.get('resumo') and len(wiki_pt['resumo']) > 50:
                contexto.append('Wikipedia PT:\n' + wiki_pt['resumo'])
                fontes.append({'titulo': wiki_pt['titulo'],
                               'trecho': wiki_pt['resumo'][:300],
                               'url': wiki_pt['url']})
                log.info('ani.busca.pt.ok', titulo=wiki_pt['titulo'])
                break
        if not fontes:
            wiki_en = self.buscar_wikipedia(query, 'en')
            if wiki_en.get('resumo') and len(wiki_en['resumo']) > 50:
                contexto.append('Wikipedia EN:\n' + wiki_en['resumo'])
                fontes.append({'titulo': wiki_en['titulo'],
                               'trecho': wiki_en['resumo'][:300],
                               'url': wiki_en['url']})
                log.info('ani.busca.en.ok', titulo=wiki_en['titulo'])
        if contexto:
            self._salvar(query, contexto)
        result = {'query': query,
                  'contexto': '\n\n'.join(contexto),
                  'fontes': fontes}
        log.info('ani.busca.concluida', query=query, chars=len(result['contexto']))
        return result

    def _salvar(self, query, contexto):
        try:
            arquivo = Path('./dados_treino/aprendizado_web.jsonl')
            arquivo.parent.mkdir(exist_ok=True)
            with open(arquivo, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'prompt': query,
                    'completion': '\n'.join(contexto)[:600],
                    'fonte': 'wikipedia',
                }, ensure_ascii=False) + '\n')
        except Exception as e:
            log.warning('ani.busca.salvar.erro', erro=str(e))
