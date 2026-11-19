import { api, requireUser, renderTopbar, timeControlText, timeControlName, colorDot, escapeHtml } from "./common.js";

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

const COLOR_LABEL = { white: "białe", black: "czarne", random: "losowo" };

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
  const tbody = document.getElementById("open-games");
  if (!games.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty">Brak otwartych partii — utwórz własną!</td></tr>`;
    return;
  }
  tbody.innerHTML = games.map(g => `
    <tr>
      <td><b>${escapeHtml(g.creator)}</b>${g.mine ? ' <span class="muted">(Ty)</span>' : ""}</td>
      <td>${timeControlText(g.minutes, g.increment)} <span class="muted">${timeControlName(g.minutes, g.increment)}</span></td>
      <td>${colorDot(g.creatorColor)}${COLOR_LABEL[g.creatorColor]}</td>
      <td class="actions">
        ${g.mine
          ? `<a href="/game/${g.id}"><button class="small">Otwórz</button></a>
             <button class="small danger" data-cancel="${g.id}">Anuluj</button>`
          : `<button class="small primary" data-join="${g.id}">Dołącz</button>`}
      </td>
    </tr>`).join("");
  tbody.querySelectorAll("[data-join]").forEach(b => b.onclick = async () => {
    b.disabled = true;
    try {
      await api(`/api/games/${b.dataset.join}/join`, { method: "POST" });
      location.href = `/game/${b.dataset.join}`;
    } catch (e) {
      alert(e.message);
      refresh();
    }
  });
  tbody.querySelectorAll("[data-cancel]").forEach(b => b.onclick = async () => {
    b.disabled = true;
    try { await api(`/api/games/${b.dataset.cancel}/cancel`, { method: "POST" }); } catch (e) { alert(e.message); }
    refresh();
  });
}

function renderActive(games) {
  const card = document.getElementById("active-card");
  card.hidden = !games.length;
  document.getElementById("active-games").innerHTML = games.map(g => {
    const opponent = g.you === "white" ? g.black : g.white;
    return `<tr>
      <td>${colorDot(g.you)}vs <b>${escapeHtml(opponent)}</b></td>
      <td>${timeControlText(g.minutes, g.increment)}</td>
      <td class="muted">${g.moves} półruchów</td>
      <td class="actions"><a href="/game/${g.id}"><button class="small primary">Wróć do gry</button></a></td>
    </tr>`;
  }).join("");
}

refresh();
setInterval(refresh, 3000);
