import { api, requireUser, renderTopbar, TERMINATION, outcomeFor, timeControlText, colorDot,
         formatDate, escapeHtml, plural } from "./common.js";

const user = await requireUser();
renderTopbar(user, "history");

const { finished } = await api("/api/my-games");
const box = document.getElementById("games");
const LABEL = { win: "Wygrana", loss: "Przegrana", draw: "Remis" };

const counts = { win: 0, loss: 0, draw: 0 };
finished.forEach(g => counts[outcomeFor(g.result, g.you)]++);
const n = finished.length;
document.getElementById("summary").textContent = n
  ? `${n} ${plural(n, "partia", "partie", "partii")} · ${counts.win} ${plural(counts.win, "wygrana", "wygrane", "wygranych")} · ` +
    `${counts.draw} ${plural(counts.draw, "remis", "remisy", "remisów")} · ${counts.loss} ${plural(counts.loss, "przegrana", "przegrane", "przegranych")}`
  : "";

if (!n) {
  box.innerHTML = `<div class="list-empty">Nie masz jeszcze zakończonych partii. <a href="/">Zagraj pierwszą</a></div>`;
} else {
  box.innerHTML = finished.map(g => {
    const outcome = outcomeFor(g.result, g.you);
    const opponent = g.you === "white" ? g.black : g.white;
    const fullMoves = Math.ceil(g.moves / 2);
    return `<div class="list-row history-row">
      <span class="name">${colorDot(g.you)}${escapeHtml(opponent)}<small class="muted" style="display:block;font-weight:400;font-size:12px">${formatDate(g.finishedAt)}</small></span>
      <span><span class="tag ${outcome}">${LABEL[outcome]}</span></span>
      <span class="muted">${TERMINATION[g.termination] || ""} · ${fullMoves} ${plural(fullMoves, "ruch", "ruchy", "ruchów")}</span>
      <span class="mono muted">${timeControlText(g.minutes, g.increment)}</span>
      <span class="actions"><a href="/game/${g.id}">Przeglądaj</a><a href="/api/games/${g.id}/pgn">PGN</a></span>
    </div>`;
  }).join("");
}
