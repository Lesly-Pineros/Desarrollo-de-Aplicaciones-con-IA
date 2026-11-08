#!/usr/bin/env node
/* Optional browser acceptance check. Node >=22 + Chrome; no npm packages.
 * Starts its own Python server, empty SQLite and isolated Chrome profile.
 * Provider credentials are cleared even if the checkout has an .env file.
 */
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import fs from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import {fileURLToPath} from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontOnly = process.argv.includes("--front-only");
const out = path.join(root, ".impeccable", "review");
const scratch = await fs.mkdtemp(path.join(os.tmpdir(), "investiq-web-"));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const checks = [];
const snapshots = [];
const errors = [];
let app, chrome, socket;
let processError;

async function freePort() {
  const probe = net.createServer();
  await new Promise((resolve, reject) => {probe.once("error", reject); probe.listen(0, "127.0.0.1", resolve);});
  const port = probe.address().port;
  await new Promise((resolve) => probe.close(resolve));
  return port;
}

async function poll(check, description, timeout = 12000) {
  const until = Date.now() + timeout;
  while (Date.now() < until) {
    if (processError) throw processError;
    try {if (await check()) return;} catch (error) {if (error.name === "AssertionError") throw error;}
    await sleep(100);
  }
  throw new Error(`Timeout: ${description}`);
}

const pending = new Map();
let serial = 0;
function cdp(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++serial;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error(`CDP timeout: ${method}`));}, 12000);
    pending.set(id, {resolve, reject, timer});
    socket.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const result = await cdp("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}
async function waitFor(expression, description) {await poll(() => evaluate(expression), description);}
async function click(selector) {
  // Dispatch through Chrome's input pipeline, including focus and pointer handling.
  const box = await evaluate(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); e.scrollIntoView({block:'nearest'}); const r=e.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()`);
  await cdp("Input.dispatchMouseEvent", {type: "mousePressed", ...box, button: "left", clickCount: 1});
  await cdp("Input.dispatchMouseEvent", {type: "mouseReleased", ...box, button: "left", clickCount: 1});
}
async function key(key, code, modifiers = 0) {
  const keyCode = {Enter: 13, Escape: 27, Tab: 9}[key] || 0;
  await cdp("Input.dispatchKeyEvent", {type: "keyDown", key, code, modifiers, windowsVirtualKeyCode: keyCode, ...(key === "Enter" ? {text: "\r"} : {})});
  await cdp("Input.dispatchKeyEvent", {type: "keyUp", key, code, modifiers, windowsVirtualKeyCode: keyCode});
}
async function type(selector, value) {
  await evaluate(`(() => {const e=document.querySelector(${JSON.stringify(selector)});e.focus();e.value='';e.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  await cdp("Input.insertText", {text: value});
}
async function expect(expression, description) {
  assert.equal(await evaluate(expression), true, description);
  checks.push(description);
}
async function viewport(width, height) {
  await cdp("Emulation.setDeviceMetricsOverride", {width, height, deviceScaleFactor: 1, mobile: width < 600});
  await sleep(240);
}
async function screenshot(name) {
  await evaluate("document.fonts.ready.then(() => true)");
  const {data} = await cdp("Page.captureScreenshot", {format: "png", captureBeyondViewport: false});
  const filename = path.join(out, `${name}.png`);
  await fs.writeFile(filename, Buffer.from(data, "base64"));
  snapshots.push(filename);
}
async function send(text) {
  const count = await evaluate("document.querySelectorAll('.message.assistant').length");
  await type("#message-input", text);
  await key("Enter", "Enter");
  await waitFor(`document.querySelectorAll('.message.assistant').length === ${count + 1} && document.querySelector('#loading-message').hidden`, `response to ${text}`);
}
async function noOverflow(label) {
  await expect("document.documentElement.scrollWidth <= innerWidth && document.body.scrollWidth <= innerWidth", `No horizontal page overflow: ${label}`);
  await expect("(() => {const r=document.querySelector('#chat-form').getBoundingClientRect();return r.bottom<=innerHeight && r.left>=0 && r.right<=innerWidth;})()", `Composer visible: ${label}`);
}

async function readable(selectors) {
  const measurements = await evaluate(`(() => {
    const rgb = value => value.match(/[\\d.]+/g).map(Number);
    const light = color => {
      const values = rgb(color).slice(0, 3).map(value => {const v=value/255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});
      return values[0]*.2126+values[1]*.7152+values[2]*.0722;
    };
    return ${JSON.stringify(selectors)}.map(selector => {
      const [target,pseudo] = selector.split('::');
      const node = document.querySelector(target);
      const style = getComputedStyle(node,pseudo?'::'+pseudo:null);
      let parent=node, background;
      while(parent) {const value=getComputedStyle(parent).backgroundColor;const channels=rgb(value);if(channels.length===3||channels[3]===1){background=value;break;}parent=parent.parentElement;}
      const a=light(style.color), b=light(background||'rgb(255,255,255)');
      return {selector,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),size:parseFloat(style.fontSize)};
    });
  })()`);
  for (const item of measurements) {
    assert.ok(item.ratio >= 4.5, `${item.selector}: contrast ${item.ratio.toFixed(2)}`);
    assert.ok(item.size >= 11, `${item.selector}: text ${item.size}px`);
  }
  checks.push(`Readable secondary text: ${selectors.join(', ')}`);
}

try {
  await fs.mkdir(out, {recursive: true});
  const appPort = await freePort();
  const debugPort = await freePort();
  const base = `http://127.0.0.1:${appPort}`;
  const candidates = [process.env.CHROME_PATH, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium"].filter(Boolean);
  let executable;
  for (const candidate of candidates) {try {await fs.access(candidate); executable = candidate; break;} catch {}}
  if (!executable) throw new Error("Chrome no encontrado. Define CHROME_PATH con su ejecutable.");
  app = spawn("bash", [path.join(root, "run_web.sh"), "--port", String(appPort)], {
    cwd: scratch,
    env: {...process.env, DATABASE_URL: `sqlite:///${path.join(scratch, "test.db")}`, NVIDIA_API_KEY: "", TWELVE_DATA_API_KEY: "", MARKETAUX_API_KEY: "", FMP_API_KEY: "", INVESTIQ_SECTOR_ETF_FALLBACK_ENABLED: "false", SEC_USER_AGENT: ""},
    stdio: "ignore",
  });
  app.on("error", () => {processError = new Error("No se pudo iniciar el servidor Python.");});
  app.on("exit", (code) => {if (code) processError = new Error("El servidor Python no arrancó; comprueba dependencias y permisos de puertos locales.");});
  await poll(async () => (await fetch(`${base}/api/health`)).ok, "local Python server");
  chrome = spawn(executable, ["--headless=new", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${path.join(scratch, "chrome")}`, "--no-first-run", "--no-default-browser-check", "--disable-background-networking", "--disable-component-update", "--disable-sync", "--disable-default-apps", "--metrics-recording-only", "--use-mock-keychain", "about:blank"], {stdio: "ignore"});
  chrome.on("error", () => {processError = new Error("Chrome no pudo iniciar; comprueba permisos de ejecución.");});
  await poll(async () => (await fetch(`http://127.0.0.1:${debugPort}/json/version`)).ok, "headless Chrome");
  const tab = await (await fetch(`http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent(base)}`, {method: "PUT"})).json();
  socket = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {socket.addEventListener("open", resolve, {once: true}); socket.addEventListener("error", reject, {once: true});});
  socket.addEventListener("message", (event) => {
    const packet = JSON.parse(event.data);
    const deferred = pending.get(packet.id);
    if (deferred) {clearTimeout(deferred.timer); pending.delete(packet.id); packet.error ? deferred.reject(new Error(packet.error.message)) : deferred.resolve(packet.result);}
    if (packet.method === "Runtime.exceptionThrown") errors.push(packet.params.exceptionDetails.text);
  });
  await cdp("Page.enable"); await cdp("Runtime.enable"); await cdp("Network.enable");
  await viewport(1440, 900);
  await cdp("Page.navigate", {url: base});
  await waitFor("!document.querySelector('#message-input').disabled && document.querySelectorAll('.instrument-button').length===20", "catalogue and chat ready");
  await expect("!document.querySelector('#welcome').hidden", "Welcome visible before first message");
  await expect("document.querySelectorAll('.branch-action').length===4 && document.querySelectorAll('.suggestion').length===5", "Quick access and starter questions expose the available modes");
  await expect("document.querySelector('#mode-text').textContent==='Respuestas locales'", "Local mode accurately labelled");
  await waitFor("!document.querySelector('#mentor-video').paused && document.querySelector('#mentor-media').classList.contains('is-playing')", "local professor video starts in the welcome");
  await expect("document.querySelector('#mentor-video').currentSrc.endsWith('/media/profesor-investiq.webm') && document.querySelector('.mentor-visual figcaption').textContent.includes('ilustrativas')", "Transparent local video and illustrative graphics label");
  await expect("document.querySelector('#mentor-video').loop && document.querySelector('#mentor-video').muted && !document.querySelector('#mentor-video').controls && !document.querySelector('#mentor-playback')", "Professor animation loops silently without playback controls");
  await evaluate("document.querySelector('#mentor-video').currentTime = Math.max(0, document.querySelector('#mentor-video').duration - 0.2)");
  await waitFor("document.querySelector('#mentor-video').currentTime < 2 && !document.querySelector('#mentor-video').paused", "professor animation starts again at the end");
  await readable(["#message-input::placeholder", ".composer-help", ".composer-invitation", ".branch-intro p", ".branch-copy small"]);
  await noOverflow("1440x900"); await screenshot("desktop");
  await type("#symbol-search", "apple");
  await expect("document.querySelectorAll('.instrument-button').length===1 && document.querySelector('.instrument-button').dataset.symbol==='AAPL'", "Catalogue search resolves company name");
  await type("#symbol-search", "zzzz");
  await expect("!document.querySelector('#no-instruments').hidden", "Empty search gives recovery guidance");
  await type("#symbol-search", "");
  await send("quiero saber que es");
  await expect("document.querySelector('#mentor-video').paused", "Professor video pauses when the chat begins");
  await expect("document.querySelector('.message.assistant:last-child').textContent.includes('¿Qué')", "Incomplete question asks for clarification");
  await send("volatilidad");
  await expect("document.querySelector('.message.assistant:last-child').textContent.toLowerCase().includes('volatilidad')", "Short answer completes educational question");
  await send("que es el aapl");
  await expect("document.querySelector('.message.assistant:last-child').textContent.includes('Apple')", "AAPL is defined from the local catalogue");
  await click(".message.assistant:last-child .response-sources summary");
  await expect("document.querySelector('.message.assistant:last-child .local-source').textContent.includes('local')", "Local catalogue source is visible");
  await readable([".response-footnote", ".response-sources", ".local-source"]);
  await send("que mas puedes hacer");
  await expect("document.querySelector('.message.assistant:last-child').textContent.toLowerCase().includes('compar')", "Conversational capabilities question works");
  await expect("[...document.querySelectorAll('.message.assistant')].every(e=>e.textContent.includes('No es asesoría financiera.'))", "Every response displays the educational disclaimer");
  await screenshot("desktop-chat");
  await type("#message-input", "una pregunta");
  await key("Enter", "Enter", 8);
  await expect("document.querySelector('#message-input').value.includes(String.fromCharCode(10))", "Shift+Enter inserts a line without sending");
  await type("#message-input", "");
  await click("#memory-settings summary");
  const enabledBefore = await evaluate("document.querySelector('#memory-enabled').checked");
  await click("#memory-enabled");
  await waitFor("!document.querySelector('#memory-enabled').disabled", "memory setting saved");
  await expect(`document.querySelector('#memory-enabled').checked===${!enabledBefore}`, "Memory setting persists through API");
  await screenshot("memory");
  await cdp("Network.emulateNetworkConditions", {offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0});
  await type("#message-input", "hola"); await key("Enter", "Enter");
  await waitFor("!document.querySelector('#app-error').hidden", "network failure visible");
  await screenshot("error");
  await cdp("Network.emulateNetworkConditions", {offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1});
  await click("#retry-action");
  await waitFor("document.querySelector('#app-error').hidden && document.querySelector('#loading-message').hidden", "retry completed");
  await expect("[...document.querySelectorAll('.message.user')].filter(e=>e.textContent==='hola').length===1", "Retry does not duplicate user message");
  await cdp("Page.reload");
  await waitFor("!document.querySelector('#message-input').disabled", "reload ready");
  await expect("document.querySelectorAll('.message.assistant').length===5", "Reload restores temporary conversation");
  await click("#new-conversation");
  await waitFor("!document.querySelector('#welcome').hidden", "new conversation reset");
  await expect("document.querySelectorAll('.message').length===0", "New conversation clears visible history");
  await send("volatilidad");
  await click('#open-sectors');
  await waitFor("document.querySelectorAll('.message.assistant').length===1 && document.querySelector('#loading-message').hidden && document.querySelector('.message.user')?.textContent.includes('NASDAQ')", "NASDAQ shortcut starts a new conversation");
  await expect("document.querySelectorAll('.message.user').length===1 && document.querySelector('.message.user').textContent.includes('NASDAQ')", "NASDAQ shortcut clears previous conversation");
  await click('#new-conversation');
  await waitFor("!document.querySelector('#welcome').hidden", "welcome returns before metrics shortcut");
  await click('.suggestion[data-starter="metrics"]');
  await waitFor("!document.querySelector('#welcome').hidden && document.querySelector('#message-input').value.startsWith('Dame las métricas')", "Metrics starter resets to a new draft");
  await expect("document.querySelectorAll('.message').length===0 && document.querySelector('#message-input').value.startsWith('Dame las métricas')", "Metrics starter creates a new draft without sending it");
  await click('#open-sp500-sectors');
  await waitFor("document.querySelectorAll('.message.assistant').length===1 && document.querySelector('#loading-message').hidden && document.querySelector('.message.user')?.textContent.includes('S&P 500')", "S&P 500 shortcut opens its own conversation");
  await expect("document.querySelectorAll('.message.user').length===1", "S&P 500 shortcut clears the metrics draft and history");
  await click('#open-recommendations');
  await waitFor("document.querySelectorAll('.message.assistant').length===1 && document.querySelector('#loading-message').hidden && document.querySelectorAll('.message.user').length===0", "Guided recommendations start a separate conversation");
  await click('#new-conversation');
  await waitFor("!document.querySelector('#welcome').hidden", "welcome restored after guided recommendation");
  await viewport(1024, 768); await noOverflow("1024x768"); await screenshot("small-desktop");
  await viewport(768, 1024); await noOverflow("768x1024"); await screenshot("tablet");
  await viewport(390, 844); await noOverflow("390x844"); await screenshot("mobile");
  await click("#open-sidebar");
  await sleep(240);
  await expect("document.querySelector('#main').inert && document.querySelector('#sidebar').getAttribute('aria-modal')==='true'", "Mobile explorer protects keyboard focus");
  await screenshot("mobile-menu");
  await key("Escape", "Escape");
  await expect("!document.querySelector('#sidebar').classList.contains('open') && document.activeElement.id==='open-sidebar'", "Escape closes explorer and returns focus");
  await sleep(240);
  await click("#open-sidebar");
  await sleep(240);
  await type("#symbol-search", "AAPL");
  await click('.instrument-button[data-symbol="AAPL"]');
  await waitFor("document.querySelectorAll('.message.assistant').length===1", "catalogue chat response");
  await expect("!document.querySelector('#sidebar').classList.contains('open') && !document.querySelector('#main').inert", "Selecting symbol opens its conversation on mobile");
  await noOverflow("mobile conversation"); await screenshot("mobile-chat");
  await cdp("Emulation.setEmulatedMedia", {features: [{name: "prefers-reduced-motion", value: "reduce"}]});
  await expect("matchMedia('(prefers-reduced-motion: reduce)').matches", "Reduced motion preference supported");
  if (frontOnly) {
    await click('#mobile-new-conversation');
    await waitFor("!document.querySelector('#welcome').hidden", "welcome returns with reduced motion");
    await expect("document.querySelector('#mentor-video').paused && !document.querySelector('#mentor-media').classList.contains('is-playing') && document.querySelector('.mentor-still').naturalWidth===1312", "Reduced motion keeps the supplied robot image visible");
  }
  if (!frontOnly) {
  await type("#message-input", '<img src=x onerror="alert(1)">'); await key("Enter", "Enter");
  await waitFor("document.querySelectorAll('.message.assistant').length===2", "untrusted text handled");
  await expect("document.querySelectorAll('.message.user img').length===0", "User HTML remains literal text");
  await click("#open-sidebar");
  await click("#memory-settings summary");
  await click("#forget-memory");
  await waitFor("!document.querySelector('#welcome').hidden && !document.querySelector('#forget-memory').disabled", "forget context completed");
  await expect("document.querySelectorAll('.message').length===0", "Forget context clears the visible conversation");
  await key("Escape", "Escape");
  await click(".suggestion:first-of-type");
  await waitFor("document.querySelectorAll('.message.assistant').length===1", "Guided recommendation suggestion completed");
  await expect("document.querySelector('.answer-content').textContent.includes('acciones, ETF o ambos')", "Recommendation suggestion starts guided exploration");
  await click("#mobile-new-conversation");
  await waitFor("!document.querySelector('#welcome').hidden", "mobile reset completed");
  await click(".suggestion:nth-of-type(2)");
  await waitFor("document.querySelectorAll('.message.assistant').length===1", "Single-symbol metrics suggestion completed");
  await expect("document.querySelector('.answer-content').textContent.includes('Qué símbolo quieres consultar')", "Metrics suggestion asks the user to choose a symbol");
  await click("#mobile-new-conversation");
  await waitFor("!document.querySelector('#welcome').hidden", "sector reset completed");
  await click(".suggestion:nth-of-type(3)");
  await waitFor("document.querySelectorAll('.message.assistant').length===1", "Sector snapshot suggestion completed");
  await expect("document.querySelector('.answer-content').textContent.includes('NASDAQ')", "Sector suggestion selects the only covered market");
  await click("#mobile-new-conversation");
  await waitFor("!document.querySelector('#welcome').hidden", "news reset completed");
  await click(".suggestion:nth-of-type(4)");
  await waitFor("document.querySelectorAll('.message.assistant').length===1", "News suggestion completed");
  await expect("/MARKETAUX_API_KEY|noticias verificadas/i.test(document.querySelector('.answer-content').textContent)", "News suggestion enters the news mode and reports data availability");
  await noOverflow("mobile after suggestions");
  await send("que es el sp500");
  await expect("(() => {const text=document.querySelector('.message.assistant:last-child .answer-content').textContent;return text.includes('S&P 500') && text.includes('500') && text.toLowerCase().includes('empresas');})()", "SP500 receives a grounded index explanation in the web chat");
  await click(".message.assistant:last-child .response-sources summary");
  await expect("document.querySelector('.message.assistant:last-child .source-link').href==='https://www.spglobal.com/spdji/en/indices/equity/sp-500/'", "Index explanation links to its official S&P source");
  await send("un ejemplo");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('S&P 500')", "Index follow-up keeps the educational topic");
  await noOverflow("mobile index explanation");
  await screenshot("mobile-sp500");
  await viewport(1440, 900);
  await click("#new-conversation");
  await waitFor("!document.querySelector('#welcome').hidden", "teacher lesson reset");
  await send("¿Qué es una acción?");
  await expect("/propiedad|parte|participación/i.test(document.querySelector('.message.assistant:last-child .answer-content').textContent)", "Teacher explains ownership with retrieved educational evidence");
  await expect("document.querySelector('.message.assistant:last-child .source-link').href.startsWith('https://')", "Teacher lesson includes an official source");
  await send("¿En qué se diferencia un ETF de una acción?");
  await expect("(() => {const text=document.querySelector('.message.assistant:last-child .answer-content').textContent;return text.includes('ETF') && text.toLowerCase().includes('acción');})()", "Conceptual comparison stays in the classroom flow");
  await send("¿Qué brokers existen para invertir?");
  await expect("/Interactive Brokers|Schwab|Fidelity/.test(document.querySelector('.message.assistant:last-child .answer-content').textContent)", "Broker lesson gives sourced examples");
  await expect("/país|residencia|jurisdicción/.test(document.querySelector('.message.assistant:last-child .answer-content').textContent)", "Broker examples retain jurisdiction limits");
  await screenshot("teacher-brokers");
  await send("¿Qué puedo usar en Colombia?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('no permite confirmar')", "Country follow-up acknowledges the limits of the reviewed library");
  await send("¿Y cuánto cobra hoy?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('no permite confirmar')", "Current fees are not invented");
  await send("¿Qué es un ETF apalancado?");
  await send("¿Y sus riesgos?");
  await expect("!document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('No encontré evidencia')", "Risk follow-up keeps the specific educational subject");
  await viewport(390, 844);
  await evaluate("(() => { const scroll=document.querySelector('#conversation-scroll'); scroll.scrollTop=scroll.scrollHeight; })()");
  await noOverflow("mobile teacher lesson");
  await screenshot("mobile-teacher");
  await send("¿Qué es una criptomoneda?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.toLowerCase().includes('cripto')", "Teacher explains crypto assets with reviewed evidence");
  await send("¿Qué es el RSI?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('RSI')", "Technical indicators are explained without trading instructions");
  await send("¿Cómo se interpreta?");
  await expect("/sobrecompra|sobreventa/.test(document.querySelector('.message.assistant:last-child .answer-content').textContent)", "Interpretation follow-up keeps the RSI lesson");
  await expect("document.querySelector('.message.assistant:last-child .source-link').href.endsWith('/rsi')", "Interpretation retains the RSI evidence");
  await send("¿Cómo funciona esto?");
  await expect("document.querySelector('.message.assistant:last-child .source-link').href.endsWith('/rsi')", "An active lesson takes priority over generic app help");
  await send("No entiendo");
  await expect("(() => {const text=document.querySelector('.message.assistant:last-child .answer-content').textContent;return text.includes('RSI') && text.includes('tendencia persistente');})()", "Clarification combines the meaning with a reviewed example");
  await send("¿Qué es la diversificación?");
  await send("¿Por qué importa?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('dependencia de un solo resultado')", "Importance follow-up stays on diversification");
  await send("Ahora explícame qué es un ETF");
  await send("¿Me lo explicas con un ejemplo?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('una sola empresa')", "Conversational request receives the ETF example");
  await send("¿Y qué costes tiene?");
  await expect("document.querySelector('.message.assistant:last-child .source-link').href.endsWith('/exchange-traded-fund-etf')", "Costs follow-up retains its specific fund context");
  await send("Ahora explícame la inflación");
  await expect("document.querySelector('.message.assistant:last-child .source-link').href.includes('imf.org')", "An explicit new subject replaces the preceding lesson");
  await send("¿Qué es AAPL?");
  await send("Un ejemplo");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('informe anual')", "An instrument definition continues as an educational example");
  await send("¿Y sus riesgos?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('Reconocer una marca')", "Instrument risk follow-up uses its reviewed issuer document");
  await send("Soy principiante");
  await send("¿Qué es un fondo de inversión?");
  await expect("(() => {const text=document.querySelector('.message.assistant:last-child .answer-content').textContent;return text.includes('Un fondo reúne dinero') && text.includes('cartera administrada');})()", "Beginner lesson preserves both the definition and the example");
  await expect("Array.from(document.querySelectorAll('.message.assistant')).every(e=>e.textContent.includes('No es asesoría financiera'))", "Every response in the extended lesson retains the disclaimer");
  await noOverflow("mobile contextual lesson");
  await screenshot("mobile-contextual-lesson");
  await send("¿Por qué importa?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('folleto')", "Beginner follow-up answers the requested explanation");
  await send("¿Qué es mejor para obtener mayores rentabilidades a largo plazo: un ETF o acciones individuales? ¿Qué sectores lideran hoy?");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('No hay un ganador universal')", "Combined question retains the long-term educational comparison");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('¿Quieres consultar Estados Unidos/NASDAQ?')", "Current sector query offers the only connected market");
  await send("Estados Unidos");
  await expect("document.querySelector('.message.assistant:last-child .answer-content').textContent.includes('no tengo un ranking sectorial actual verificado')", "Current sector leaders are not fabricated from static knowledge");
  await noOverflow("mobile trading education");
  await screenshot("mobile-trading-education");

  // Exercise the added branches against the actual Python service with a
  // separate temporary database. All values below are labelled offline fixtures.
  const branchPort = await freePort();
  const branchEnv = {...process.env, DATABASE_URL: `sqlite:///${path.join(scratch, 'branches.db')}`,
    PYTHONPATH: path.join(root, 'src'), NVIDIA_API_KEY: '', TWELVE_DATA_API_KEY: '',
    MARKETAUX_API_KEY: '', FMP_API_KEY: '', INVESTIQ_SECTOR_ETF_FALLBACK_ENABLED: 'false', SEC_USER_AGENT: ''};
  const python = process.env.INVESTIQ_PYTHON || path.join(root, '.venv', 'bin', 'python');
  const fixtureCode = String.raw`
from datetime import datetime, timedelta, timezone, date
import json
import os
import pandas as pd
from sqlmodel import Session
from investiq.data.database import create_db, make_engine
from investiq.data.models import InstrumentFeature, MLClusterRun, MarketContextCache
from investiq.domain import RouterDecision
from investiq.instruments import INSTRUMENTS
from investiq.ml.similarity import fit_similarity_model, save_model_artifact
from investiq.providers.headlines import daily_headlines
from investiq.providers.sectors import SECTOR_LABELS
from investiq.settings import Settings
from zoneinfo import ZoneInfo
from types import SimpleNamespace
now = datetime.now(timezone.utc)
settings = Settings(_env_file=None, database_url=os.environ['DATABASE_URL'], marketaux_api_key='offline-fixture')
engine = create_db(make_engine(settings.database_url))
frame = pd.DataFrame({item.symbol: {'volatility': .1+(i//7)*.2+(i%7)*.004,
    'mean_peer_correlation': .1+(i//7)*.3+(i%7)*.003,
    'beta': .3+(i//7)*.7+(i%7)*.006} for i,item in enumerate(INSTRUMENTS)}).T
fit = fit_similarity_model(frame)
assert fit.passed_thresholds
artifact = {**fit.model, 'observation_start': '2025-01-01', 'observation_end': '2026-10-30'}
filename = save_model_artifact(artifact, 'ml/artifacts/offline-web-fixture.joblib')
with Session(engine) as db:
    for item in INSTRUMENTS:
        db.add(InstrumentFeature(symbol=item.symbol, calculated_at=now-timedelta(minutes=1),
            sector=item.sector, volatility_bucket='fixture', **frame.loc[item.symbol].to_dict()))
    db.add(MLClusterRun(run_id='offline-web-fixture', created_at=now, artifact_path=str(filename),
        universe_size=20, observation_start=date(2025,1,1), observation_end=date(2026,10,30), seed=42,
        n_clusters=fit.model['model'].n_clusters, silhouette=fit.silhouette, stability_ari=fit.stability_ari,
        passed_thresholds=fit.passed_thresholds))
    day = now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    sectors = [{'sector': name, 'exchange': 'NASDAQ', 'date': day, 'averageChange': i/10}
               for i,name in enumerate(SECTOR_LABELS)]
    db.add(MarketContextCache(cache_key='sectors:NASDAQ:'+day, payload_json=json.dumps(sectors),
        fetched_at=now, expires_at=now+timedelta(minutes=15)))
    db.commit()
    articles = [{'title': 'OFFLINE FIXTURE: Bank ACME update '+str(i),
        'description': 'OFFLINE FIXTURE excerpt number '+str(i)+': this is synthetic browser test content.',
        'url': 'https://example.org/offline-news/'+str(i), 'language': 'en', 'published_at': now.isoformat()}
        for i in range(1,4)]
    daily_headlines(db, RouterDecision(intent='market_news'), settings, now=now,
        http_get=lambda *a,**k: SimpleNamespace(raise_for_status=lambda:None, json=lambda:{'data':articles}))
engine.dispose()
`;
  const setup = spawn(python, ['-c', fixtureCode], {cwd: scratch, env: branchEnv, stdio: 'ignore'});
  await new Promise((resolve, reject) => {
    setup.once('error', reject);
    setup.once('exit', code => code === 0 ? resolve() : reject(new Error('No se pudieron preparar los fixtures offline de navegador.')));
  });
  const previousApp = app;
  previousApp.kill('SIGTERM');
  await new Promise(resolve => previousApp.exitCode !== null ? resolve() : previousApp.once('exit', resolve));
  app = spawn(python, ['-m', 'investiq.web.server', '--port', String(branchPort)],
    {cwd: scratch, env: branchEnv, stdio: 'ignore'});
  app.on('error', () => {processError = new Error('No arrancó el servidor de fixtures offline.');});
  const branchBase = `http://127.0.0.1:${branchPort}`;
  await poll(async () => (await fetch(`${branchBase}/api/health`)).ok, 'offline branch server');
  await cdp('Page.navigate', {url: branchBase});
  await waitFor(`location.port==='${branchPort}' && document.querySelector('#message-input') && !document.querySelector('#message-input').disabled`, 'branch app bootstrap');
  await expect("document.querySelectorAll('.branch-action').length===3", 'News, exploration and sector actions stay available beside the chat');
  await click('#open-news');
  await waitFor("document.querySelectorAll('.response-action').length===3", 'cached offline fixture headlines');
  await expect("document.querySelector('.message.assistant:last-child').textContent.includes('OFFLINE FIXTURE')", 'News displays retrieved fixture headlines and sources');
  await click('.message.assistant:last-child .response-action:nth-child(2)');
  await waitFor("document.querySelector('.message.assistant:last-child').textContent.includes('excerpt number 2')", 'selected fixture summary');
  await expect("document.querySelector('.message.assistant:last-child .source-link').href.endsWith('/offline-news/2')", 'Summary button selects its exact article source');
  await expect("document.querySelector('.message.assistant:last-child').textContent.toLowerCase().includes('extracto')", 'Summary discloses the excerpt boundary');
  await expect("!document.querySelector('.message.user:last-of-type')?.textContent.includes('news:day:') && Array.from(document.querySelectorAll('.message.user')).every(e=>!e.textContent.includes('news:day:'))", 'Selecting a summary keeps internal IDs out of the visible conversation');
  await screenshot('mobile-news-offline-fixture');
  await click('#open-recommendations');
  await waitFor("document.querySelector('.message.assistant:last-child').textContent.includes('acciones, ETF o ambos')", 'exploration kind question');
  await send('ambos');
  await expect("document.querySelector('.message.assistant:last-child').textContent.toLowerCase().includes('cuándo podrías necesitar')", 'Exploration asks for the cash horizon in the chat');
  await send('largo plazo');
  await expect("document.querySelector('.message.assistant:last-child').textContent.includes('baja, media o alta')", 'Exploration asks for a historical-variation criterion');
  await send('baja');
  await send('sin referencia');
  await expect("document.querySelector('.message.assistant:last-child table')!==null", 'Fitted fixture KMeans produces a rendered candidate table');
  await expect("document.querySelector('.message.assistant:last-child').textContent.includes('11.20%')", 'Candidate volatility is formatted as an annualized percentage');
  await expect("document.querySelector('.message.assistant:last-child').textContent.includes('no una probabilidad')", 'ML coincidence is not presented as a profit probability');
  await expect("Array.from(document.querySelectorAll('.message.assistant:last-child .local-source')).some(e=>e.textContent.includes('clustering'))", 'Candidates retain their model provenance');
  await noOverflow('mobile fitted-model candidates');
  await screenshot('mobile-exploration-offline-fixture');
  await click('#open-sectors');
  await waitFor("document.querySelector('.message.assistant:last-child table')?.rows.length===12", 'sector snapshot table');
  await expect("document.querySelector('.message.assistant:last-child table').rows.length===12", 'Sector fixture requires all eleven sectors before displaying the ranking');
  await expect("document.querySelector('.message.assistant:last-child').textContent.includes('NASDAQ')", 'Sector ranking declares the exchange scope');
  await expect("document.querySelector('.message.assistant:last-child').textContent.includes('hora exacta')", 'Snapshot date is not invented as a provider timestamp');
  await noOverflow('mobile sector snapshot');
  await screenshot('mobile-sectors-offline-fixture');
  }
  assert.deepEqual(errors, [], "No uncaught browser exceptions");
  checks.push("No uncaught browser exceptions");
  await fs.writeFile(path.join(out, "browser-report.json"), JSON.stringify({checks, snapshots, providerCalls: false, database: "temporary", browser: "Chrome headless"}, null, 2));
  console.log(JSON.stringify({passed: checks.length, screenshots: snapshots, providerCalls: false}, null, 2));
} finally {
  socket?.close();
  for (const process of [chrome, app]) if (process && process.exitCode === null) process.kill("SIGTERM");
  await sleep(500);
  await fs.rm(scratch, {recursive: true, force: true, maxRetries: 3, retryDelay: 200}).catch(() => {});
}
