"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { markGuess, decompose, isPlayableGuess } = require("../play/marks.js");

const CODE = { green: "G", yellow: "Y", blue: "B", grey: "X", "": "·" };

function compact(marks) {
  return marks.map((m) => (m == null ? "·" : CODE[m] || "?")).join("");
}

function assertMarks(guess, answer, expected, note) {
  const marks = markGuess(guess, answer);
  const got = compact(marks);
  assert.equal(
    got,
    expected,
    `${note || ""}\n  đoán  ${[...guess].join(" ")}\n  đáp   ${[...answer].join(" ")}\n  được  ${got}\n  muốn  ${expected}`
  );
}

test("xanh lá: đúng chữ + đúng dấu, đúng vị trí", () => {
  assertMarks("cà phê", "cà phê", "GG·GGG", "khớp hoàn toàn");
  assertMarks("bánh mì", "bánh mì", "GGGG·GG", "khớp hoàn toàn");
  assertMarks("cá ba", "cá ba", "GG·GG", "mọi ô đúng chỗ");
});

test("vàng: đúng chữ + đúng dấu, sai vị trí", () => {
  assertMarks("ba dc", "ab cd", "YY·YY", "đổi chỗ trong từng từ");
  assertMarks("ba má", "má ba", "YY·YY", "đổi hai từ, cùng spaceIndex");
  assertMarks("hac ba", "abc ha", "YYG·YG", "c và a đúng chỗ; h/b/a kia sai chỗ");
});

test("xanh dương: cùng nguyên âm gốc, sai dấu — cùng vị trí", () => {
  assertMarks("cà ba", "cá ba", "GB·GG", "à vs á cùng chỗ");
  assertMarks("cả phê", "cà phê", "GB·GGG", "ả vs à");
  assertMarks("cạ phê", "cà phê", "GB·GGG", "ạ vs à");
  assertMarks("cã phê", "cà phê", "GB·GGG", "ã vs à");
});

test("xanh dương: cùng nguyên âm gốc, sai dấu — khác vị trí", () => {
  assertMarks("xy cà", "cá xy", "YY·YB", "à khớp á ở chỗ khác");
  assertMarks("hà xy", "ha xy", "GB·GG", "à vs a (không dấu)");
});

test("xám: không có trong cụm từ", () => {
  assertMarks("cớ de", "cá ba", "GX·XX", "ớ/d/e không có");
  assertMarks("xy zt", "ab cd", "XX·XX", "không chữ nào trùng");
});

test("thứ tự ưu tiên: xanh lá > vàng > xanh dương > xám", () => {
  assertMarks("cá ca", "cá ba", "GG·XG", "c thứ hai không còn slot; a cuối đúng chỗ");
  assertMarks("àá xy", "áà xy", "YY·GG", "đúng chữ+dấu nhưng đổi chỗ → vàng, không phải xanh dương");
  assertMarks("cà ca", "cá ba", "GB·XG", "à xanh dương với á; c thừa xám; a cuối xanh lá");
});

test("a ă â là khác nhau; e≠ê, o≠ô≠ơ, u≠ư", () => {
  assertMarks("cắ xy", "cá xy", "GX·GG", "ắ (ă) không phải á (a)");
  assertMarks("câ xy", "cá xy", "GX·GG", "â không phải a");
  assertMarks("cê xy", "cé xy", "GX·GG", "ê không phải e");
  assertMarks("cô xy", "có xy", "GX·GG", "ô không phải o");
  assertMarks("cơ xy", "có xy", "GX·GG", "ơ không phải o");
  assertMarks("cư xy", "cú xy", "GX·GG", "ư không phải u");
  assertMarks("cắ xy", "cằ xy", "GB·GG", "cùng gốc ă, khác dấu → xanh dương");
  assertMarks("cố xy", "cồ xy", "GB·GG", "cùng gốc ô, khác dấu → xanh dương");
});

test("phụ âm không được tô xanh dương", () => {
  assertMarks("đi xa", "đi xa", "GG·GG", "đ khớp");
  assertMarks("di xa", "đi xa", "XG·GG", "d ≠ đ → xám, không xanh dương");
  assertMarks("kó ba", "có ba", "XG·GG", "k ≠ c");
});

test("ô cách luôn null; không tô màu", () => {
  const marks = markGuess("cà phê", "cà phê");
  assert.equal(marks[2], null);
  assert.equal(compact(marks)[2], "·");
});

test("mỗi chữ đáp án chỉ dùng một lần", () => {
  assertMarks("hà hà", "ha xy", "GB·XX", "một a/à trong đáp; à thứ hai xám");
  assertMarks("hà hà", "ha ha", "GB·GB", "hai a → hai xanh dương");
  assertMarks("ha ha", "hà hà", "GB·GB", "hai hà, đoán ha");
});

test("decompose khớp bảng dấu tiếng Việt", () => {
  assert.deepEqual(decompose("á"), { b: "a", t: "acute" });
  assert.deepEqual(decompose("à"), { b: "a", t: "grave" });
  assert.deepEqual(decompose("ả"), { b: "a", t: "hook" });
  assert.deepEqual(decompose("ã"), { b: "a", t: "tilde" });
  assert.deepEqual(decompose("ạ"), { b: "a", t: "dot" });
  assert.deepEqual(decompose("ă"), { b: "ă", t: "none" });
  assert.deepEqual(decompose("ắ"), { b: "ă", t: "acute" });
  assert.deepEqual(decompose("â"), { b: "â", t: "none" });
  assert.deepEqual(decompose("ế"), { b: "ê", t: "acute" });
  assert.deepEqual(decompose("ớ"), { b: "ơ", t: "acute" });
  assert.deepEqual(decompose("ự"), { b: "ư", t: "dot" });
  assert.deepEqual(decompose("đ"), { b: "đ", t: "none" });
});

test("chuỗi vô nghĩa vẫn đoán được nếu đúng khuôn ô", () => {
  assert.equal(isPlayableGuess("àáạ ăâê", "abc def"), true);
  assert.equal(isPlayableGuess("ae êôơ", "cà phê"), true);
  assert.equal(isPlayableGuess("cà phê", "cà phê"), true);
  assert.equal(isPlayableGuess("ca phe", "cà phê"), true, "bỏ dấu vẫn đúng khuôn");
  assert.equal(isPlayableGuess("àáạ ăâê", "cà phê"), false, "sai length / spaceIndex");
  assert.equal(isPlayableGuess("cà phê!", "cà phê"), false);
  assert.equal(isPlayableGuess("càphê", "cà phê"), false);
});

test("mò nguyên âm: guess vô nghĩa vẫn ra màu, không cần có trong kho", () => {
  assertMarks("ae êôơ", "cà phê", "BX·YXX", "a→à xanh dương; ê vàng; còn lại xám");
  assertMarks("àáạ ăâê", "abc def", "BXX·XXX", "à vs a xanh dương; các nguyên âm còn lại xám");
});
