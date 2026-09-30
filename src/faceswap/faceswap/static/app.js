"use strict";

const $ = (id) => document.getElementById(id);

const state = {
  status: null,
  target: null, // {id, name, width, height, faces, file}
  sources: [], // same shape as target
  activeSource: -1,
  selectedTarget: null, // target face index
  pendingSource: null, // {sourceId, face} picked before a target face
  pairs: new Map(), // target face index -> {sourceId, face}
  result: null, // {url, blob, ext}
  busy: false,
};

// ---------- api ----------

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (_) {}
    throw new Error(msg);
  }
  return res;
}

async function uploadImage(file) {
  const form = new FormData();
  form.append("file", file);
  form.append("thorough", $("thorough").checked ? "true" : "false");
  const res = await api("/api/images", { method: "POST", body: form });
  const data = await res.json();
  data.file = file;
  return data;
}

// ---------- helpers ----------

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null) node.append(c);
  return node;
}

function toast(message) {
  const t = $("toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 6000);
}

async function withBusy(node, fn) {
  node.classList.add("busy");
  state.busy = true;
  try {
    return await fn();
  } catch (err) {
    toast(err.message || String(err));
  } finally {
    node.classList.remove("busy");
    state.busy = false;
    render();
  }
}

const sourceById = (id) => state.sources.find((s) => s.id === id);
const faceLabel = (i) => `#${i + 1}`;

// ---------- actions ----------

async function setTarget(file) {
  if (!file) return;
  await withBusy($("target-card"), async () => {
    const data = await uploadImage(file);
    state.target = data;
    state.pairs.clear();
    state.selectedTarget = data.faces.length === 1 ? 0 : null;
    clearResult();
    applyPendingSource();
  });
}

async function addSources(files) {
  files = [...files].filter(Boolean);
  if (!files.length) return;
  await withBusy($("source-card"), async () => {
    for (const file of files) {
      const data = await uploadImage(file);
      state.sources.push(data);
      state.activeSource = state.sources.length - 1;
      // a single-face photo paired with a selected target face needs no extra click
      if (
        data.faces.length === 1 &&
        state.target &&
        state.selectedTarget != null &&
        !state.pairs.has(state.selectedTarget)
      ) {
        pick(data.id, 0);
      }
    }
  });
}

function removeSource(idx) {
  const [gone] = state.sources.splice(idx, 1);
  for (const [t, p] of state.pairs) if (p.sourceId === gone.id) state.pairs.delete(t);
  if (state.pendingSource?.sourceId === gone.id) state.pendingSource = null;
  state.activeSource = Math.min(state.activeSource, state.sources.length - 1);
  render();
}

function selectTarget(i) {
  state.selectedTarget = i;
  applyPendingSource();
  render();
}

function applyPendingSource() {
  if (!state.pendingSource || !state.target) return;
  let t = state.selectedTarget;
  if (t == null && state.target.faces.length === 1) t = 0;
  if (t == null) return;
  state.pairs.set(t, state.pendingSource);
  state.selectedTarget = t;
  state.pendingSource = null;
}

function pick(sourceId, face) {
  if (state.target && state.selectedTarget == null && state.target.faces.length === 1) state.selectedTarget = 0;
  if (state.target && state.selectedTarget != null) {
    state.pairs.set(state.selectedTarget, { sourceId, face });
    state.pendingSource = null;
  } else {
    state.pendingSource = { sourceId, face };
  }
  render();
}

function unpair(t) {
  state.pairs.delete(t);
  render();
}

function clearResult() {
  if (state.result) URL.revokeObjectURL(state.result.url);
  state.result = null;
}

async function runSwap() {
  if (!state.target || !state.pairs.size) return;
  const body = {
    target_id: state.target.id,
    swaps: [...state.pairs].map(([t, p]) => ({ target_face: t, source_id: p.sourceId, source_face: p.face })),
    enhance: state.status?.enhancer ? $("enhance").checked : false,
    enhance_blend: $("blend").value / 100,
    format: $("format").value,
  };
  const btn = $("swap-btn");
  const label = btn.textContent;
  btn.replaceChildren(el("span", { class: "spinner" }), " Swapping…");
  await withBusy($("plan-card"), async () => {
    const res = await api("/api/swap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const blob = await res.blob();
    clearResult();
    state.result = { url: URL.createObjectURL(blob), blob, ext: body.format };
    requestAnimationFrame(() => $("result-card").scrollIntoView({ behavior: "smooth", block: "start" }));
  });
  btn.textContent = label;
}

async function reuseResult() {
  if (!state.result) return;
  const base = (state.target?.name || "photo").replace(/\.[^.]+$/, "");
  const file = new File([state.result.blob], `${base}-swapped.${state.result.ext}`, { type: state.result.blob.type });
  await setTarget(file);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ---------- rendering ----------

function renderStage(stage, image, { isSelected, isPaired, onPick }) {
  stage.hidden = !image;
  stage.replaceChildren();
  if (!image) return;
  const frame = el("div", { class: "frame" });
  frame.append(el("img", { src: `/api/images/${image.id}/preview`, alt: image.name || "", draggable: "false" }));
  for (const f of image.faces) {
    const [x1, y1, x2, y2] = f.bbox;
    const cls = ["box", isSelected(f.index) && "selected", isPaired(f.index) && "paired"].filter(Boolean).join(" ");
    const box = el(
      "button",
      {
        class: cls,
        title: `Face ${faceLabel(f.index)} (${Math.round(f.score * 100)}%)`,
        onclick: () => onPick(f.index),
      },
      el("span", { class: "num" }, faceLabel(f.index)),
    );
    box.style.left = `${(x1 / image.width) * 100}%`;
    box.style.top = `${(y1 / image.height) * 100}%`;
    box.style.width = `${((x2 - x1) / image.width) * 100}%`;
    box.style.height = `${((y2 - y1) / image.height) * 100}%`;
    frame.append(box);
  }
  stage.append(frame);
}

function renderStrip(strip, image, { isSelected, isPaired, mini, onPick }) {
  strip.replaceChildren();
  if (!image) return;
  if (!image.faces.length) {
    strip.append(
      el(
        "p",
        { class: "empty-note" },
        "No faces found in this photo. ",
        el("button", { class: "icon", onclick: () => redetect(image) }, "Retry with “find small faces”"),
      ),
    );
    return;
  }
  for (const f of image.faces) {
    const cls = ["face", isSelected(f.index) && "selected", isPaired(f.index) && "paired"].filter(Boolean).join(" ");
    const m = mini?.(f.index);
    strip.append(
      el(
        "button",
        { class: cls, onclick: () => onPick(f.index), title: `Face ${faceLabel(f.index)}` },
        el("img", { src: f.thumb, alt: "" }),
        m ? el("img", { class: "mini", src: m, alt: "" }) : null,
        el("span", { class: "label" }, faceLabel(f.index)),
      ),
    );
  }
}

async function redetect(image) {
  $("thorough").checked = true;
  if (image === state.target) return setTarget(image.file);
  const idx = state.sources.indexOf(image);
  await withBusy($("source-card"), async () => {
    const data = await uploadImage(image.file);
    for (const [t, p] of state.pairs) if (p.sourceId === image.id) state.pairs.delete(t);
    state.sources[idx] = data;
  });
}

function sourceThumb(pair) {
  const src = pair && sourceById(pair.sourceId);
  return src?.faces[pair.face]?.thumb;
}

function hint() {
  if (!state.target && !state.sources.length) return "Start by adding the photo you want to change.";
  if (!state.target) return "Now add the photo you want to change.";
  if (!state.target.faces.length)
    return "No faces were found in that photo. Try “find small faces”, or use a different photo.";
  if (state.pendingSource) return "Now click the face in the photo that should be replaced.";
  if (!state.sources.length) {
    return state.selectedTarget == null
      ? "Click the face you want to replace, then add a photo of the new face."
      : `Face ${faceLabel(state.selectedTarget)} selected. Add a photo of the new face.`;
  }
  if (state.selectedTarget == null) return "Click a face in the photo to change, then click the replacement face.";
  if (!state.pairs.has(state.selectedTarget))
    return `Face ${faceLabel(state.selectedTarget)} selected. Click the replacement face on the right.`;
  return "Ready. Click another face to pair more, or press Swap faces.";
}

function render() {
  const t = state.target;
  const src = state.sources[state.activeSource];

  $("target-drop").classList.toggle("compact", !!t);
  $("target-drop").querySelector("span").innerHTML = t
    ? "Replace photo: drop or <u>browse</u>"
    : "Drop a photo here or <u>browse</u>";
  const targetOpts = {
    isSelected: (i) => i === state.selectedTarget,
    isPaired: (i) => state.pairs.has(i),
    mini: (i) => sourceThumb(state.pairs.get(i)),
    onPick: selectTarget,
  };
  renderStage($("target-stage"), t, targetOpts);
  renderStrip($("target-strip"), t, targetOpts);

  $("source-drop").classList.toggle("compact", state.sources.length > 0);
  $("source-drop").querySelector("span").innerHTML = state.sources.length
    ? "Add another photo: drop or <u>browse</u>"
    : "Drop one or more photos of the new face or <u>browse</u>";
  const tabs = $("source-tabs");
  tabs.replaceChildren(
    ...state.sources.map((s, i) =>
      el(
        "div",
        {
          class: `tab${i === state.activeSource ? " active" : ""}`,
          onclick: () => {
            state.activeSource = i;
            render();
          },
        },
        el("span", { title: s.name }, s.name || `photo ${i + 1}`),
        el(
          "button",
          {
            class: "x",
            title: "Remove",
            onclick: (e) => {
              e.stopPropagation();
              removeSource(i);
            },
          },
          "×",
        ),
      ),
    ),
  );
  const currentPair = state.selectedTarget != null ? state.pairs.get(state.selectedTarget) : null;
  const sourceOpts = {
    isSelected: (i) =>
      (state.pendingSource?.sourceId === src?.id && state.pendingSource?.face === i) ||
      (currentPair?.sourceId === src?.id && currentPair?.face === i),
    isPaired: (i) => [...state.pairs.values()].some((p) => p.sourceId === src?.id && p.face === i),
    onPick: (i) => pick(src.id, i),
  };
  renderStage($("source-stage"), src, sourceOpts);
  renderStrip($("source-strip"), src, sourceOpts);

  // plan
  const plan = $("plan");
  plan.replaceChildren();
  const pairs = [...state.pairs].sort((a, b) => a[0] - b[0]);
  if (!pairs.length) plan.append(el("li", { class: "empty" }, "No faces paired yet."));
  for (const [ti, p] of pairs) {
    const s = sourceById(p.sourceId);
    plan.append(
      el(
        "li",
        { class: "row" },
        el("img", { src: t.faces[ti].thumb, alt: "" }),
        el("span", { class: "arrow" }, "→"),
        el("img", { src: s.faces[p.face].thumb, alt: "" }),
        el(
          "span",
          { class: "desc" },
          "Face ",
          el("b", {}, faceLabel(ti)),
          " becomes face ",
          el("b", {}, faceLabel(p.face)),
          ` from ${s.name || "photo"}`,
        ),
        el("button", { class: "icon", title: "Remove this pair", onclick: () => unpair(ti) }, "Remove"),
      ),
    );
  }
  const enh = !!state.status?.enhancer;
  $("enhance-wrap").hidden = !enh;
  $("blend-wrap").hidden = !enh || !$("enhance").checked;
  $("swap-btn").disabled = state.busy || !pairs.length;
  if (!state.busy) $("swap-btn").textContent = pairs.length > 1 ? `Swap ${pairs.length} faces` : "Swap face";

  // result
  const r = state.result;
  $("result-card").hidden = !r;
  if (r) {
    $("result-img").src = r.url;
    const base = (t?.name || "photo").replace(/\.[^.]+$/, "");
    $("download").href = r.url;
    $("download").download = `${base}-swapped.${r.ext}`;
  }

  $("hint").textContent = hint();
}

// ---------- wiring ----------

function wireDrop(label, input, onFiles) {
  input.addEventListener("change", () => {
    onFiles([...input.files]);
    input.value = "";
  });
  label.addEventListener("dragover", (e) => {
    e.preventDefault();
    label.classList.add("over");
  });
  label.addEventListener("dragleave", () => label.classList.remove("over"));
  label.addEventListener("drop", (e) => {
    e.preventDefault();
    label.classList.remove("over");
    const files = [...e.dataTransfer.files].filter((f) => f.type.startsWith("image/") || !f.type);
    if (files.length) onFiles(files);
  });
}

wireDrop($("target-drop"), $("target-input"), (files) => setTarget(files[0]));
wireDrop($("source-drop"), $("source-input"), addSources);

// paste an image: fills the photo to change first, then replacement faces
document.addEventListener("paste", (e) => {
  const file = [...(e.clipboardData?.files || [])].find((f) => f.type.startsWith("image/"));
  if (!file) return;
  if (!state.target) setTarget(file);
  else addSources([file]);
});

$("swap-btn").addEventListener("click", runSwap);
$("reuse-btn").addEventListener("click", reuseResult);
$("enhance").addEventListener("change", render);
$("blend").addEventListener("input", () => ($("blend-out").textContent = `${$("blend").value}%`));

const compare = $("compare-btn");
const showOriginal = (on) => {
  if (!state.result || !state.target) return;
  $("result-img").src = on ? `/api/images/${state.target.id}/preview` : state.result.url;
};
compare.addEventListener("pointerdown", () => showOriginal(true));
for (const ev of ["pointerup", "pointerleave", "pointercancel"])
  compare.addEventListener(ev, () => showOriginal(false));

(async function init() {
  render();
  try {
    state.status = await (await api("/api/status")).json();
    const d = $("device");
    const name = state.status.provider.replace("ExecutionProvider", "");
    d.textContent = state.status.gpu ? `GPU: ${name}` : "CPU only (slow)";
    d.className = `badge ${state.status.gpu ? "ok" : "warn"}`;
    if (!state.status.gpu) d.title = "Install the cuda or directml extra to use your graphics card";
  } catch (err) {
    toast(`Could not reach the local server: ${err.message}`);
  }
  render();
})();
