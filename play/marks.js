"use strict";

const TONE = {
  "\u0301": "acute",
  "\u0300": "grave",
  "\u0309": "hook",
  "\u0303": "tilde",
  "\u0323": "dot"
};
const VOWEL_BASES = "aăâeêioôơuưy";
const VIET_LETTER_RE = /[a-zA-ZÀ-ỹ]/;

function decompose(ch) {
  const nfd = (ch || "").normalize("NFD");
  let tone = "none";
  let base = "";
  for (const c of nfd) {
    if (TONE[c]) tone = TONE[c];
    else base += c;
  }
  return { b: base.normalize("NFC").toLowerCase(), t: tone };
}

function markGuess(guess, answer) {
  guess = String(guess || "").normalize("NFC");
  answer = String(answer || "").normalize("NFC");
  const n = answer.length;
  const marks = Array(n).fill(null);
  const used = Array(n).fill(false);
  const isSpace = (i) => answer[i] === " ";

  for (let i = 0; i < n; i++) {
    if (isSpace(i)) continue;
    if (guess[i] === answer[i]) {
      marks[i] = "green";
      used[i] = true;
    }
  }
  for (let i = 0; i < n; i++) {
    if (isSpace(i) || marks[i]) continue;
    for (let j = 0; j < n; j++) {
      if (used[j] || isSpace(j)) continue;
      if (guess[i] === answer[j]) {
        marks[i] = "yellow";
        used[j] = true;
        break;
      }
    }
  }
  for (let i = 0; i < n; i++) {
    if (isSpace(i) || marks[i]) continue;
    const g = decompose(guess[i]);
    if (!VOWEL_BASES.includes(g.b)) continue;
    for (let j = 0; j < n; j++) {
      if (used[j] || isSpace(j)) continue;
      const a = decompose(answer[j]);
      if (g.b === a.b && g.t !== a.t) {
        marks[i] = "blue";
        used[j] = true;
        break;
      }
    }
  }
  for (let i = 0; i < n; i++) {
    if (isSpace(i)) marks[i] = null;
    else if (!marks[i]) marks[i] = "grey";
  }
  return marks;
}

function isPlayableGuess(guess, answer) {
  guess = String(guess || "").normalize("NFC");
  answer = String(answer || "").normalize("NFC");
  if (guess.length !== answer.length) return false;
  const space = answer.indexOf(" ");
  if (space < 0 || guess.indexOf(" ") !== space) return false;
  for (let i = 0; i < answer.length; i++) {
    if (i === space) {
      if (guess[i] !== " ") return false;
      continue;
    }
    if (guess[i] === " " || !VIET_LETTER_RE.test(guess[i])) return false;
  }
  return true;
}

const api = { decompose, markGuess, isPlayableGuess, TONE, VOWEL_BASES };
if (typeof module === "object" && module.exports) {
  module.exports = api;
}
if (typeof globalThis !== "undefined") {
  globalThis.DOANCHU_MARK = api;
}
