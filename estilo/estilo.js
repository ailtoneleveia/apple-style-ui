/* ==========================================================================================
   estilo.js: o perfil de estilo do Apple Style UI, medido nos 3 clones do @creatoroly
   (Satellite, Joi e VoiceOS). Qualquer molde ou peça importa esta biblioteca, sem dependência:
   no HyperFrames, <script src="estilo.js"></script> e window.ESTILO; no Node, require("./estilo.js").
   As cores e a fonte de cada marca ficam no kit de marca da peça; aqui ficam só movimento, tempo,
   tipografia, acabamento e a caixa que se transforma. Os números e de onde vieram estão no ESTILO.md.
   Tudo é função pura do tempo (seek-safe): nada de Date.now, Math.random ou estado entre quadros.
   Uso interno de estudo (SF Pro e emojis da Apple só neste Mac).
   ========================================================================================== */
(function (root) {
  "use strict";

  // ---------------------------------------------------------------- utilitários (do Satellite)
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const E = {
    lin: (t) => t,
    out: (t) => 1 - Math.pow(1 - t, 3),
    out2: (t) => 1 - (1 - t) * (1 - t),
    out4: (t) => 1 - Math.pow(1 - t, 4),
    in2: (t) => t * t,
    in3: (t) => t * t * t,
    sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * t),
  };
  const prog = (F, a, b, e = E.lin) => e(clamp((F - a) / (b - a)));
  // chaves [[quadro, valor, ease?], ...] com ease por trecho
  function kf(F, keys, ease = E.sine) {
    if (F <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) if (F <= keys[i][0]) {
      const [f0, v0] = keys[i - 1], [f1, v1, e] = keys[i];
      return lerp(v0, v1, (e || ease)((F - f0) / (f1 - f0)));
    }
    return keys[keys.length - 1][1];
  }
  // Catmull-Rom pelas chaves: sem parar a velocidade nas chaves internas
  function cr(F, keys) {
    const n = keys.length;
    if (F <= keys[0][0]) return keys[0][1];
    if (F >= keys[n - 1][0]) return keys[n - 1][1];
    let i = 0; while (keys[i + 1][0] < F) i++;
    const p0 = keys[Math.max(i - 1, 0)], p1 = keys[i], p2 = keys[i + 1], p3 = keys[Math.min(i + 2, n - 1)];
    const t = (F - p1[0]) / (p2[0] - p1[0]);
    const m1 = ((p2[1] - p0[1]) / (p2[0] - p0[0] || 1)) * (p2[0] - p1[0]);
    const m2 = ((p3[1] - p1[1]) / (p3[0] - p1[0] || 1)) * (p2[0] - p1[0]);
    const t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * p1[1] + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2[1] + (t3 - t2) * m2;
  }
  const hex = (h) => { h = String(h).replace("#", ""); return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)); };
  const mixc = (a, b, t) => a.map((v, i) => Math.round(lerp(v, b[i], t)));
  const rgb = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  const blurf = (b) => (b > 0.05 ? `blur(${b.toFixed(2)}px)` : "none");
  const luma = (c) => { const [r, g, b] = hex(c); return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255; };

  // ---------------------------------------------------------------- obturador (motion blur)
  // Exposição medida: Satellite 0,25 q a 30 fps, VoiceOS 0,5 q a 60 fps (ajuste), Joi 0,4 q a 60 fps.
  // As duas medidas mais firmes dão o mesmo tempo de exposição: 1/120 s.
  const EXPOSICAO = 1 / 120;
  const obturador = (fps) => fps * EXPOSICAO; // fração do quadro: 0,25 a 30 fps, 0,5 a 60 fps
  // Render a fps*N (N subquadros), tmix N. MB_SHIFT centra os subquadros no quadro (vai no mb.js).
  const mbShift = (n, fps) => (n - 1) / 2 / (fps * n);
  // Fi: quadro inteiro (decide o que existe, cortes secos); F: quadro contínuo que move as coisas.
  function quadro(t, fps, nf, shutter = obturador(fps)) {
    const Fi = Math.min(nf - 1, Math.floor(t * fps + 1e-4));
    const frac = t * fps - Fi, shift = (root.MB_SHIFT || 0) * fps;
    return { Fi, F: Fi + (frac - shift) * shutter };
  }

  // ---------------------------------------------------------------- molas em forma fechada
  // Oscilador amortecido: e'' = -2*zeta*omega*e' - omega^2*e, com e(0)=e0 e e'(0)=v0. Devolve [e, e'].
  function molaErro(t, e0, v0, z, w) {
    if (t <= 0) return [e0, v0];
    if (z < 0.9999) {
      const a = z * w, wd = w * Math.sqrt(1 - z * z), B = (v0 + a * e0) / wd;
      const ex = Math.exp(-a * t), c = Math.cos(wd * t), s = Math.sin(wd * t);
      return [ex * (e0 * c + B * s), ex * ((B * wd - a * e0) * c - (a * B + e0 * wd) * s)];
    }
    if (z <= 1.0001) {
      const c = v0 + w * e0, ex = Math.exp(-w * t);
      return [ex * (e0 + c * t), ex * (c - w * (e0 + c * t))];
    }
    const q = Math.sqrt(z * z - 1), r1 = -w * (z - q), r2 = -w * (z + q);
    const A = (v0 - r2 * e0) / (r1 - r2), B = e0 - A, x1 = Math.exp(r1 * t), x2 = Math.exp(r2 * t);
    return [A * x1 + B * x2, A * r1 * x1 + B * r2 * x2];
  }
  // Presets ajustados por mínimos quadrados nas trilhas medidas (ESTILO.md, tabela "Molas").
  // u0: impulso inicial em "distâncias por segundo" (0 = sai do repouso).
  const MOLAS = {
    suave: { zeta: 1.22, omega: 20.0, u0: 0, origem: "Satellite, caixa cartão→tile f88-110 (rms 1,8 %)" },
    firme: { zeta: 1.57, omega: 37.9, u0: 0, origem: "Satellite, caixa ícone→cartão f31-50 (rms 1,5 %); VoiceOS janela assenta no mesmo 0,30 s" },
    elastica: { zeta: 0.62, omega: 19.2, u0: 0, origem: "Joi, botão Upgrade f334-356 (rms 1,8 %); Joi ícone e balão do Satellite dão zeta 0,58-0,66" },
    // internas: forma e cor chegam antes da caixa; deslize é a cauda longa de listas e títulos
    rapida: { zeta: 1.0, omega: 39, u0: 0, origem: "Satellite, raio e cor no ícone→cartão f31-35" },
    deslize: { zeta: 1.94, omega: 13.7, u0: 13.5, origem: "Satellite, pílula Vehicle f150-190 (rms 0,8 %)" },
  };
  const P = (m) => (typeof m === "string" ? MOLAS[m] : m ? { u0: 0, ...m } : MOLAS.suave);  // mola sem u0 sai do repouso (antes dava NaN)
  // progresso 0→1 de uma mola que sai do repouso em t=0 (t em segundos)
  const mola = (t, m = "suave") => { const p = P(m); return 1 - molaErro(t, 1, -p.u0, p.zeta, p.omega)[0]; };
  const molaVel = (t, m = "suave") => { const p = P(m); return -molaErro(t, 1, -p.u0, p.zeta, p.omega)[1]; };
  const _cache = new Map();
  function _scan(m, key, fn) {
    const k = key + JSON.stringify(P(m)); if (!_cache.has(k)) _cache.set(k, fn(P(m))); return _cache.get(k);
  }
  // tempo até ficar dentro de tol (2 %) da distância e não sair mais
  const assenta = (m = "suave", tol = 0.02) => _scan(m, "a" + tol, (p) => {
    let last = 0; for (let t = 0; t < 6; t += 0.001) if (Math.abs(1 - mola(t, p)) > tol) last = t; return +last.toFixed(3);
  });
  const overshoot = (m) => _scan(m, "o", (p) => { let o = 0; for (let t = 0; t < 6; t += 0.001) o = Math.max(o, mola(t, p) - 1); return o; });
  const velMax = (m) => _scan(m, "v", (p) => { let v = 0; for (let t = 0; t < 3; t += 0.0005) v = Math.max(v, Math.abs(molaVel(t, p))); return v; });
  // Mola encadeada: chaves [[t, valor, mola?], ...]. Em cada chave o alvo muda e a velocidade
  // atual continua (sem tranco quando um estado novo chega antes do anterior assentar).
  function cadeia(t, chaves, m = "suave", comVel = false) {
    let seg = { ts: chaves[0][0], xs: chaves[0][1], vs: 0, alvo: chaves[0][1], p: P(m) };
    const aval = (s, tt) => { const [e, de] = molaErro(tt - s.ts, s.xs - s.alvo, s.vs, s.p.zeta, s.p.omega); return [s.alvo + e, de]; };
    for (let i = 1; i < chaves.length; i++) {
      const [ti, alvo, mi] = chaves[i];
      if (t < ti) break;
      const [x, v] = aval(seg, ti), p = P(mi || m);
      seg = { ts: ti, xs: x, vs: v + p.u0 * (alvo - x), alvo, p };
    }
    const r = aval(seg, Math.max(t, chaves[0][0]));
    return comVel ? r : r[0];
  }
  const cadeiaCor = (t, chaves, m = "rapida") => [0, 1, 2].map((i) => Math.round(clamp(cadeia(t, chaves.map((c) => [c[0], hex(c[1])[i], c[2]]), m), 0, 255)));

  // ---------------------------------------------------------------- entradas e saídas
  // dist em múltiplos de "altura" do elemento ou da largura do "quadro"; tempos em segundos.
  const ENTRADAS = {
    cima: { eixo: "y", dist: -1.6, ref: "altura", mola: "suave", s0: 1, blur: 10, tBlur: 0.17, tOp: 0.06 }, // Joi "Get your subscription"; Satellite título cai 2,9x
    baixo: { eixo: "y", dist: 1.2, ref: "altura", mola: "firme", s0: 1, blur: 24, tBlur: 0.2, tOp: 0.05 }, // VoiceOS palavras e pílula
    lado: { eixo: "x", dist: 0.62, ref: "quadro", mola: "suave", s0: 1, blur: 12, tBlur: 0.2, tOp: 0.05 }, // Joi estrela, x 1052→382 em 0,23 s
    escala: { eixo: null, mola: "elastica", s0: 0.45, blur: 16, tBlur: 0.3, tOp: 0.1 }, // Joi Upgrade 0,45→1,05→1; Satellite ícone blur 16→0
    desfoque: { eixo: null, mola: "firme", s0: 1.12, blur: 12, tBlur: 0.12, tOp: 0.05 }, // Joi textos 8-12 px→0 em 0,1 s; motor "desfoque" 12 % maior
  };
  // t: segundos desde o início da entrada. o: {altura, quadro, ...sobrescritas}. tinta: 0→1 da cor de destaque para a tinta final.
  function entrada(tipo, t, o = {}) {
    const c = Object.assign({}, ENTRADAS[tipo], o), p = mola(t, c.mola);
    const d = c.eixo ? c.dist * (c.ref === "quadro" ? o.quadro || 1080 : o.altura || 100) : 0;
    const off = d * (1 - p);
    return {
      dx: c.eixo === "x" ? off : 0, dy: c.eixo === "y" ? off : 0, s: lerp(c.s0, 1, p), rot: (c.rot0 || 0) * (1 - p),
      blur: c.blur * Math.pow(1 - clamp(t / c.tBlur), 2), op: clamp(t / c.tOp), tinta: prog(t, 0.1, 0.25),
    };
  }
  // Saída medida no Satellite (f259-276): sobe 134 de 1080 px acelerando x1,25 por quadro a 30 fps (lambda 6,7/s),
  // desfoque 0→9 px a partir de 41 % do tempo, some nos últimos 29 %. lado e escala: espelho da entrada (sem medida própria).
  const SAIDAS = {
    cima: { eixo: "y", dist: -0.124, ref: "quadro", T: 0.47 },
    baixo: { eixo: "y", dist: 0.124, ref: "quadro", T: 0.47 },
    lado: { eixo: "x", dist: -0.62, ref: "quadro", T: 0.47 },
    escala: { eixo: null, s1: 0.45, T: 0.47 },
    desfoque: { eixo: null, s1: 1, T: 0.47 },
  };
  function saida(tipo, t, o = {}) {
    const c = Object.assign({}, SAIDAS[tipo], o), u = clamp(t / c.T), L = 6.7 * c.T;
    const ac = (Math.exp(L * u) - 1) / (Math.exp(L) - 1);
    const d = c.eixo ? c.dist * (c.ref === "quadro" ? o.quadro || 1080 : o.altura || 100) : 0;
    return {
      dx: c.eixo === "x" ? d * ac : 0, dy: c.eixo === "y" ? d * ac : 0, s: lerp(1, c.s1 == null ? 1 : c.s1, ac), rot: 0,
      blur: 9 * Math.pow(clamp((u - 0.41) / 0.59), 1.5), op: kf(u, [[0.71, 1], [0.88, 0.7, E.lin], [1, 0, E.lin]]),
    };
  }
  // escalonamento medido: palavras 35-42 ms (Joi), botões 33 ms (Joi), itens de lista 170-200 ms (Satellite)
  const PASSO = { palavra: 0.04, botao: 0.033, item: 0.18, letra: 0.1 };
  const escalona = (i, passo = PASSO.palavra, base = 0) => base + i * passo;

  // ---------------------------------------------------------------- tempo: encaixe nas batidas
  // grade({bpm, primeiro, divisao}) ou grade({batidas: [t...] ou [{time}...]}); divisao 2 = colcheias.
  function grade({ bpm, primeiro = 0, divisao = 2, batidas = null, ate = 120 } = {}) {
    if (batidas && batidas.length > 1) {
      const b = batidas.map((x) => (typeof x === "number" ? x : x.time)), g = [];
      for (let i = 0; i + 1 < b.length; i++) for (let j = 0; j < divisao; j++) g.push(lerp(b[i], b[i + 1], j / divisao));
      g.push(b[b.length - 1]); return g;
    }
    const passo = 60 / bpm / divisao, g = [];
    for (let t = primeiro - Math.floor(primeiro / passo) * passo; t <= ate; t += passo) g.push(+t.toFixed(6));
    return g;
  }
  // Move cada evento (número em s ou {t}) para a marca mais perto da grade, se estiver a até `tolerancia` s.
  // fps arredonda para o quadro. Objetos voltam com {desvio} = quanto andaram.
  function encaixa(eventos, g, { tolerancia = Infinity, fps = 0 } = {}) {
    return eventos.map((e) => {
      const t = typeof e === "number" ? e : e.t;
      let best = t, d = Infinity;
      for (const x of g) { const dd = Math.abs(x - t); if (dd < d) { d = dd; best = x; } }
      let nt = d <= tolerancia ? best : t;
      if (fps) nt = Math.round(nt * fps) / fps;
      return typeof e === "number" ? nt : Object.assign({}, e, { t: nt, desvio: nt - t });
    });
  }

  // ---------------------------------------------------------------- tipografia
  // pesos do SF Pro por função (Joi medido; Satellite e VoiceOS no ESTILO.md)
  const PESOS = { titulo: 600, lista: 620, botao: 590, rotulo: 590, frase: 450, corpo: 500, digito: 900, tecla: 700 };
  // Tamanho pela LARGURA da frase (VoiceOS: pela altura erra 8-12 %). Itera porque o SF Pro troca o opsz com o tamanho.
  // Mede a largura de avanço (uns 2 % maior que a tinta). Chame só depois de document.fonts.load("<peso> 100px \"SF Pro\""):
  // antes disso mede a fonte reserva e erra 6-10 % (testado no render).
  function tamanhoPorLargura(texto, largura, { peso = 500, familia = '"SF Pro", -apple-system, sans-serif', espacamento = 0, doc = root.document } = {}) {
    const sp = doc.createElement("span");
    sp.style.cssText = `position:absolute;left:-9999px;top:0;visibility:hidden;white-space:pre;font-family:${familia};font-weight:${peso};letter-spacing:${espacamento}px;font-optical-sizing:auto`;
    sp.textContent = texto; doc.body.appendChild(sp);
    let px = 100;
    for (let i = 0; i < 4; i++) { sp.style.fontSize = px + "px"; px *= largura / sp.getBoundingClientRect().width; }
    sp.remove(); return px;
  }

  // ---------------------------------------------------------------- acabamento
  // raio / menor lado (border-radius comum; nenhum dos 3 clones usou canto contínuo)
  const RAIO = { icone: 0.229, cartao: 0.229, tile: 0.235, menu: 0.246, pilula: 0.345, capsula: 0.5, janela: 0.15, tecla: 0.216 };
  const raio = (w, h, tipo = "cartao") => RAIO[tipo] * Math.min(w, h);
  // sombras quase não existem: profundidade vem de aro fino e brilho colorido
  const SOMBRA = {
    nenhuma: "none",
    pilula: "0 2.5px 0 0 #e3e3e3, 0 1px 3px rgba(0,0,0,0.03)", // Satellite, lista
    flutuante: "0 10px 26px rgba(0,0,0,0.16)", // Satellite, Dynamic Island
    tecla: "inset 0 0 0 2.5px rgba(206,211,220,1), 0 8px 22px rgba(30,40,60,0.07)", // VoiceOS, tecla fn
    aroEscuro: "inset 0 0 0 2px #2c2c2f", // Joi, menu escuro
    aroClaro: "inset 0 0 0 3px rgba(255,255,255,0.22)", // Joi, pílula
    aroVidro: "inset 0 0 0 1px rgba(255,255,255,0.07)", // VoiceOS, janela
  };
  // brilho colorido: Satellite knob 16 px / 0,55, barra do tile 14 px / 0,6; VoiceOS 18-26 px / 0,55-0,8
  const brilho = (cor, r = 16, a = 0.55) => `0 0 ${r}px ${rgb(hex(cor), a)}`;
  // calibração de luma do encode (só Y, nunca croma). filtro: ganho do Satellite, faz a cor escrita sair igual
  // (#fdfdfd saía #fbfbfb). instagram: + LUT do Joi, que copia os níveis do vídeo postado (escuros +2, brancos +1);
  // só serve para comparar com um original baixado: por cima do ganho, #fdfdfd vira #ffffff.
  const LUMA = {
    ganho: 1.008,
    filtro: "lutyuv=y='clip(16+(val-16)*1.008\\,0\\,255)'",
    instagram: "lutyuv=y='clip(16+(val-16)*1.008\\,0\\,255)',lutyuv=y='clip(val+0.5+if(lt(val\\,73)\\,2\\,if(lt(val\\,154)\\,2*(154-val)/81\\,if(lt(val\\,233)\\,0\\,1)))\\,0\\,255)'",
  };

  // ---------------------------------------------------------------- a caixa que se transforma
  // caixa(pai, {estados, sequencia, mola?, desfoque?}) cria um retângulo arredondado que passa de estado
  // em estado com o morph calibrado do Satellite:
  //  - posição e tamanho pela mola da transição, encadeada (velocidade continua se um estado chega cedo);
  //  - raio e cor chegam antes (mola "rapida", ~0,15 s); a cor nova cobre a velha como opacidade (sem brightness);
  //    se o estado novo é bem mais claro, a cor vem numa rampa em S de 0,5 s e a velha perde o matiz (cinza);
  //  - desfoque de profundidade proporcional à velocidade da forma (Satellite: pico 7,5 / 3 / 6 px);
  //  - conteúdo velho sai em 0,08 s, o novo entra entre 0,04 e 0,17 s saindo de 8 px de desfoque (0,3 s);
  //  - virar: true faz o flip do Joi (rotateX 0→180, perspectiva 1200, troca de face aos 90°, pico de 10 px).
  // estado: {x, y (centro), w, h, raio: px | nome em RAIO, cor, fundo?, sombra?, brilho?: {cor, raio, opacidade},
  //          conteudo?: HTML no tamanho w x h do estado, encaixe?: "conter" | "mascara", atraso?: s}
  // sequencia: [{t, estado, mola?, desfoque?, virar?, entrada?}], t em segundos; o primeiro item é a aparição.
  function caixa(pai, cfg) {
    const doc = pai.ownerDocument, { estados, sequencia: seq } = cfg;
    const el = (css, parent, html) => { const e = doc.createElement("div"); e.style.cssText = css; if (html != null) e.innerHTML = html; parent.appendChild(e); return e; };
    const raiz = el("position:absolute;left:0;top:0;width:0;height:0", pai);
    const halos = el("position:absolute;left:0;top:0", raiz);
    const corpo = el("position:absolute;left:0;top:0", raiz);
    const box = el("position:absolute;left:0;top:0;overflow:hidden", corpo);
    const L = {};
    const kr = (st) => (typeof st.raio === "string" ? RAIO[st.raio] : (st.raio == null ? RAIO.cartao * Math.min(st.w, st.h) : st.raio) / Math.min(st.w, st.h));
    for (const n of Object.keys(estados)) {
      const st = estados[n], b = st.brilho;
      L[n] = {
        halo: b ? el(`position:absolute;background:${b.cor};filter:blur(${b.raio || 40}px);opacity:0`, halos) : null,
        fundo: el(`position:absolute;inset:0;background:${st.fundo || st.cor};opacity:0`, box),
      };
    }
    for (const n of Object.keys(estados)) {
      const st = estados[n];
      L[n].cont = st.conteudo != null ? el(`position:absolute;left:0;top:0;width:${st.w}px;height:${st.h}px;transform-origin:0 0;opacity:0;z-index:3`, box, st.conteudo) : null;
      L[n].pele = el(`position:absolute;pointer-events:none;box-shadow:${st.sombra || "none"};opacity:0`, corpo);
    }
    const chaves = (f) => seq.map((s) => [s.t, f(estados[s.estado]), s.mola || cfg.mola || "suave"]);
    const CH = { x: chaves((s) => s.x), y: chaves((s) => s.y), w: chaves((s) => s.w), h: chaves((s) => s.h), k: seq.map((s) => [s.t, kr(estados[s.estado]), "rapida"]) };

    function geometria(t) {
      const g = {};
      for (const c of ["x", "y", "w", "h"]) g[c] = cadeia(t, CH[c]);
      g.r = cadeia(t, CH.k) * Math.min(g.w, g.h);
      return g;
    }
    function desenha(t) {
      if (t < seq[0].t) { raiz.style.display = "none"; return null; }
      raiz.style.display = "block";
      let k = 0; while (k + 1 < seq.length && t >= seq[k + 1].t) k++;
      const tr = seq[k], dt = t - tr.t, cur = tr.estado, prev = k > 0 ? seq[k - 1].estado : null;
      const muda = prev && prev !== cur, m = tr.mola || cfg.mola || "suave";
      const g = geometria(t), x0 = g.x - g.w / 2, y0 = g.y - g.h / 2;
      // escurecer é rápido (mola "rapida", ~0,15 s); clarear é lento, rampa em S de 0,5 s que passa por cinza
      // (Satellite tile→pílula f119-133, Joi fundo escuro→branco f271-303)
      const clareia = muda && !tr.virar && luma(estados[cur].cor) - luma(estados[prev].cor) > 0.25;
      const pc = !muda ? 1 : clareia ? E.sine(clamp(dt / 0.5)) : mola(dt, "rapida");
      // pesos de cada camada
      const W = {}; for (const n in L) W[n] = { fundo: 0, cont: 0, pele: 0, blurC: 0, z: 0 };
      let ang = 0, blur = 0;
      if (muda) blur = (tr.desfoque != null ? tr.desfoque : cfg.desfoque != null ? cfg.desfoque : 5) * Math.abs(molaVel(dt, m)) / velMax(m);
      if (muda && tr.virar) {
        ang = 180 * mola(dt, m);
        const lado = ang < 90 ? prev : cur;
        Object.assign(W[lado], { fundo: 1, cont: 1, pele: 1, z: 2 });
        blur += 10 * Math.max(0, 1 - Math.abs(ang - 90) / 30); // Joi f83: o ícone de lado quase some
      } else {
        const at = muda ? estados[cur].atraso || 0 : 0;
        Object.assign(W[cur], { fundo: pc, pele: pc, z: 2, cont: muda ? E.out2(prog(dt - at, 0.04, 0.17)) : 1, blurC: muda ? 8 * Math.pow(1 - prog(dt - at, 0.04, 0.3), 2) : 0 });
        if (muda) Object.assign(W[prev], { fundo: 1, pele: 1 - pc, z: 1, cont: 1 - prog(dt, 0, 0.08), blurC: 4 * prog(dt, 0, 0.08) });
      }
      // entrada da primeira aparição
      let tf = "";
      if (seq[0].entrada) {
        const en = entrada(seq[0].entrada, t - seq[0].t, { altura: g.h });
        tf += `translate(${en.dx}px,${en.dy}px) scale(${en.s}) `; blur += en.blur; raiz.style.opacity = en.op;
      }
      if (ang) tf += `perspective(1200px) rotateX(${ang < 90 ? ang : ang - 180}deg)`;
      raiz.style.transformOrigin = `${g.x}px ${g.y}px`;
      raiz.style.transform = tf || "none";
      Object.assign(box.style, { left: x0 + "px", top: y0 + "px", width: g.w + "px", height: g.h + "px", borderRadius: g.r + "px" });
      corpo.style.filter = blurf(blur);
      for (const n in L) {
        const st = estados[n], w = W[n], l = L[n];
        l.fundo.style.opacity = w.fundo; l.fundo.style.zIndex = w.z;
        l.fundo.style.filter = clareia && n === prev ? `grayscale(${clamp(dt / 0.1).toFixed(3)})` : "none";
        Object.assign(l.pele.style, { left: x0 + "px", top: y0 + "px", width: g.w + "px", height: g.h + "px", borderRadius: g.r + "px", opacity: w.pele });
        if (l.cont) {
          l.cont.style.display = w.cont > 0.001 ? "block" : "none";
          if (w.cont > 0.001) {
            const s = st.encaixe === "mascara" ? 1 : Math.min(g.w / st.w, g.h / st.h);
            l.cont.style.transform = `translate(${(g.w - st.w * s) / 2}px,${(g.h - st.h * s) / 2}px) scale(${s})`;
            l.cont.style.opacity = w.cont; l.cont.style.filter = blurf(w.blurC);
          }
        }
        if (l.halo) {
          const b = st.brilho, sp = b.espalha != null ? b.espalha : (b.raio || 40) * 0.6;
          Object.assign(l.halo.style, { left: x0 - sp + "px", top: y0 - sp + "px", width: g.w + 2 * sp + "px", height: g.h + 2 * sp + "px", borderRadius: g.r + sp + "px", opacity: (b.opacidade != null ? b.opacidade : 0.5) * Math.max(w.fundo * (w.z === 2 ? 1 : 1 - pc), 0) });
        }
      }
      return g;
    }
    return { raiz, desenha, geometria };
  }

  const API = {
    clamp, lerp, E, prog, kf, cr, hex, mixc, rgb, blurf, luma,
    EXPOSICAO, obturador, mbShift, quadro,
    molaErro, MOLAS, mola, molaVel, assenta, overshoot, velMax, cadeia, cadeiaCor,
    ENTRADAS, entrada, SAIDAS, saida, PASSO, escalona,
    grade, encaixa,
    PESOS, tamanhoPorLargura,
    RAIO, raio, SOMBRA, brilho, LUMA,
    caixa,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.ESTILO = API;
})(typeof window !== "undefined" ? window : globalThis);
