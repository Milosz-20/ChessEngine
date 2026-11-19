import { api, requireUser, renderTopbar, timeControlText, timeControlName, colorDot, escapeHtml, toast } from "./common.js";

const TIME_CONTROLS = [
  [1, 0], [2, 1], [3, 0],
  [3, 2], [5, 0], [5, 3],
  [10, 0], [10, 5], [15, 10],
  [30, 0], [30, 20], [60, 30],
];

const user = await requireUser();
renderTopbar(user, "play");

let selectedTc = [5, 3];
let selectedColor = "random";

const grid = document.getElementById("tc-grid");
for (const [m, inc] of TIME_CONTROLS) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.innerHTML = `<span class="tc">${timeControlText(m, inc)}</span><span class="tc-name">${timeControlName(m, inc)}</span>`;
  if (m === selectedTc[0] && inc === selectedTc[1]) btn.classList.add("selected");
  btn.onclick = () => {
    selectedTc = [m, inc];
    grid.querySelectorAll("button").forEach(b => b.classList.toggle("selected", b === btn));
  };
  grid.appendChild(btn);
}

document.querySelectorAll("#color-pick button").forEach(btn => {
  btn.onclick = () => {
    selectedColor = btn.dataset.color;
    document.querySelectorAll("#color-pick button").forEach(b => b.classList.toggle("selected", b === btn));
  };
});

document.getElementById("create").onclick = async e => {
  const err = document.getElementById("create-error");
  err.textContent = "";
  e.target.disabled = true;
  try {
    const { id } = await api("/api/games", {
      method: "POST",
      body: { minutes: selectedTc[0], increment: selectedTc[1], color: selectedColor },
    });
    location.href = `/game/${id}`;
  } catch (ex) {
    err.textContent = ex.message;
    e.target.disabled = false;
  }
};

const COLOR_LABEL = { white: "gra białymi", black: "gra czarnymi", random: "kolor losowy" };

async function refresh() {
  try {
    const [open, mine] = await Promise.all([api("/api/games/open"), api("/api/my-games")]);
    renderOpen(open);
    renderActive(mine.active);
  } catch (e) {
    if (e.status === 401) location.href = "/login";
  }
}

function renderOpen(games) {
  const box = document.getElementById("open-games");
  if (!games.length) {
    box.innerHTML = `<div class="list-empty">Nikt teraz nie czeka na grę. Utwórz własną partię.</div>`;
    return;
  }
  box.innerHTML = games.map(g => `
    <div class="list-row">
      <span class="name">${escapeHtml(g.creator)}${g.mine ? ' <span class="muted">· Ty</span>' : ""}</span>
      <span class="mono muted">${timeControlText(g.minutes, g.increment)} <span style="font-family:var(--font)">${timeControlName(g.minutes, g.increment).toLowerCase()}</span></span>
      <span class="muted">${colorDot(g.creatorColor)}${COLOR_LABEL[g.creatorColor]}</span>
      <span class="actions">
        ${g.mine
          ? `<a href="/game/${g.id}">Otwórz</a><button class="link" data-cancel="${g.id}">Anuluj</button>`
          : `<button class="link accent" data-join="${g.id}">Dołącz</button>`}
      </span>
    </div>`).join("");
  box.querySelectorAll("[data-join]").forEach(b => b.onclick = async () => {
    b.disabled = true;
    try {
      await api(`/api/games/${b.dataset.join}/join`, { method: "POST" });
      location.href = `/game/${b.dataset.join}`;
    } catch (e) {
      toast(e.message);
      refresh();
    }
  });
  box.querySelectorAll("[data-cancel]").forEach(b => b.onclick = async () => {
    b.disabled = true;
    try { await api(`/api/games/${b.dataset.cancel}/cancel`, { method: "POST" }); } catch (e) { toast(e.message); }
    refresh();
  });
}

function renderActive(games) {
  document.getElementById("active-section").hidden = !games.length;
  document.getElementById("active-games").innerHTML = games.map(g => {
    const opponent = g.you === "white" ? g.black : g.white;
    return `<div class="list-row">
      <span class="name">${colorDot(g.you)}${escapeHtml(opponent)}</span>
      <span class="mono muted">${timeControlText(g.minutes, g.increment)}</span>
      <span class="muted">ruch ${Math.floor(g.moves / 2) + 1}</span>
      <span class="actions"><a href="/game/${g.id}">Wróć do gry</a></span>
    </div>`;
  }).join("");
}

refresh();
setInterval(refresh, 3000);
