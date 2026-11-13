self.onmessage = async ({ data: { pesos, exemplos } }) => {
  const novos = pesos.slice();
  const etapas = 48;
  for (let passo = 0; passo < etapas; passo++) {
    const [indices, classe] = exemplos[passo % exemplos.length];
    const logito = indices.reduce((total, i) => total + novos[i], 0);
    const erro = classe - 1 / (1 + Math.exp(-logito));
    for (const i of indices) novos[i] += 0.1 * erro;
    if ((passo + 1) % 4 === 0) {
      self.postMessage({ progresso: passo + 1, etapas });
      await new Promise(resolve => setTimeout(resolve, 50));
    }
  }
  self.postMessage({ delta: novos.map((valor, i) => valor - pesos[i]) });
};
