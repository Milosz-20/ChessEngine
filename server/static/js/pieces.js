// Chess pieces as SVG: a simplified, modern take on the classic Staunton silhouettes.
//
// Every piece is built from the same parts: a foot, a collar ring and a concave body, topped
// by the piece's head. It is drawn twice - an outline layer (stroked) under a fill layer - so
// only the outer contour of the union is visible and overlapping parts never show seams.
// "det" paths are fine inner lines; they always stop well inside the silhouette so they never
// touch or cross the outline.

const FOOT = "M27 90 H73 Q77 90 77 86.5 Q77 83 73 83 H27 Q23 83 23 86.5 Q23 90 27 90 Z " +
             "M33 83 Q33 78.5 37 78.5 H63 Q67 78.5 67 83 Z";
const SMALL_FOOT = "M31 90 H69 Q73 90 73 86.8 Q73 83.6 69 83.6 H31 Q27 83.6 27 86.8 Q27 90 31 90 Z " +
                   "M36 83.6 Q36 79.6 40 79.6 H60 Q64 79.6 64 83.6 Z";

// Concave body rising from the foot ring to a waist, finished with a thin collar disc
const body = (waistTop, waistHalf, collarY, collarHalf) =>
  `M37.5 79 C${42 - waistHalf / 3} 71 ${50 - waistHalf} ${waistTop + 8} ${50 - waistHalf} ${waistTop} ` +
  `H${50 + waistHalf} C${50 + waistHalf} ${waistTop + 8} ${58 + waistHalf / 3} 71 62.5 79 Z ` +
  `M${50 - collarHalf} ${collarY + 2.4} Q${50 - collarHalf} ${collarY} ${50 - collarHalf + 2.4} ${collarY} ` +
  `H${50 + collarHalf - 2.4} Q${50 + collarHalf} ${collarY} ${50 + collarHalf} ${collarY + 2.4} ` +
  `Q${50 + collarHalf} ${collarY + 4.8} ${50 + collarHalf - 2.4} ${collarY + 4.8} ` +
  `H${50 - collarHalf + 2.4} Q${50 - collarHalf} ${collarY + 4.8} ${50 - collarHalf} ${collarY + 2.4} Z`;

const FOOT_LINE = `<path class="det" d="M39 83 H61"/>`;

const SHAPES = {
  p: `<path class="body" d="${SMALL_FOOT}
        M39.5 79.6 C43 73 45 66 45.2 58 H54.8 C55 66 57 73 60.5 79.6 Z
        M39 55.6 Q39 53.2 41.4 53.2 H58.6 Q61 53.2 61 55.6 Q61 58 58.6 58 H41.4 Q39 58 39 55.6 Z
        M50 33.5 a10.5 10.5 0 1 1 -0.01 0 Z"/>
      <path class="det" d="M42 83.6 H58"/>`,

  r: `<path class="body" d="${FOOT} ${body(46, 9.5, 41.5, 15)}
        M33 22 H40 V27.5 H46.5 V22 H53.5 V27.5 H60 V22 H67 V39 Q67 43 63.5 43 H36.5 Q33 43 33 39 Z"/>
      ${FOOT_LINE}<path class="det" d="M39 34.5 H61"/>`,

  b: `<path class="body" d="${FOOT} ${body(57, 6, 53, 12.5)}
        M50 20 C60 28 63 37 60.5 44.5 C59 49.5 55.5 53 50 55 C44.5 53 41 49.5 39.5 44.5 C37 37 40 28 50 20 Z
        M50 12.2 a4.4 4.4 0 1 1 -0.01 0 Z"/>
      ${FOOT_LINE}<path class="det" d="M54 31 L47.5 40"/>`,

  n: `<path class="body" d="${FOOT}
        M37 79 C36 70 38.5 63.5 45 58.5 C39 57.5 32.5 55.5 28.5 51.5 C25.8 48.8 25.6 45 28 42.6
        L38.6 32.2 C40.2 27 41.2 22.4 43.4 17.8 L47.6 23 C59.5 23.6 68.5 33.5 69.5 47 C70.4 59.5 67.5 70 64 79 Z"/>
      ${FOOT_LINE}<path class="det" d="M30.5 47.6 L34 48.4"/><path class="det" d="M59 32.5 C62.8 37 64.3 42.5 64 48.5"/>
      <circle class="eye" cx="42" cy="36" r="2.4"/>`,

  q: `<path class="body" d="${FOOT} ${body(59, 7, 55, 13)}
        M42.5 57 C40 47.5 35.5 40 30 32.5 L39.6 37.5 L41 26.5 L46.6 36.2 L50 23.5 L53.4 36.2 L59 26.5 L60.4 37.5
        L70 32.5 C64.5 40 60 47.5 57.5 57 Z
        M30 26.6 a3.2 3.2 0 1 1 -0.01 0 Z M41 20.6 a3.2 3.2 0 1 1 -0.01 0 Z M50 17 a3.6 3.6 0 1 1 -0.01 0 Z
        M59 20.6 a3.2 3.2 0 1 1 -0.01 0 Z M70 26.6 a3.2 3.2 0 1 1 -0.01 0 Z"/>
      ${FOOT_LINE}<path class="det" d="M44.5 48 H55.5"/>`,

  k: `<path class="body" d="${FOOT} ${body(59, 7, 55, 13)}
        M43 57 C39.5 49 33.5 43 32.5 37 C31.8 32.6 39 30.2 50 30.2 C61 30.2 68.2 32.6 67.5 37
        C66.5 43 60.5 49 57 57 Z
        M47.6 9 H52.4 V14.6 H57.6 V19.4 H52.4 V33 H47.6 V19.4 H42.4 V14.6 H47.6 Z"/>
      ${FOOT_LINE}<path class="det" d="M43 47 H57"/>`,
};

export const PIECE_NAMES = { k: "Król", q: "Hetman", r: "Wieża", b: "Goniec", n: "Skoczek", p: "Pion" };

// piece = "wk", "bp", ...
export function pieceSvg(piece) {
  const shape = SHAPES[piece[1]];
  const color = piece[0] === "w" ? "white" : "black";
  return `<svg class="piece-svg ${color}" viewBox="0 0 100 100" aria-hidden="true">` +
         `<g class="ol">${shape}</g><g class="fl">${shape}</g></svg>`;
}

// The site logo: the knight in the accent colour.
export function logoSvg() {
  return `<svg viewBox="0 0 100 100" aria-hidden="true" class="logo-svg">${SHAPES.n}</svg>`;
}
