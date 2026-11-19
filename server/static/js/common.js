// Shared helpers for every page: API calls, the top bar, labels, small UI bits.
import { logoSvg } from "./pieces.js";

export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    const err = new Error((data && data.detail) || `Błąd ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

// Returns the logged-in user. Visitors without an account are sent to the login page, or -
// with guestPrompt - offered to play straight away as a guest.
export async function requireUser({ guestPrompt = false } = {}) {
  try {
    return await api("/api/me");
  } catch (e) {
    if (e.status !== 401) throw e;
    if (guestPrompt) return askGuest();
    location.href = "/login?next=" + encodeURIComponent(location.pathname);
    return new Promise(() => {}); // never resolves, page is leaving
  }
}

function askGuest() {
  const main = document.querySelector("main");
  const content = [...main.children];
  content.forEach(el => el.style.display = "none");  // [hidden] loses to display: grid
  const next = encodeURIComponent(location.pathname);
  const box = document.createElement("div");
  box.className = "auth";
  box.innerHTML = `
    <div class="brand-big">${logoSvg()}<h1>Zaproszenie do partii</h1>
      <div class="muted">Zagraj od razu jako gość albo zaloguj się na swoje konto.</div></div>
    <button class="primary block" id="guest-play">Graj jako gość</button>
    <div class="error-text" id="guest-error"></div>
    <div class="guest-alt">Masz konto? <a href="/login?next=${next}">Zaloguj się</a></div>`;
  main.prepend(box);
  return new Promise(resolve => {
    box.querySelector("#guest-play").onclick = async ev => {
      ev.target.disabled = true;
      try {
        const user = await api("/api/guest", { method: "POST" });
        box.remove();
        content.forEach(el => el.style.display = "");
        resolve(user);
      } catch (err) {
        box.querySelector("#guest-error").textContent = err.message;
        ev.target.disabled = false;
      }
    };
  });
}

export function renderTopbar(user, active) {
  const bar = document.createElement("header");
  bar.className = "topbar";
  bar.innerHTML = `
    <a class="brand" href="/">${logoSvg()}Szachy</a>
    <nav>
      <a href="/" class="${active === "play" ? "active" : ""}">Graj</a>
      <a href="/history" class="${active === "history" ? "active" : ""}">Historia</a>
    </nav>
    <div class="spacer"></div>
    <div class="user"></div>`;
  if (user) {
    const u = bar.querySelector(".user");
    u.innerHTML = user.guest
      ? `<span class="who"><b></b> <span class="muted">· gość</span></span><a href="/login">Załóż konto</a>`
      : `<span class="who"><b></b></span><button class="link" id="logout">Wyloguj</button>`;
    u.querySelector("b").textContent = user.username;
    if (user.guest) { document.body.prepend(bar); return; }
    u.querySelector("#logout").onclick = async () => {
      await api("/api/logout", { method: "POST" });
      location.href = "/login";
    };
  }
  document.body.prepend(bar);
}

export const TERMINATION = {
  checkmate: "mat",
  resign: "poddanie",
  timeout: "przekroczenie czasu",
  timeout_vs_insufficient: "czas, ale brak materiału do mata",
  stalemate: "pat",
  repetition: "trzykrotne powtórzenie pozycji",
  fifty_moves: "zasada 50 ruchów",
  insufficient_material: "niewystarczający materiał",
  agreement: "za porozumieniem",
};

export function resultText(result) {
  if (result === "1-0") return "Wygrały białe";
  if (result === "0-1") return "Wygrały czarne";
  if (result === "1/2-1/2") return "Remis";
  return "";
}

export function outcomeFor(result, you) {
  if (result === "1/2-1/2") return "draw";
  if ((result === "1-0" && you === "white") || (result === "0-1" && you === "black")) return "win";
  return "loss";
}

export function timeControlText(minutes, increment) {
  const m = minutes === 0.5 ? "½" : String(minutes);
  return `${m}+${increment}`;
}

export function timeControlName(minutes, increment) {
  const total = minutes * 60 + increment * 40; // estimated game length, like most servers
  if (total < 180) return "Bullet";
  if (total < 480) return "Blitz";
  if (total < 1500) return "Rapid";
  return "Klasyczne";
}

// Polish plural: plural(5, "partia", "partie", "partii")
export function plural(n, one, few, many) {
  if (n === 1) return one;
  const d = n % 10, dd = n % 100;
  if (d >= 2 && d <= 4 && !(dd >= 12 && dd <= 14)) return few;
  return many;
}

export function colorDot(color) {
  return `<span class="dot-color ${color}"></span>`;
}

export function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
}

let toastTimer;
export function toast(message) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}

export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
