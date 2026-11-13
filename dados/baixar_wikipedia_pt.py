import json, sys
from pathlib import Path

print()
print("📚 ANI — Baixando Wikipedia em Português")
print("   Primeiro conhecimento da IA livre...")
print()

from datasets import load_dataset

saida = Path("./dados_treino")
saida.mkdir(exist_ok=True)

print("🔄 Conectando ao HuggingFace...")
ds = load_dataset(
    "wikimedia/wikipedia",
    "20231101.pt",
    split="train",
    streaming=True,
)

print("✅ Conectado! Processando em streaming...")
print("   Ctrl+C para parar quando quiser")
print()

arquivo = saida / "wikipedia_pt.jsonl"
count   = 0
MAX     = 50_000

with open(arquivo, "w", encoding="utf-8") as f:
    for artigo in ds:
        texto  = artigo.get("text",  "")
        titulo = artigo.get("title", "")
        if len(texto) < 200:
            continue
        f.write(json.dumps({
            "prompt":     f"O que é {titulo}?",
            "completion": texto[:600],
        }, ensure_ascii=False) + "\n")
        paragrafos = [p for p in texto.split("\n") if len(p) > 50][:2]
        if paragrafos:
            f.write(json.dumps({
                "prompt":     f"Explique {titulo}.",
                "completion": " ".join(paragrafos)[:600],
            }, ensure_ascii=False) + "\n")
        count += 1
        if count % 5_000 == 0:
            mb = arquivo.stat().st_size / 1024**2
            print(f"   ✅ {count:,} artigos | {mb:.1f} MB")
        if count >= MAX:
            break

print()
print(f"✅ {count:,} artigos → {count*2:,} pares de treino")
print(f"📊 {arquivo.stat().st_size/1024**2:.1f} MB")
print()
print("🌱 ANI tem seu primeiro conhecimento livre!")
