const TOKEN = 'aggilli';
let ocupado = false;
let historico = [];
const sessoes = [];
let sessaoAtual = null;
const boasVindas = document.getElementById('mensagens').innerHTML;
function renderizarSessoes() {
  const lista = document.getElementById('session-list');
  lista.replaceChildren();
  for (const sessao of sessoes) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'session-item' + (sessao.id === sessaoAtual ? ' active' : '');
    btn.textContent = sessao.titulo;
    btn.setAttribute('aria-current',sessao.id === sessaoAtual ? 'true' : 'false');
    btn.addEventListener('click',() => selecionarSessao(sessao.id));
    lista.appendChild(btn);
  }
}
function selecionarSessao(id) {
  if (ocupado) return;
  const sessao = sessoes.find(s => s.id === id);
  if (!sessao) return;
  sessaoAtual = id;
  historico = sessao.historico;
  document.getElementById('mensagens').innerHTML = boasVindas;
  for (const msg of historico) adicionarMensagem(msg.role === 'user' ? 'user' : 'ani',msg.content);
  document.getElementById('sugestoes').hidden = historico.length > 0;
  document.getElementById('conversation-title').textContent = sessao.titulo;
  renderizarSessoes();
}
function criarSessao(moverFoco = true) {
  if (ocupado) return;
  const id = String(Date.now())+'-'+Math.random().toString(36).slice(2,7);
  sessoes.unshift({id,titulo:'Nova conversa',historico:[]});
  selecionarSessao(id);
  if (moverFoco) document.getElementById('input').focus();
}
document.getElementById('new-chat').addEventListener('click', () => criarSessao());
const campo = document.getElementById('input');
campo.addEventListener('keydown', tecla);
campo.addEventListener('input', () => auto_resize(campo));
document.getElementById('composer').addEventListener('submit', evento => {
  evento.preventDefault();
  enviar();
});
criarSessao(false);

// Status
async function atualizarStatus() {
  const status = document.getElementById('service-status');
  let online = false;
  try {
    const resposta = await fetch('/status');
    online = resposta.ok;
  } catch {
    online = false;
  }
  const estado = online ? 'online' : 'offline';
  if (status.dataset.state !== estado) {
    status.dataset.state = estado;
    document.getElementById('status-badge').textContent = online ? 'Disponível' : 'Indisponível';
  }
}

atualizarStatus();
setInterval(atualizarStatus, 15000);

// Chat
async function enviar() {
  const input = document.getElementById('input');
  const texto = input.value.trim();
  if (!texto || ocupado) return;
  input.value = '';
  auto_resize(input);
  await perguntar(texto);
}

async function perguntar(texto) {
  if (ocupado || !texto.trim()) return;
  ocupado = true;
  document.getElementById('sugestoes').hidden = true;
  adicionarMensagem('user', texto);
  historico.push({role:'user',content:texto});
  const atual = sessoes.find(s => s.id === sessaoAtual);
  if (atual && atual.titulo === 'Nova conversa') {
    atual.titulo = texto.slice(0,45) + (texto.length > 45 ? '…' : '');
    document.getElementById('conversation-title').textContent = atual.titulo;
    renderizarSessoes();
  }
  document.getElementById('btn').disabled = true;
  const typingId = adicionarTyping();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(),60000);
  try {
    const r = await fetch('/v1/chat/completions', {
      method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+TOKEN},
      body:JSON.stringify({messages:historico,dominio:'geral'}),
      signal:controller.signal
    });
    if (!r.ok) throw new Error('HTTP '+r.status);
    const d = await r.json();
    const resposta = d.choices?.[0]?.message?.content ?? d.content ?? d.resposta ?? d.response;
    if (typeof resposta !== 'string' || !resposta.trim()) throw new Error('Resposta vazia');
    historico.push({role:'assistant',content:resposta});
    adicionarMensagem('ani',resposta);
  } catch(err) {
    historico.pop();
    adicionarMensagem('ani',err.name==='AbortError'?'A resposta demorou demais. Tente novamente.':'Falha ao responder ('+err.message+'). Tente novamente.');
  } finally {
    clearTimeout(timeout);
    removerTyping(typingId);
    ocupado = false;
    document.getElementById('btn').disabled = false;
  }
}

function adicionarMensagem(tipo, texto) {
  const cont = document.getElementById('mensagens');
  const div  = document.createElement('div');
  div.className = `msg ${tipo}`;

  const avatar = tipo === 'ani'
    ? `<div class="msg-avatar"><img src="/static/ani-avatar.png" alt="ANI"></div>`
    : `<div class="msg-avatar user" aria-hidden="true">Você</div>`;

  div.innerHTML = `
    ${avatar}
    <div class="msg-bubble">${esc(texto)}</div>
  `;
  cont.appendChild(div);
  cont.scrollTop = cont.scrollHeight;
}

function adicionarTyping() {
  const cont = document.getElementById('mensagens');
  const id   = 'typing-' + Date.now();
  const div  = document.createElement('div');
  div.className = 'msg ani';
  div.id = id;
  div.innerHTML = `
    <div class="msg-avatar"><img src="/static/ani-avatar.png" alt="ANI"></div>
    <div class="msg-bubble">
      <span class="typing-dots">ANI está respondendo…</span>
    </div>
  `;
  cont.appendChild(div);
  cont.scrollTop = cont.scrollHeight;
  return id;
}

function removerTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function esc(t) {
  return t
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/\n/g,'<br>');
}

function tecla(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    e.currentTarget.form.requestSubmit();
  }
}

function auto_resize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}
