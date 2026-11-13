const form = document.getElementById("piloto");
const iniciar = document.getElementById("iniciar");
const parar = document.getElementById("parar");
const estado = document.getElementById("estado");
const resultado = document.getElementById("resultado");
let sessao;
const credencial = new URLSearchParams(location.hash.slice(1)).get("participar");
if (credencial) {
  history.replaceState(null, "", location.pathname + location.search);
} else {
  iniciar.disabled = true;
  estado.textContent = "Abra o link de participação que você recebeu para iniciar.";
}

async function api(rota, options) {
  const response = await fetch("/api/piloto/" + rota, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "O servidor recusou a solicitação.");
  return data;
}

function enviar(rota, dados, signal) {
  return api(rota, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
    signal,
  });
}

async function atualizarResultado() {
  try {
    const dados = await api("resultado");
    resultado.textContent = dados.rodadas
      ? `Rodada ${dados.rodadas}. Erro na avaliação: ${dados.perda_antes.toFixed(3)} antes e ${dados.perda_candidata.toFixed(3)} após o treino. ${dados.adotado ? "Modelo atualizado." : "Versão anterior mantida."}`
      : "A primeira rodada aguarda três contribuições.";
  } catch {
    resultado.textContent = "";
  }
}

function finalizar(atual, mensagem) {
  if (sessao !== atual) return;
  clearTimeout(atual.timeout);
  atual.worker?.terminate();
  atual.controller.abort();
  sessao = undefined;
  estado.textContent = mensagem;
  iniciar.disabled = false;
  parar.disabled = true;
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  if (sessao || !credencial) return;
  const atual = { controller: new AbortController() };
  sessao = atual;
  iniciar.disabled = true;
  parar.disabled = false;
  estado.textContent = "Solicitando lote…";
  atual.timeout = setTimeout(() => finalizar(atual, "O tempo da sessão terminou."), 300_000);
  try {
    const lote = await enviar("lote", { codigo: credencial }, atual.controller.signal);
    if (sessao !== atual) return;
    const worker = new Worker("/static/piloto-worker.js");
    atual.worker = worker;
    worker.onerror = () => finalizar(atual, "O navegador não conseguiu completar o treino.");
    worker.onmessage = async ({ data }) => {
      if (sessao !== atual) return;
      if (!data.delta) {
        estado.textContent = `Treinando no seu navegador: ${data.progresso} de ${data.etapas} passos.`;
        return;
      }
      worker.terminate();
      parar.disabled = true;
      estado.textContent = "Enviando a atualização…";
      try {
        const recibo = await enviar("entrega", { ticket: lote.ticket, delta: data.delta }, atual.controller.signal);
        finalizar(atual, `Contribuição recebida para a rodada ${recibo.rodada}.`);
        atualizarResultado();
      } catch (erro) {
        finalizar(atual, erro.message);
      }
    };
    worker.postMessage(lote);
  } catch (erro) {
    finalizar(atual, erro.message);
  }
});

parar.addEventListener("click", () => finalizar(sessao, "Contribuição interrompida."));
window.addEventListener("pagehide", () => {
  if (sessao) finalizar(sessao, "Contribuição interrompida.");
});
atualizarResultado();
