// Autoteste do estilo.js: node teste.js (sai com erro se algo quebrar)
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const ES = require("./estilo.js");

// 1. forma fechada = integração numérica (RK4) do oscilador amortecido
function rk4(z, w, e0, v0, T, dt = 1e-4) {
  let e = e0, v = v0;
  const f = (e, v) => [v, -2 * z * w * v - w * w * e];
  for (let t = 0; t < T - 1e-12; t += dt) {
    const [a1, b1] = f(e, v), [a2, b2] = f(e + a1 * dt / 2, v + b1 * dt / 2), [a3, b3] = f(e + a2 * dt / 2, v + b2 * dt / 2), [a4, b4] = f(e + a3 * dt, v + b3 * dt);
    e += dt / 6 * (a1 + 2 * a2 + 2 * a3 + a4); v += dt / 6 * (b1 + 2 * b2 + 2 * b3 + b4);
  }
  return [e, v];
}
for (const [z, w, e0, v0] of [[0.62, 19.2, 1, 0], [1, 39, 1, 0], [1.22, 20, 1, 0], [1.94, 13.7, 1, -13.5], [0.3, 10, -2, 5], [1.57, 37.9, 0, 3]]) {
  for (const T of [0.05, 0.13, 0.4]) {
    const [a, av] = ES.molaErro(T, e0, v0, z, w), [b, bv] = rk4(z, w, e0, v0, T);
    assert(Math.abs(a - b) < 1e-5 && Math.abs(av - bv) < 1e-3, `molaErro z${z} w${w} T${T}: ${a} vs ${b}`);
  }
}

// 2. números dos presets (os mesmos do ESTILO.md)
const near = (a, b, tol, msg) => assert(Math.abs(a - b) <= tol, `${msg}: ${a} (esperado ${b})`);
near(ES.assenta("suave"), 0.406, 0.01, "assenta suave");
near(ES.assenta("firme"), 0.297, 0.01, "assenta firme");
near(ES.assenta("elastica"), 0.311, 0.01, "assenta elastica");
near(ES.overshoot("elastica"), 0.084, 0.005, "overshoot elastica");
assert(ES.overshoot("suave") < 1e-6 && ES.overshoot("firme") < 1e-6, "suave e firme sem overshoot");

// 3. cadeia: valor e velocidade contínuos quando o alvo muda no meio do caminho
const ch = [[0, 0], [0.1, 100, "suave"], [0.25, 40, "elastica"]];
const [xa, va] = ES.cadeia(0.25 - 1e-7, ch, "suave", true), [xb, vb] = ES.cadeia(0.25 + 1e-7, ch, "suave", true);
assert(Math.abs(xa - xb) < 1e-3 && Math.abs(va - vb) < 0.5, `cadeia descontínua: ${xa}/${xb} ${va}/${vb}`);
// mola própria sem u0 sai do repouso (o teste cego B3 tropeçou num NaN silencioso)
assert(Number.isFinite(ES.cadeia(0.3, [[0, 0], [0.1, 1, { zeta: 0.8, omega: 20 }]])) && Number.isFinite(ES.mola(0.2, { zeta: 0.8, omega: 20 })), "mola sem u0 deu NaN");
near(ES.cadeia(5, ch), 40, 1e-6, "cadeia assenta no último alvo");
near(ES.cadeia(0.05, ch), 0, 1e-9, "cadeia parada antes da 1a mudança");

// 4. batidas: colcheias de 136,9 BPM com a fase medida no Joi (23,5 ms)
const g = ES.grade({ bpm: 136.9, primeiro: 0.0235, divisao: 2, ate: 8 });
near(g[1] - g[0], 60 / 136.9 / 2, 1e-6, "passo da grade");
const [e1, e2] = ES.encaixa([1.333, { t: 4.683, nome: "Get" }], g, { fps: 60 });
near(e1, Math.round(1.3383 * 60) / 60, 1e-9, "encaixa flip do Joi");
assert(e2.nome === "Get" && Math.abs(e2.desvio) < 0.12, "encaixa objeto");
const solto = ES.encaixa([1.4], g, { tolerancia: 0.01 })[0];
near(solto, 1.4, 1e-9, "fora da tolerância fica onde está");
const gb = ES.grade({ batidas: [{ time: 1 }, { time: 1.5 }, { time: 2 }], divisao: 2 });
assert.deepStrictEqual(gb, [1, 1.25, 1.5, 1.75, 2]);

// 5. entradas e saídas chegam no repouso / somem
for (const tipo of Object.keys(ES.ENTRADAS)) {
  const a = ES.entrada(tipo, 3, { altura: 80 });
  assert(Math.abs(a.dx) < 0.01 && Math.abs(a.dy) < 0.01 && Math.abs(a.s - 1) < 1e-3 && a.blur === 0 && a.op === 1, "entrada " + tipo);
  const b = ES.saida(tipo, 1, {});
  assert(b.op === 0 && b.blur > 8.9, "saida " + tipo);
  assert(ES.saida(tipo, 0, {}).op === 1, "saida começa visível " + tipo);
}

// 6. os presets reproduzem as trilhas medidas que lhes deram origem (clones são só leitura)
// a trilha do clone não vai no repositório: o teste 6 roda só com ASUI_ORIGINAIS/satellite-tracks.js
const R = process.env.ASUI_ORIGINAIS || path.join(require("os").homedir(), ".apple-style-ui", "originais");
const load = (p) => { const window = {}; eval(fs.readFileSync(path.join(R, p), "utf8")); return window.TR; };
const TEM = fs.existsSync(path.join(R, "satellite-tracks.js"));
const S = TEM ? load("satellite-tracks.js") : null;
const box = (f, i) => S.box.v[f - S.box.a][i];
function rms(m, fps, f0, f1, x0, x1, val, shift = 0) {
  let e = 0, n = 0;
  for (let f = f0; f <= f1; f++) { const p = ES.mola((f - f0 - shift) / fps, m); const q = (val(f) - x0) / (x1 - x0); e += (p - q) ** 2; n++; }
  return Math.sqrt(e / n);
}
const r1 = TEM ? rms("suave", 30, 88, 110, 614, 268, (f) => box(f, 0), 1) : 0;
const r2 = TEM ? rms("firme", 30, 31, 50, 318, 766, (f) => box(f, 0), 0.5) : 0;
const UPG = [[334, 0.45], [336, 0.55], [338, 0.7], [340, 0.85], [342, 0.97], [344, 1.04], [346, 1.05], [348, 1.04], [350, 1.02], [352, 0.99], [356, 1.0], [380, 1.0]];
const r3 = Math.sqrt(UPG.reduce((s, [f, v]) => s + (ES.mola((f - 334) / 60, "elastica") - (v - 0.45) / 0.55) ** 2, 0) / UPG.length);
assert(r1 < 0.025 && r2 < 0.025 && r3 < 0.025, `rms das trilhas: suave ${r1} firme ${r2} elastica ${r3}`);

console.log("estilo.js ok",
  { assenta: { suave: ES.assenta("suave"), firme: ES.assenta("firme"), elastica: ES.assenta("elastica"), rapida: ES.assenta("rapida"), deslize: ES.assenta("deslize") },
    overshoot_elastica: +ES.overshoot("elastica").toFixed(3), rms: { suave: +r1.toFixed(4), firme: +r2.toFixed(4), elastica: +r3.toFixed(4) } });
