import { api, requireUser, renderTopbar, TERMINATION, resultText, outcomeFor, timeControlText,
         colorDot, toast, escapeHtml } from "./common.js";
import { Board, parseFen } from "./board.js";
import { pieceSvg } from "./pieces.js";

const gameId = location.pathname.split("/").pop();
const user = await requireUser({ guestPrompt: true });
renderTopbar(user, "play");

const board = new Board(document.getElementById("board"), {
  onMove: uci => send({ type: "move", uci }),
  onPremove: uci => { premove = uci; },
});
const el = id => document.getElementById(id);

let state = null;
let receivedAt = 0;      // performance.now() when `state` arrived, for ticking clocks
let viewPly = null;      // null = follow the live position, otherwise index into state.fens
let premove = null;      // move queued during the opponent's turn, played as soon as it's ours
let ws = null;
let retry = 0;
let pingTimer = null;

// ---------- connection ----------

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/game/${encodeURIComponent(gameId)}`);
  ws.onopen = () => {
    retry = 0;
    el("conn-status").textContent = "";
    clearInterval(pingTimer);
    pingTimer = setInterval(() => send({ type: "ping" }), 25000);
  };
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "state") onState(msg);
    else if (msg.type === "error") toast(msg.message);
  };
  ws.onclose = ev => {
    clearInterval(pingTimer);
    if (ev.code === 4404) { showMissing(); return; }
    if (ev.code === 4401) { location.href = "/login?next=" + encodeURIComponent(location.pathname); return; }
    el("conn-status").textContent = "Utracono połączenie — łączę ponownie…";
    setTimeout(connect, Math.min(8000, 500 * 2 ** retry++));
  };
}

function send(msg) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
  else toast("Brak połączenia z serwerem.");
}

function showMissing() {
  document.querySelector("main").innerHTML =
    `<div class="card" style="max-width:420px;margin:60px auto;text-align:center">
       <h2>Nie ma takiej partii</h2><p class="muted">Link jest nieprawidłowy albo partia została usunięta.</p>
       <a href="/"><button class="primary">Wróć do lobby</button></a></div>`;
}

// ---------- state ----------

function onState(next) {
  const prev = state;
  const wasAtEnd = viewPly === null || (prev && viewPly >= prev.fens.length - 1);
  state = next;
  receivedAt = performance.now();
  if (wasAtEnd) viewPly = null;
  if (prev && next.moves.length > prev.moves.length) playSound(next);
  if (prev && prev.status !== next.status && next.status === "finished") playSound(next, true);
  if (premove && tryPremove()) return;
  render();
}

// Our turn has come: play the queued premove if it is legal now, otherwise drop it.
function tryPremove() {
  if (state.status !== "active" || !state.you) { premove = null; return false; }
  if (state.turn !== state.you) return false;
  const uci = premove;
  premove = null;
  const match = state.legal.find(m => m === uci) || state.legal.find(m => m === uci.slice(0, 4) + "q");
  if (!match) return false;
  render();
  board._play(match);   // shows the move at once, then sends it
  return true;
}

function currentPly() {
  return viewPly === null ? state.fens.length - 1 : viewPly;
}

function myOrientation() {
  if (state.you) return state.you;
  if (state.status === "waiting" && state.isCreator && state.creatorColor === "black") return "black";
  return "white";
}

// ---------- rendering ----------

function render() {
  const ply = currentPly();
  const live = ply === state.fens.length - 1;
  board.setOrientation(myOrientation());
  board.setState({
    fen: state.fens[ply],
    legal: live ? state.legal : [],
    lastMove: ply > 0 ? state.moves[ply - 1] : null,
    check: live ? state.check : null,
    interactive: live && state.status === "active" && state.you === state.turn,
    premovable: live && state.status === "active" && !!state.you && state.you !== state.turn,
    myColor: state.you ? state.you[0] : null,
    premove: live ? premove : null,
  });
  renderPlayers();
  renderCaptures(state.fens[ply]);
  renderMoves(ply);
  renderPanel();
  renderControls();
  updateClocks();
  const myTurn = state.status === "active" && state.you && state.you === state.turn;
  document.title = (myTurn ? "Twój ruch · " : "") + "Partia · Szachy";
}

function playerName(color) {
  if (state[color]) return state[color];
  // before anyone joins, show the creator on the side they asked for
  if (state.status === "waiting" && state.creatorColor === color) return state.creator;
  return null;
}

function renderPlayers() {
  const bottom = myOrientation();
  const top = bottom === "white" ? "black" : "white";
  for (const [id, color] of [["top-player", top], ["bottom-player", bottom]]) {
    const box = el(id);
    const name = playerName(color);
    const sub = (color === "white" ? "białe" : "czarne") + (state.you === color ? " · Ty" : "");
    box.querySelector(".nm").innerHTML = name
      ? `<span class="who">${escapeHtml(name)}</span><small>${sub}</small>`
      : `<span class="who muted">czeka na gracza…</span><small>${color === "white" ? "białe" : "czarne"}</small>`;
    box.dataset.color = color;
  }
}

// ---------- captured pieces ----------

const START_COUNT = { p: 8, n: 2, b: 2, r: 2, q: 1 };
const VALUE = { p: 1, n: 3, b: 3, r: 5, q: 9 };
const CAPTURE_ORDER = ["p", "n", "b", "r", "q"];

// What each side has taken (pieces missing from the opponent's starting set) and who is ahead.
function materialFromFen(fen) {
  const count = { w: { p: 0, n: 0, b: 0, r: 0, q: 0 }, b: { p: 0, n: 0, b: 0, r: 0, q: 0 } };
  for (const piece of Object.values(parseFen(fen))) {
    if (piece[1] !== "k") count[piece[0]][piece[1]]++;
  }
  const score = c => CAPTURE_ORDER.reduce((sum, t) => sum + count[c][t] * VALUE[t], 0);
  const takenFrom = c => {
    const taken = {};
    // a promoted piece makes its type "over-full"; it then cancels one captured pawn
    let extra = 0;
    for (const t of ["n", "b", "r", "q"]) extra += Math.max(0, count[c][t] - START_COUNT[t]);
    for (const t of CAPTURE_ORDER) taken[t] = Math.max(0, START_COUNT[t] - count[c][t]);
    taken.p = Math.max(0, taken.p - extra);
    return taken;
  };
  return { white: takenFrom("b"), black: takenFrom("w"), diff: score("w") - score("b") };
}

function renderCaptures(fen) {
  const m = materialFromFen(fen);
  const bottom = myOrientation();
  const top = bottom === "white" ? "black" : "white";
  for (const [id, color] of [["captures-top", top], ["captures-bottom", bottom]]) {
    const taken = m[color];                       // opponent pieces this player has captured
    const victim = color === "white" ? "b" : "w";
    const groups = CAPTURE_ORDER.filter(t => taken[t]).map(t =>
      `<span class="group">${`<span class="cap">${pieceSvg(victim + t)}</span>`.repeat(taken[t])}</span>`).join("");
    const lead = color === "white" ? m.diff : -m.diff;
    el(id).innerHTML = groups + (lead > 0 ? `<span class="delta">+${lead}</span>` : "");
  }
}

function renderMoves(ply) {
  const grid = el("moves");
  let html = "";
  for (let i = 0; i < state.san.length; i += 2) {
    html += `<div class="num">${i / 2 + 1}.</div>`;
    for (const j of [i, i + 1]) {
      html += j < state.san.length
        ? `<div class="mv${j + 1 === ply ? " current" : ""}" data-ply="${j + 1}">${state.san[j]}</div>`
        : `<div></div>`;
    }
  }
  if (!state.san.length) html = `<div class="moves-empty">Partia jeszcze się nie zaczęła</div>`;
  grid.innerHTML = html;
  grid.querySelectorAll(".mv").forEach(m => m.onclick = () => goTo(Number(m.dataset.ply)));
  const current = grid.querySelector(".mv.current");
  const box = el("moves-box");
  if (viewPly === null) box.scrollTop = box.scrollHeight;
  else if (current) current.scrollIntoView({ block: "nearest" });
}

function renderPanel() {
  const panel = el("panel");
  const s = state;
  const tc = timeControlText(s.initialMs / 60000, s.incrementMs / 1000);
  let html = "";

  if (s.status === "waiting") {
    if (s.isCreator) {
      html = `<div class="banner">
        <div class="big">Czekamy na przeciwnika</div>
        <div class="sub">Tempo ${tc}. Wyślij ten link znajomemu:</div>
        <div class="share"><input id="share-link" readonly value="${location.href}"><button class="dark small" id="copy">Kopiuj</button></div>
        <div class="row"><button id="cancel">Anuluj partię</button></div></div>`;
    } else {
      const color = { white: "białymi", black: "czarnymi", random: "losowym kolorem" }[s.creatorColor];
      html = `<div class="banner">
        <div class="big">Zaproszenie do gry</div>
        <div class="sub">${escapeHtml(s.creator)} gra ${color}, tempo ${tc}.</div>
        <div class="row"><button class="primary" id="join">Dołącz do partii</button></div></div>`;
    }
  } else if (s.status === "active") {
    if (s.abortInMs !== null && s.abortInMs !== undefined) {
      const who = s.you === "white" ? "Masz" : "Białe mają";
      html += `<div class="banner"><div class="sub">${who} <b id="abort-secs"></b> s na pierwszy ruch, inaczej partia zostanie przerwana.</div></div>`;
    }
    if (s.drawOffer && s.you && s.drawOffer !== s.you) {
      html += `<div class="banner offer"><div class="big">Przeciwnik proponuje remis</div>
        <div class="row"><button class="primary" id="accept-draw">Przyjmij</button><button id="decline-draw">Odrzuć</button></div></div>`;
    } else if (s.drawOffer && s.drawOffer === s.you) {
      html += `<div class="banner offer"><div class="sub">Zaproponowałeś remis. Czekamy na odpowiedź.</div></div>`;
    }
    if (!s.you) html += `<div class="banner"><div class="sub">Oglądasz partię jako widz · tempo ${tc}</div></div>`;
  } else if (s.status === "finished") {
    let headline = resultText(s.result);
    if (s.you) headline = { win: "Wygrana", loss: "Przegrana", draw: "Remis" }[outcomeFor(s.result, s.you)];
    html = `<div class="banner"><div class="big">${headline}</div>
      <div class="sub">${s.result} · ${TERMINATION[s.termination] || ""}</div>
      <div class="row"><a href="/"><button class="primary">Nowa partia</button></a>
      <a href="/api/games/${s.id}/pgn"><button>Pobierz PGN</button></a></div></div>`;
  } else if (s.status === "aborted") {
    html = `<div class="banner"><div class="big">Partia przerwana</div>
      <div class="sub">Nikt nie wygrał, partia nie trafia do historii.</div>
      <div class="row"><a href="/"><button class="primary">Wróć do lobby</button></a></div></div>`;
  }
  panel.innerHTML = html;

  const on = (id, fn) => { const b = el(id); if (b) b.onclick = fn; };
  on("copy", async () => {
    try { await navigator.clipboard.writeText(location.href); toast("Skopiowano link"); }
    catch { el("share-link").select(); }
  });
  on("cancel", async () => {
    try { await api(`/api/games/${gameId}/cancel`, { method: "POST" }); location.href = "/"; }
    catch (e) { toast(e.message); }
  });
  on("join", async () => {
    try { await api(`/api/games/${gameId}/join`, { method: "POST" }); }
    catch (e) { toast(e.message); }
  });
  on("accept-draw", () => send({ type: "accept_draw" }));
  on("decline-draw", () => send({ type: "decline_draw" }));
}

function renderControls() {
  const box = el("controls");
  const s = state;
  if (s.status !== "active" || !s.you) { box.innerHTML = ""; return; }
  const canAbort = s.moves.length < 2;
  box.innerHTML = `
    ${canAbort ? `<button class="link" id="abort">Przerwij</button>` : ""}
    <button class="link" id="offer-draw" ${s.drawOffer === s.you ? "disabled" : ""}>½ Zaproponuj remis</button>
    <button class="link" id="resign">Poddaj się</button>`;
  const abort = el("abort");
  if (abort) abort.onclick = () => send({ type: "abort" });
  el("offer-draw").onclick = () => send({ type: "offer_draw" });
  el("resign").onclick = () => { if (confirm("Na pewno chcesz się poddać?")) send({ type: "resign" }); };
}

// ---------- clocks ----------

function formatClock(ms) {
  ms = Math.max(0, ms);
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), s = total % 60;
  const pad = n => String(n).padStart(2, "0");
  if (h) return `${h}:${pad(m)}:${pad(s)}`;
  if (ms < 10000) return `${m}:${pad(s)}.${Math.floor((ms % 1000) / 100)}`;
  return `${m}:${pad(s)}`;
}

function updateClocks() {
  if (!state) return;
  const elapsed = performance.now() - receivedAt;
  for (const id of ["top-player", "bottom-player"]) {
    const box = el(id);
    const color = box.dataset.color;
    const clock = box.querySelector(".clock");
    if (state.status === "waiting") { clock.textContent = formatClock(state.initialMs); continue; }
    let ms = state.clocks[color];
    const running = state.clockRunning === color;
    if (running) ms -= elapsed;
    clock.textContent = formatClock(ms);
    clock.classList.toggle("running", running);
    clock.classList.toggle("low", ms < 10000 && state.status === "active");
  }
  const abortEl = el("abort-secs");
  if (abortEl && state.abortInMs != null) abortEl.textContent = Math.max(0, Math.ceil((state.abortInMs - elapsed) / 1000));
}
setInterval(updateClocks, 100);

// ---------- history navigation ----------

function goTo(ply) {
  if (!state) return;
  const last = state.fens.length - 1;
  ply = Math.max(0, Math.min(last, ply));
  viewPly = ply === last ? null : ply;
  render();
}

el("nav-first").onclick = () => goTo(0);
el("nav-prev").onclick = () => goTo(currentPly() - 1);
el("nav-next").onclick = () => goTo(currentPly() + 1);
el("nav-last").onclick = () => goTo(Infinity);
document.addEventListener("keydown", e => {
  if (!state || e.target.tagName === "INPUT") return;
  if (e.key === "ArrowLeft") goTo(currentPly() - 1);
  else if (e.key === "ArrowRight") goTo(currentPly() + 1);
  else if (e.key === "ArrowUp" || e.key === "Home") goTo(0);
  else if (e.key === "ArrowDown" || e.key === "End") goTo(Infinity);
  else return;
  e.preventDefault();
});

// ---------- sound ----------

let audio;
function playSound(s, end = false) {
  try {
    audio = audio || new AudioContext();
    const capture = /x/.test(s.san[s.san.length - 1] || "");
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.type = end ? "triangle" : "sine";
    osc.frequency.value = end ? 440 : capture ? 300 : 520;
    gain.gain.setValueAtTime(0.18, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + (end ? 0.5 : 0.09));
    osc.connect(gain).connect(audio.destination);
    osc.start();
    osc.stop(audio.currentTime + (end ? 0.5 : 0.1));
  } catch { /* sound is optional */ }
}

connect();
