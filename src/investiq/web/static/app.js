/* The browser presents the conversation; all interpretation and finance stay in Python. */
"use strict";

const $ = (selector) => document.querySelector(selector);
const elements = {
  sidebar: $("#sidebar"), backdrop: $("#sidebar-backdrop"), openSidebar: $("#open-sidebar"),
  closeSidebar: $("#close-sidebar"), main: $("#main"), list: $("#instrument-list"),
  search: $("#symbol-search"), noInstruments: $("#no-instruments"), count: $("#instrument-count"),
  welcome: $("#welcome"), messages: $("#messages"), scroll: $("#conversation-scroll"),
  loading: $("#loading-message"), input: $("#message-input"), send: $("#send-message"),
  form: $("#chat-form"), error: $("#app-error"), errorText: $("#error-text"),
  retry: $("#retry-action"), dismissError: $("#dismiss-error"),
  memoryEnabled: $("#memory-enabled"), memorySummary: $("#memory-summary"),
  forgetMemory: $("#forget-memory"), newChat: $("#new-conversation"), mobileNewChat: $("#mobile-new-conversation"),
  modeText: $("#mode-text"),
};
const mobile = window.matchMedia("(max-width: 820px)");
const state = {ready: false, busy: false, instruments: [], memory: {enabled: false, summary: ""}, retry: null, sidebarReturnFocus: null};
const DISCLAIMER = "No es asesoría financiera.";
const STARTERS = {
  news: {prompt: "¿Cuáles son las últimas noticias del mercado hoy?"},
  recommendations: {action: "recommendations"},
  nasdaq: {prompt: "¿Qué sectores lideran hoy en NASDAQ?"},
  sp500: {prompt: "¿Cómo van los sectores de las empresas del S&P 500 en la última sesión disponible?"},
  metrics: {prefill: "Dame las métricas de la acción o ETF: "},
};

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("icon");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#icon-${name}`);
  svg.append(use);
  return svg;
}

function normalize(text) {
  return String(text).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

async function request(path, body) {
  let response;
  try {
    response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      headers: body === undefined ? {Accept: "application/json"} : {"Content-Type": "application/json", Accept: "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(65000),
    });
  } catch (error) {
    if (error.name === "TimeoutError" || error.name === "AbortError") {
      throw new Error("La consulta está tardando más de lo esperado. Puedes volver a intentarlo.");
    }
    throw new Error("No puedo comunicarme con la app. Comprueba que el servidor siga abierto y vuelve a intentarlo.");
  }
  let data;
  try { data = await response.json(); } catch {
    throw new Error("La app devolvió una respuesta que no pude leer. Vuelve a intentarlo.");
  }
  if (!response.ok) throw new Error(typeof data.error === "string" ? data.error : "No pude completar la acción. Vuelve a intentarlo.");
  return data;
}

function showError(message, retryAction = null, retryLabel = "Reintentar") {
  state.retry = retryAction;
  elements.errorText.textContent = message;
  elements.retry.textContent = retryLabel;
  elements.retry.hidden = !retryAction;
  elements.error.hidden = false;
}

function hideError() {
  elements.error.hidden = true;
  state.retry = null;
}

function syncControls() {
  elements.send.disabled = !state.ready || state.busy || !elements.input.value.trim();
  elements.input.disabled = !state.ready;
  for (const button of document.querySelectorAll('.branch-action, .response-action')) button.disabled = !state.ready || state.busy;
  elements.newChat.disabled = elements.mobileNewChat.disabled = !state.ready || state.busy;
  elements.memoryEnabled.disabled = elements.forgetMemory.disabled = !state.ready || state.busy;
  for (const button of document.querySelectorAll(".instrument-button, .suggestion")) button.disabled = !state.ready || state.busy;
  elements.form.setAttribute("aria-busy", String(state.busy));
}

function resizeInput() {
  elements.input.style.height = "auto";
  elements.input.style.height = `${Math.min(elements.input.scrollHeight, 142)}px`;
}

function scrollToEnd() {
  elements.scroll.scrollTop = elements.scroll.scrollHeight;
}

function updateMemory(memory) {
  if (!memory) return;
  state.memory = {enabled: Boolean(memory.enabled), summary: typeof memory.summary === "string" ? memory.summary : ""};
  elements.memoryEnabled.checked = state.memory.enabled;
  elements.memorySummary.textContent = state.memory.summary || (state.memory.enabled ? "Todavía no hay contexto guardado. Lo iremos construyendo al conversar." : "El recuerdo del contexto está desactivado.");
}

function renderCatalogue() {
  const term = normalize(elements.search.value.trim());
  const matching = state.instruments.filter((item) => normalize(`${item.symbol} ${item.name}`).includes(term));
  elements.list.replaceChildren();
  elements.count.textContent = String(matching.length);
  elements.noInstruments.hidden = matching.length !== 0;
  for (const instrument of matching) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "instrument-button";
    button.dataset.symbol = instrument.symbol;
    button.setAttribute("aria-label", `Conocer ${instrument.symbol}, ${instrument.name}`);
    button.title = `${instrument.symbol} · ${instrument.name}`;
    const symbol = document.createElement("span");
    symbol.className = "instrument-symbol";
    symbol.textContent = instrument.symbol;
    const name = document.createElement("span");
    name.className = "instrument-name";
    name.textContent = instrument.name;
    button.append(symbol, name, icon("chevron"));
    button.addEventListener("click", () => {
      closeSidebar(false);
      sendMessage(`¿Qué es ${instrument.symbol}?`);
    });
    elements.list.append(button);
  }
  syncControls();
}

function safeLink(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch { return null; }
}

/* Small text-only Markdown renderer. Never insert model or user strings as HTML. */
function appendInline(parent, text) {
  const pattern = /(\*\*([^*\n]+)\*\*|`([^`\n]+)`|\[([^\]\n]+)\]\(([^)\s]+)\))/g;
  let cursor = 0;
  for (const match of text.matchAll(pattern)) {
    parent.append(document.createTextNode(text.slice(cursor, match.index)));
    if (match[2]) {
      const strong = document.createElement("strong"); strong.textContent = match[2]; parent.append(strong);
    } else if (match[3]) {
      const code = document.createElement("code"); code.textContent = match[3]; parent.append(code);
    } else {
      const href = safeLink(match[5]);
      if (href) {
        const link = document.createElement("a"); link.href = href; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = match[4]; parent.append(link);
      } else { parent.append(document.createTextNode(match[4])); }
    }
    cursor = match.index + match[0].length;
  }
  parent.append(document.createTextNode(text.slice(cursor)));
}

function renderMarkdown(parent, content) {
  const lines = content.replaceAll("\r\n", "\n").split("\n");
  let index = 0;
  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) { index++; continue; }
    if (line.includes("|") && index + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[index + 1])) {
      const wrap = document.createElement("div"); wrap.className = "table-wrap"; wrap.tabIndex = 0; wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", "Tabla de resultados, desplazable horizontalmente");
      const table = document.createElement("table");
      const rows = [];
      rows.push(lines[index]); index += 2;
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) rows.push(lines[index++]);
      rows.forEach((row, rowIndex) => {
        const tr = document.createElement("tr");
        const cells = row.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|");
        for (const cell of cells) {
          const td = document.createElement(rowIndex === 0 ? "th" : "td");
          if (rowIndex === 0) td.scope = "col";
          appendInline(td, cell.trim()); tr.append(td);
        }
        table.append(tr);
      });
      wrap.append(table); parent.append(wrap); continue;
    }
    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      const node = document.createElement(`h${Math.min(heading[1].length + 1, 4)}`); appendInline(node, heading[2]); parent.append(node); index++; continue;
    }
    if (/^[-*]\s+/.test(line) || /^\d+[.)]\s+/.test(line)) {
      const ordered = /^\d/.test(line);
      const list = document.createElement(ordered ? "ol" : "ul");
      const marker = ordered ? /^\d+[.)]\s+/ : /^[-*]\s+/;
      while (index < lines.length && marker.test(lines[index].trim())) {
        const li = document.createElement("li"); appendInline(li, lines[index].trim().replace(marker, "")); list.append(li); index++;
      }
      parent.append(list); continue;
    }
    const paragraph = document.createElement("p");
    appendInline(paragraph, line);
    index++;
    while (index < lines.length && lines[index].trim() && !/^(?:#{1,4}\s|[-*]\s|\d+[.)]\s)/.test(lines[index].trim()) && !(lines[index].includes("|") && index + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[index + 1]))) {
      paragraph.append(document.createElement("br")); appendInline(paragraph, lines[index].trim()); index++;
    }
    parent.append(paragraph);
  }
}

function appendSources(article, sources) {
  if (!Array.isArray(sources) || sources.length === 0) return;
  const details = document.createElement("details"); details.className = "response-sources";
  const summary = document.createElement("summary"); summary.textContent = `Ver ${sources.length === 1 ? "fuente" : `fuentes (${sources.length})`}`;
  const list = document.createElement("ul"); list.className = "source-list";
  for (const source of sources) {
    const li = document.createElement("li");
    const href = safeLink(source.url);
    const node = document.createElement(href ? "a" : "span");
    node.className = href ? "source-link" : "local-source";
    const label = document.createElement("span");
    label.textContent = source.title || source.provider || "Fuente consultada";
    if (!href && typeof source.url === "string" && source.url.startsWith("local://")) {
      label.textContent += source.url.startsWith("local://glossary") ? " · glosario local" : source.url.startsWith("local://catalogue") ? " · catálogo local" : " · fuente local";
    }
    node.append(label);
    if (href) { node.href = href; node.target = "_blank"; node.rel = "noopener noreferrer"; node.append(icon("external")); }
    if (source.delayed) node.title = "Fuente con datos retrasados";
    li.append(node); list.append(li);
  }
  details.append(summary, list); article.append(details);
}

function renderMessage(message) {
  const isUser = message.role === "user";
  const article = document.createElement("article"); article.className = `message ${isUser ? "user" : "assistant"}`;
  if (isUser) {
    article.setAttribute("aria-label", "Tu mensaje");
    const text = document.createElement("div"); text.className = "user-content"; text.textContent = message.content || ""; article.append(text);
  } else {
    article.setAttribute("aria-label", "Respuesta de InvestiQ");
    const label = document.createElement("p"); label.className = "assistant-label";
    const avatar = document.createElement("span"); avatar.className = "mentor-avatar"; avatar.append(icon("mentor"));
    label.append(avatar, document.createTextNode("InvestiQ · tu profesor")); article.append(label);
    const content = document.createElement("div"); content.className = "answer-content";
    const body = String(message.content || message.answer || "").replace(/\*{0,2}No es asesoría financiera\.\*{0,2}/gi, "").trim();
    renderMarkdown(content, body); article.append(content); appendSources(article, message.sources);
    if (Array.isArray(message.actions) && message.actions.length) {
      const actions = document.createElement('div'); actions.className = 'response-actions';
      for (const action of message.actions.slice(0, 10)) {
        if (typeof action.label !== 'string' || typeof action.prompt !== 'string') continue;
        const button = document.createElement('button'); button.type = 'button'; button.className = 'response-action';
        button.textContent = action.label; button.addEventListener('click', () => sendMessage(action.prompt, null, action.news_id));
        actions.append(button);
      }
      article.append(actions);
    }
    const disclaimer = document.createElement("p"); disclaimer.className = "response-footnote"; disclaimer.textContent = DISCLAIMER; article.append(disclaimer);
  }
  elements.messages.append(article);
  elements.messages.hidden = false;
  elements.welcome.hidden = true;
  return article;
}

function clearMessages() {
  elements.messages.replaceChildren(); elements.messages.hidden = true; elements.welcome.hidden = false;
  elements.scroll.scrollTop = 0;
}

function prefillMessage(prompt) {
  if (!state.ready || state.busy) return;
  elements.input.value = prompt;
  resizeInput(); syncControls(); elements.input.focus();
}

async function sendMessage(rawMessage, existingUser = null, newsId = null) {
  const message = rawMessage.trim();
  if (!state.ready || state.busy || !message) return;
  if (message.length > 2000) { showError("La pregunta puede tener hasta 2000 caracteres. Acórtala un poco para enviarla."); return; }
  hideError(); state.busy = true; syncControls();
  const userNode = existingUser && existingUser.isConnected ? existingUser : renderMessage({role: "user", content: message});
  elements.input.value = ""; resizeInput(); elements.loading.hidden = false; scrollToEnd();
  try {
    const data = await request("/api/chat", {message, ...(newsId ? {news_id: newsId} : {})});
    if (!data.response || typeof data.response.answer !== "string") throw new Error("No pude leer la respuesta del agente. Vuelve a intentarlo.");
    if (data.response.clear_history) clearMessages();
    renderMessage({role: "assistant", content: data.response.answer, sources: data.response.sources, actions: data.response.actions, status: data.response.status});
    updateMemory(data.memory);
  } catch (error) {
    showError(error.message, () => sendMessage(message, userNode, newsId));
  } finally {
    state.busy = false; elements.loading.hidden = true; syncControls(); scrollToEnd();
    if (!mobile.matches) elements.input.focus();
  }
}

async function startRecommendations() {
  if (!state.ready || state.busy) return;
  hideError(); state.busy = true; syncControls(); elements.loading.hidden = false; scrollToEnd();
  try {
    const data = await request("/api/chat", {action: "start_recommendations"});
    if (!data.response || typeof data.response.answer !== "string") throw new Error("No pude iniciar la recomendación guiada. Vuelve a intentarlo.");
    renderMessage({role: "assistant", content: data.response.answer, sources: data.response.sources, actions: data.response.actions, status: data.response.status});
    updateMemory(data.memory);
  } catch (error) {
    showError(error.message, startRecommendations);
  } finally {
    state.busy = false; elements.loading.hidden = true; syncControls(); scrollToEnd();
    if (!mobile.matches) elements.input.focus();
  }
}

async function resetConversation(starter = null) {
  if (!state.ready || state.busy) return;
  hideError(); state.busy = true; syncControls();
  try {
    const data = await request("/api/session/reset", {});
    clearMessages(); updateMemory(data.memory); elements.input.value = ""; resizeInput(); closeSidebar(false);
  } catch (error) { showError(error.message, () => resetConversation(starter)); return; }
  finally { state.busy = false; syncControls(); }
  if (starter?.prefill) prefillMessage(starter.prefill);
  else if (starter?.action === "recommendations") startRecommendations();
  else if (starter?.prompt) sendMessage(starter.prompt);
  else elements.input.focus();
}

async function updateMemorySetting(body) {
  if (!state.ready || state.busy) return;
  const previous = state.memory.enabled;
  hideError(); state.busy = true; syncControls();
  try {
    const data = await request("/api/memory", body); updateMemory(data.memory);
    if (body.forget) clearMessages();
  } catch (error) {
    elements.memoryEnabled.checked = previous; showError(error.message, () => updateMemorySetting(body));
  } finally { state.busy = false; syncControls(); }
}

function mobileSidebarState() {
  const open = elements.sidebar.classList.contains("open");
  elements.sidebar.inert = mobile.matches && !open;
  elements.sidebar.setAttribute("aria-hidden", String(mobile.matches && !open));
  if (!mobile.matches) {
    elements.backdrop.hidden = true; elements.main.inert = false;
    elements.sidebar.removeAttribute("role"); elements.sidebar.removeAttribute("aria-modal");
  }
}

function openSidebar() {
  if (!mobile.matches) return;
  state.sidebarReturnFocus = document.activeElement;
  elements.sidebar.classList.add("open"); elements.sidebar.inert = false;
  elements.sidebar.setAttribute("aria-hidden", "false"); elements.sidebar.setAttribute("role", "dialog"); elements.sidebar.setAttribute("aria-modal", "true");
  elements.backdrop.hidden = false; elements.openSidebar.setAttribute("aria-expanded", "true"); elements.main.inert = true; elements.closeSidebar.focus();
}

function closeSidebar(restoreFocus = true) {
  elements.sidebar.classList.remove("open"); elements.backdrop.hidden = true;
  elements.openSidebar.setAttribute("aria-expanded", "false"); elements.main.inert = false;
  elements.sidebar.removeAttribute("role"); elements.sidebar.removeAttribute("aria-modal");
  mobileSidebarState();
  if (restoreFocus && state.sidebarReturnFocus) state.sidebarReturnFocus.focus();
}

async function bootstrap() {
  hideError(); state.ready = false; syncControls();
  try {
    const data = await request("/api/bootstrap");
    state.instruments = Array.isArray(data.instruments) ? data.instruments : [];
    updateMemory(data.memory); clearMessages();
    for (const message of data.messages || []) renderMessage(message);
    elements.modeText.textContent = data.mode === "configured" ? "Modelo configurado" : "Respuestas locales";
    elements.modeText.parentElement.title = data.mode === "configured" ? "Hay un modelo configurado. Su disponibilidad se comprueba al responder." : "Puedes aprender y explorar el catálogo sin conectar un modelo. Los datos de mercado requieren sus fuentes.";
    state.ready = true; renderCatalogue(); syncControls();
    if (data.messages?.length) scrollToEnd();
    else elements.scroll.scrollTop = 0;
  } catch (error) {
    elements.modeText.textContent = "App sin conexión";
    showError(error.message, bootstrap, "Reconectar");
  }
}

elements.form.addEventListener("submit", (event) => { event.preventDefault(); sendMessage(elements.input.value); });
elements.input.addEventListener("input", () => { resizeInput(); syncControls(); });
elements.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); sendMessage(elements.input.value); }
});
elements.search.addEventListener("input", renderCatalogue);
elements.newChat.addEventListener("click", () => resetConversation());
elements.mobileNewChat.addEventListener("click", () => resetConversation());
elements.openSidebar.addEventListener("click", openSidebar);
elements.closeSidebar.addEventListener("click", () => closeSidebar());
elements.backdrop.addEventListener("click", () => closeSidebar());
elements.memoryEnabled.addEventListener("change", () => updateMemorySetting({enabled: elements.memoryEnabled.checked}));
elements.forgetMemory.addEventListener("click", () => updateMemorySetting({forget: true}));
elements.retry.addEventListener("click", () => { const action = state.retry; if (action) action(); });
elements.dismissError.addEventListener("click", hideError);
for (const button of document.querySelectorAll(".suggestion, .branch-action")) {
  button.addEventListener("click", () => resetConversation(STARTERS[button.dataset.starter]));
}
mobile.addEventListener("change", () => { closeSidebar(false); });
document.addEventListener("keydown", (event) => {
  if (!mobile.matches || !elements.sidebar.classList.contains("open")) return;
  if (event.key === "Escape") { event.preventDefault(); closeSidebar(); return; }
  if (event.key !== "Tab") return;
  const focusable = [...elements.sidebar.querySelectorAll("button:not(:disabled), a[href], input:not(:disabled), summary")].filter((node) => node.getClientRects().length);
  const first = focusable[0], last = focusable.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
});
mobileSidebarState();
bootstrap();
