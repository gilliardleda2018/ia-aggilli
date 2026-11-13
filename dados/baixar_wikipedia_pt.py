# ANI — Primeiro conhecimento: Wikipedia PT
# Usa API nova do HuggingFace (Parquet, sem script)

import sys, subprocess, json
from pathlib import Path

subprocess.run([sys.executable, "-m", "pip", "install",
                "datasets>=2.19.0", "-q"], check=True)

from datasets import load_dataset

print()
print("📚 ANI — Baixando Wikipedia em Português")
print("   Primeiro conhecimento da IA livre...")
print()

saida = Path("./dados_treino")
saida.mkdir(exist_ok=True)

print("🔄 Conectando ao HuggingFace...")

# API nova — sem trust_remote_code
ds = load_dataset(
    "wikimedia/wikipedia",
    "20231101.pt",
    split="train",
    streaming=True,   # streaming = não baixa tudo de uma vez
)

print("✅ Conectado! Processando artigos em streaming...")
print("   (Ctrl+C para parar quando quiser)")
print()

arquivo = saida / "wikipedia_pt.jsonl"
count   = 0
max_artigos = 50_000  # começa com 50k — suficiente para treino inicial

with open(arquivo, "w", encoding="utf-8") as f:
    for artigo in ds:
        texto  = artigo.get("text",  "")
        titulo = artigo.get("title", "")

        if len(texto) < 200:
            continue

        # Par 1: pergunta direta
        f.write(json.dumps({
            "prompt":     f"O que é {titulo}?",
            "completion": texto[:600],
        }, ensure_ascii=False) + "\n")

        # Par 2: resumo
        paragrafos = [p for p in texto.split("\n") if len(p) > 50][:2]
        if paragrafos:
            f.write(json.dumps({
                "prompt":     f"Explique {titulo}.",
                "completion": " ".join(paragrafos)[:600],
            }, ensure_ascii=False) + "\n")

        count += 1

        if count % 5_000 == 0:
            tamanho = arquivo.stat().st_size / 1024**2
            print(f"   ✅ {count:,} artigos | {tamanho:.1f} MB")

        if count >= max_artigos:
            break

print()
print(f"✅ {count:,} artigos convertidos!")
print(f"📄 {count*2:,} pares de treino gerados!")
print(f"📊 Tamanho: {arquivo.stat().st_size / 1024**2:.1f} MB")
print()
print("🌱 A ANI tem sua primeira fonte de conhecimento livre!")
