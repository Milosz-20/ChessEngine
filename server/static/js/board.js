// Interactive chessboard. It only draws and collects the player's intent; whether a move is
// legal is decided by the server, which sends the list of legal moves (UCI strings).

import { pieceSvg, PIECE_NAMES } from "./pieces.js";

const FILES = "abcdefgh";
export function squareName(file, rank) { return FILES[file] + (rank + 1); }

export function parseFen(fen) {
  // { "e1": "wk", ... }
  const pieces = {};
  const rows = fen.split(" ")[0].split("/");
  rows.forEach((row, i) => {
    const rank = 7 - i;
    let file = 0;
    for (const ch of row) {
      if (/\d/.test(ch)) { file += Number(ch); continue; }
      const color = ch === ch.toUpperCase() ? "w" : "b";
      pieces[squareName(file, rank)] = color + ch.toLowerCase();
      file++;
    }
  });
  return pieces;
}

export function pieceHtml(piece) {
  return `<div class="piece">${pieceSvg(piece)}</div>`;
}

export class Board {
  constructor(el, { onMove, onPremove } = {}) {
    this.el = el;
    this.el.classList.add("board");
    this.onMove = onMove || (() => {});
    this.onPremove = onPremove || (() => {});
    this.premovable = false;   // opponent's turn: own pieces can be picked to queue a premove
    this.myColor = null;       // "w" / "b"
    this.premove = null;       // queued premove, e.g. "e2e4"
    this.orientation = "white";
    this.pieces = {};
    this.legal = [];
    this.lastMove = null;
    this.check = null;
    this.interactive = false;
    this.selected = null;
    this.drag = null;
    this.squares = {};
    this._build();
    this._bindPointer();
    new ResizeObserver(() => this._resize()).observe(this.el);
  }

  _build() {
    this.el.innerHTML = "";
    this.squares = {};
    for (let row = 0; row < 8; row++) {
      for (let col = 0; col < 8; col++) {
        const rank = this.orientation === "white" ? 7 - row : row;
        const file = this.orientation === "white" ? col : 7 - col;
        const name = squareName(file, rank);
        const sq = document.createElement("div");
        sq.className = "sq " + ((file + rank) % 2 === 0 ? "dark" : "light");
        sq.dataset.square = name;
        if (col === 0) sq.insertAdjacentHTML("beforeend", `<span class="coord rank">${rank + 1}</span>`);
        if (row === 7) sq.insertAdjacentHTML("beforeend", `<span class="coord file">${FILES[file]}</span>`);
        this.el.appendChild(sq);
        this.squares[name] = sq;
      }
    }
  }

  _resize() {
    this.squareSize = this.el.clientWidth / 8;
  }

  setOrientation(color) {
    if (color === this.orientation) return;
    this.orientation = color;
    this._build();
    this.render();
  }

  setState({ fen, legal = [], lastMove = null, check = null, interactive = false,
              premovable = false, myColor = null, premove = null }) {
    this.pieces = parseFen(fen);
    this.legal = legal;
    this.lastMove = lastMove;
    this.check = check;
    this.interactive = interactive;
    this.premovable = premovable && !interactive;
    this.myColor = myColor;
    this.premove = premove;
    if (this.selected && !this._targetsFrom(this.selected).length) this.selected = null;
    this._closePromotion();
    this.render();
  }

  render() {
    this.el.classList.toggle("interactive", this.interactive || this.premovable);
    const preFrom = this.premove && this.premove.slice(0, 2);
    const preTo = this.premove && this.premove.slice(2, 4);
    const targets = this.selected ? this._targetsFrom(this.selected) : [];
    const lastFrom = this.lastMove && this.lastMove.slice(0, 2);
    const lastTo = this.lastMove && this.lastMove.slice(2, 4);
    for (const [name, sq] of Object.entries(this.squares)) {
      const piece = this.pieces[name];
      const existing = sq.querySelector(".piece");
      if (existing) existing.remove();
      if (piece) sq.insertAdjacentHTML("beforeend", pieceHtml(piece));
      sq.classList.toggle("last", name === lastFrom || name === lastTo);
      sq.classList.toggle("selected", name === this.selected);
      sq.classList.toggle("target", targets.includes(name));
      sq.classList.toggle("capture", targets.includes(name) && !!piece);
      sq.classList.toggle("premove", name === preFrom || name === preTo);
      sq.classList.toggle("movable", this._targetsFrom(name).length > 0);
    }
  }

  _targetsFrom(square) {
    if (this.interactive) {
      const out = new Set();
      for (const m of this.legal) if (m.startsWith(square)) out.add(m.slice(2, 4));
      return [...out];
    }
    if (this.premovable) return this._premoveTargets(square);
    return [];
  }

  // Squares a piece could go to on our next turn, judged by how it moves and ignoring
  // what the opponent may do (their pieces might move away, so sliders pass through them).
  _premoveTargets(square) {
    const piece = this.pieces[square];
    if (!piece || piece[0] !== this.myColor) return [];
    const f0 = FILES.indexOf(square[0]), r0 = Number(square[1]) - 1;
    const own = (f, r) => { const p = this.pieces[squareName(f, r)]; return p && p[0] === this.myColor; };
    const on = (f, r) => f >= 0 && f < 8 && r >= 0 && r < 8;
    const out = [];
    const add = (f, r) => { if (on(f, r) && !own(f, r)) out.push(squareName(f, r)); };
    const ray = (df, dr) => {
      for (let f = f0 + df, r = r0 + dr; on(f, r) && !own(f, r); f += df, r += dr) out.push(squareName(f, r));
    };
    const type = piece[1];
    if (type === "n") {
      for (const [df, dr] of [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]]) add(f0 + df, r0 + dr);
    } else if (type === "k") {
      for (let df = -1; df <= 1; df++) for (let dr = -1; dr <= 1; dr++) if (df || dr) add(f0 + df, r0 + dr);
      const home = this.myColor === "w" ? 0 : 7;
      if (f0 === 4 && r0 === home) { add(6, home); add(2, home); }
    } else if (type === "p") {
      const dir = this.myColor === "w" ? 1 : -1;
      add(f0, r0 + dir);
      if (r0 === (this.myColor === "w" ? 1 : 6) && !own(f0, r0 + dir)) add(f0, r0 + 2 * dir);
      add(f0 - 1, r0 + dir);
      add(f0 + 1, r0 + dir);
    } else {
      const dirs = [];
      if (type !== "b") dirs.push([1, 0], [-1, 0], [0, 1], [0, -1]);
      if (type !== "r") dirs.push([1, 1], [1, -1], [-1, 1], [-1, -1]);
      for (const [df, dr] of dirs) ray(df, dr);
    }
    return out;
  }

  // Briefly light up the king that is in check (shown only after an illegal attempt)
  _flashCheck() {
    const sq = this.squares[this.check];
    if (!sq) return;
    sq.classList.remove("check-flash");
    void sq.offsetWidth;            // restart the animation if it is already running
    sq.classList.add("check-flash");
    clearTimeout(this._flashTimer);
    this._flashTimer = setTimeout(() => sq.classList.remove("check-flash"), 850);
  }

  _setPremove(uci) {
    this.premove = uci;
    this.selected = null;
    this.render();
    this.onPremove(uci);
  }

  _squareAt(x, y) {
    const el = document.elementFromPoint(x, y);
    const sq = el && el.closest && el.closest(".sq");
    return sq && this.el.contains(sq) ? sq.dataset.square : null;
  }

  _bindPointer() {
    this.el.addEventListener("pointerdown", e => this._down(e));
    window.addEventListener("pointermove", e => this._move(e));
    window.addEventListener("pointerup", e => this._up(e));
    this.el.addEventListener("contextmenu", e => {
      e.preventDefault();
      if (this.premove || this.selected) { this.selected = null; this._setPremove(null); }
    });
  }

  _down(e) {
    if (e.button !== 0 || this.promotion) return;
    const square = this._squareAt(e.clientX, e.clientY);
    if (!square) return;

    // Second click of a click-click move
    if (this.selected && this._targetsFrom(this.selected).includes(square)) {
      this._attempt(this.selected, square);
      return;
    }
    // In check, trying a piece that can't move, or a square the selected piece can't reach,
    // is an illegal attempt: point at the king.
    const piece = this.pieces[square];
    const ownPiece = piece && piece[0] === this.myColor;
    if (this.interactive && this.check && square !== this.selected &&
        ((ownPiece && !this._targetsFrom(square).length) || (this.selected && !ownPiece))) {
      this._flashCheck();
    }
    if (this._targetsFrom(square).length) {
      this.selected = square;
      this.render();
      // start dragging
      const ghost = this.squares[square].querySelector(".piece").cloneNode(true);
      ghost.classList.add("dragging");
      ghost.style.width = ghost.style.height = `${this.squareSize}px`;
      ghost.style.left = `${e.clientX}px`;
      ghost.style.top = `${e.clientY}px`;
      document.body.appendChild(ghost);
      this.squares[square].classList.add("drag-origin");
      this.drag = { from: square, ghost, hover: null };
      e.preventDefault();
    } else if (this.selected || this.premove) {
      // clicking anywhere else cancels the selection and any queued premove
      this.selected = null;
      if (this.premove) this._setPremove(null); else this.render();
    }
  }

  _move(e) {
    if (!this.drag) return;
    this.drag.ghost.style.left = `${e.clientX}px`;
    this.drag.ghost.style.top = `${e.clientY}px`;
    const sq = this._squareAt(e.clientX, e.clientY);
    if (sq !== this.drag.hover) {
      if (this.drag.hover) this.squares[this.drag.hover].classList.remove("hover");
      if (sq && this._targetsFrom(this.drag.from).includes(sq)) this.squares[sq].classList.add("hover");
      this.drag.hover = sq;
    }
  }

  _up(e) {
    if (!this.drag) return;
    const { from, ghost, hover } = this.drag;
    ghost.remove();
    this.squares[from].classList.remove("drag-origin");
    if (hover) this.squares[hover].classList.remove("hover");
    this.drag = null;
    const to = this._squareAt(e.clientX, e.clientY);
    if (to && to !== from && this._targetsFrom(from).includes(to)) {
      this._attempt(from, to);
    } else if (to && to !== from && this.interactive && this.check) {
      this._flashCheck();
    }
    // dropping back on the origin keeps it selected for a click-click move
  }

  _attempt(from, to) {
    if (!this.interactive && this.premovable) {
      const piece = this.pieces[from];
      const lastRank = this.myColor === "w" ? "8" : "1";
      this._setPremove(from + to + (piece && piece[1] === "p" && to[1] === lastRank ? "q" : ""));
      return;
    }
    const base = from + to;
    const options = this.legal.filter(m => m.startsWith(base));
    if (!options.length) return;
    if (options.length > 1) {
      this._askPromotion(from, to);
      return;
    }
    this._play(options[0]);
  }

  _play(uci) {
    this.selected = null;
    this._applyLocally(uci);
    this.interactive = false;
    this.legal = [];
    this.render();
    this.onMove(uci);
  }

  // Show the move immediately; the server's answer replaces this position anyway.
  _applyLocally(uci) {
    const from = uci.slice(0, 2), to = uci.slice(2, 4), promo = uci[4];
    const piece = this.pieces[from];
    if (!piece) return;
    delete this.pieces[from];
    if (piece[1] === "p" && from[0] !== to[0] && !this.pieces[to]) {
      delete this.pieces[to[0] + from[1]]; // en passant
    }
    if (piece[1] === "k" && Math.abs(FILES.indexOf(from[0]) - FILES.indexOf(to[0])) === 2) {
      const rank = from[1];
      const [rf, rt] = to[0] === "g" ? ["h", "f"] : ["a", "d"];
      this.pieces[rt + rank] = this.pieces[rf + rank];
      delete this.pieces[rf + rank];
    }
    this.pieces[to] = promo ? piece[0] + promo : piece;
    this.lastMove = uci;
    this.check = null;
  }

  _askPromotion(from, to) {
    const color = this.pieces[from][0];
    const backdrop = document.createElement("div");
    backdrop.className = "promo-backdrop";
    const box = document.createElement("div");
    box.className = "promo";
    const sqEl = this.squares[to];
    const boardRect = this.el.getBoundingClientRect();
    const rect = sqEl.getBoundingClientRect();
    const fromTop = rect.top - boardRect.top < boardRect.height / 2;
    box.style.left = `${rect.left - boardRect.left}px`;
    box.style.width = `${rect.width}px`;
    if (fromTop) box.style.top = "0px"; else box.style.bottom = "0px";
    const order = fromTop ? ["q", "n", "r", "b"] : ["b", "r", "n", "q"];
    for (const p of order) {
      const btn = document.createElement("button");
      btn.style.width = btn.style.height = `${rect.width}px`;
      btn.title = PIECE_NAMES[p];
      btn.dataset.piece = p;
      btn.innerHTML = pieceHtml(color + p);
      btn.onclick = ev => { ev.stopPropagation(); this._closePromotion(); this._play(from + to + p); };
      box.appendChild(btn);
    }
    backdrop.addEventListener("pointerdown", ev => {
      ev.stopPropagation();
      this._closePromotion();
      this.selected = null;
      this.render();
    });
    box.addEventListener("pointerdown", ev => ev.stopPropagation());
    this.el.appendChild(backdrop);
    this.el.appendChild(box);
    this.promotion = { backdrop, box };
  }

  _closePromotion() {
    if (!this.promotion) return;
    this.promotion.backdrop.remove();
    this.promotion.box.remove();
    this.promotion = null;
  }
}
