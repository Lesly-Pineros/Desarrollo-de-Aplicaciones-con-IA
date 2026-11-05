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
    env: {...process.env, DATABASE_URL: `sqlite:///${path.join(scratch, "test.db")}`, NVIDIA_API_KEY: "", TWELVE_DATA_API_KEY: "", MARKETAUX_API_KEY: "", SEC_USER_AGENT: ""},
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
  await expect("document.querySelector('#mode-text').textContent==='Respuestas locales'", "Local mode accurately labelled");
  await readable(["#message-input::placeholder", ".composer-help", ".composer-invitation", ".catalogue-hint", ".sidebar-note"]);
  await noOverflow("1440x900"); await screenshot("desktop");
  await type("#symbol-search", "apple");
  await expect("document.querySelectorAll('.instrument-button').length===1 && document.querySelector('.instrument-button').dataset.symbol==='AAPL'", "Catalogue search resolves company name");
  await type("#symbol-search", "zzzz");
  await expect("!document.querySelector('#no-instruments').hidden", "Empty search gives recovery guidance");
  await type("#symbol-search", "");
  await send("quiero saber que es");
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
  await viewport(1024, 768); await noOverflow("1024x768"); await screenshot("small-desktop");
  await viewport(768, 1024); await noOverflow("768x1024"); await screenshot("tablet");
  await viewport(390, 844); await noOverflow("390x844"); await screenshot("mobile");
  await click("#open-sidebar");
  await expect("document.querySelector('#main').inert && document.querySelector('#sidebar').getAttribute('aria-modal')==='true'", "Mobile explorer protects keyboard focus");
  await screenshot("mobile-menu");
  await key("Escape", "Escape");
  await expect("!document.querySelector('#sidebar').classList.contains('open') && document.activeElement.id==='open-sidebar'", "Escape closes explorer and returns focus");
  await click("#open-sidebar");
  await type("#symbol-search", "AAPL");
  await click('.instrument-button[data-symbol="AAPL"]');
  await waitFor("document.querySelectorAll('.message.assistant').length===1", "catalogue chat response");
  await expect("!document.querySelector('#sidebar').classList.contains('open') && !document.querySelector('#main').inert", "Selecting symbol opens its conversation on mobile");
  await noOverflow("mobile conversation"); await screenshot("mobile-chat");
  await cdp("Emulation.setEmulatedMedia", {features: [{name: "prefers-reduced-motion", value: "reduce"}]});
  await expect("matchMedia('(prefers-reduced-motion: reduce)').matches", "Reduced motion preference supported");
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
  await waitFor("document.querySelectorAll('.message.assistant').length===1", "ETF suggestion completed");
  await expect("document.querySelector('.answer-content').textContent.includes('ETF')", "Learning suggestion starts a real educational turn");
  await click("#mobile-new-conversation");
  await waitFor("!document.querySelector('#welcome').hidden", "mobile reset completed");
  await click(".suggestion:last-of-type");
  await waitFor("document.querySelectorAll('.message.assistant').length===1", "comparison suggestion completed");
  await expect("document.querySelector('.answer-content').textContent.includes('compar')", "Comparison suggestion asks a relevant next question");
  await noOverflow("mobile after suggestions");
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
