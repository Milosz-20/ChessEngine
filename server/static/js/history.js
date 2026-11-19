import { api, requireUser, renderTopbar, TERMINATION, outcomeFor, timeControlText, colorDot,
         formatDate, escapeHtml } from "./common.js";

const user = await requireUser();
renderTopbar(user, "history");

const { finished } = await api("/api/my-games");
const tbody = document.getElementById("games");
const LABEL = { win: "Wygrana", loss: "Przegrana", draw: "Remis" };

const counts = { win: 0, loss: 0, draw: 0 };
finished.forEach(g => counts[outcomeFor(g.result, g.you)]++);
document.getElementById("summary").textContent = finished.length
  ? `${finished.length} partii · ${counts.win} wygranych · ${counts.draw} remisów · ${counts.loss} przegranych`
  : "";

if (!finished.length) {
  tbody.innerHTML = `<tr><td colspan="8" class="empty">Nie masz jeszcze zakończonych partii. <a href="/">Zagraj pierwszą!</a></td></tr>`;
} else {
  tbody.innerHTML = finished.map(g => {
    const outcome = outcomeFor(g.result, g.you);
    const opponent = g.you === "white" ? g.black : g.white;
    return `<tr>
      <td class="muted">${formatDate(g.finishedAt)}</td>
      <td><b>${escapeHtml(opponent)}</b></td>
      <td>${colorDot(g.you)}${g.you === "white" ? "białe" : "czarne"}</td>
      <td><span class="badge ${outcome}">${LABEL[outcome]}</span> <span class="muted">${g.result}</span></td>
      <td>${TERMINATION[g.termination] || ""}</td>
      <td>${Math.ceil(g.moves / 2)}</td>
      <td>${timeControlText(g.minutes, g.increment)}</td>
      <td class="actions">
        <a href="/game/${g.id}"><button class="small">Przeglądaj</button></a>
        <a href="/api/games/${g.id}/pgn"><button class="small">PGN</button></a>
      </td>
    </tr>`;
  }).join("");
}
