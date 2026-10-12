const form = document.querySelector("#command-form");
const input = document.querySelector("#command-input");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#send-button");
const statusLabel = document.querySelector("#hub-status");
const connection = document.querySelector("#connection-status");
const pairingCard = document.querySelector("#pairing-card");
const pairingInput = document.querySelector("#pairing-token");
const pairingButton = document.querySelector("#pair-button");

const storageKey = "titan-mobile-session";
const tokenKey = "titan-mobile-access-token";
let sessionId = localStorage.getItem(storageKey) || "";
let accessToken = localStorage.getItem(tokenKey) || "";

function authHeaders(headers = {}) {
  return accessToken ? { ...headers, Authorization: `Bearer ${accessToken}` } : headers;
}

function showPairing(message = "Conectează acest telefon") {
  pairingCard.hidden = false;
  statusLabel.textContent = message;
}

function appendMessage(text, author) {
  const message = document.createElement("article");
  message.className = `message ${author}-message`;
  message.textContent = text;
  messages.append(message);
  messages.scrollTop = messages.scrollHeight;
}

async function sendCommand(text) {
  const command = text.trim();
  if (!command) return;
  appendMessage(command, "user");
  input.value = "";
  input.focus();
  sendButton.disabled = true;

  try {
    const response = await fetch("/api/commands", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ text: command, session_id: sessionId || null }),
    });
    const payload = await response.json();
    if (response.status === 401) {
      showPairing("Este necesar codul TITAN");
      throw new Error("Conectează telefonul cu codul TITAN.");
    }
    if (!response.ok) throw new Error(payload.detail || "TITAN nu a putut procesa comanda.");
    sessionId = payload.session_id;
    localStorage.setItem(storageKey, sessionId);
    appendMessage(payload.response, "titan");
  } catch (error) {
    appendMessage(error.message || "Conexiunea cu TITAN Hub a eșuat.", "titan");
  } finally {
    sendButton.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendCommand(input.value);
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => sendCommand(button.dataset.command));
});

document.querySelector("#clear-chat").addEventListener("click", () => {
  messages.replaceChildren();
  appendMessage("Conversația locală a fost curățată. Sesiunea de confirmare rămâne protejată.", "titan");
});

pairingButton.addEventListener("click", async () => {
  const candidate = pairingInput.value.trim();
  if (!candidate) return;
  accessToken = candidate;
  await checkHub();
  if (connection.classList.contains("online")) {
    localStorage.setItem(tokenKey, candidate);
    pairingCard.hidden = true;
    pairingInput.value = "";
    appendMessage("Telefon conectat privat la TITAN Hub.", "titan");
    startHomePolling();
  }
});

async function checkHub() {
  try {
    const response = await fetch("/api/status", { headers: authHeaders() });
    if (response.status === 401) {
      connection.classList.remove("online");
      connection.lastChild.textContent = " Blocat";
      showPairing("Introduce codul pentru conectare");
      return;
    }
    if (!response.ok) throw new Error();
    const hub = await response.json();
    statusLabel.textContent = hub.mode === "protected" ? "Online · conexiune protejată" : "Preview local activ";
    connection.classList.add("online");
    connection.lastChild.textContent = " Online";
    pairingCard.hidden = true;
  } catch {
    statusLabel.textContent = "Hub indisponibil";
    connection.lastChild.textContent = " Offline";
  }
}

/* ---- Casa: dispozitive și consum ---- */
const homeSection = document.querySelector("#home-section");
const deviceGrid = document.querySelector("#device-grid");
const energyCard = document.querySelector("#energy-card");
const homeNote = document.querySelector("#home-note");
let energyRange = "day";
let homeTimer = null;
const rangeLabels = { day: "ASTĂZI", week: "7 ZILE", month: "LUNA ACEASTA" };

const fmtWatts = (w) => (w == null ? "—" : w >= 1000 ? `${(w / 1000).toFixed(2)} kW` : `${Math.round(w)} W`);
const fmtKwh = (k) => `${k.toFixed(k < 10 ? 2 : 1)} kWh`;

async function homeFetch(path, options = {}) {
  const response = await fetch(path, { ...options, headers: authHeaders(options.headers || {}) });
  if (response.status === 401) {
    showPairing("Este necesar codul TITAN");
    throw new Error("auth");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "Cerere eșuată.");
  return payload;
}

function brightnessFor(id) {
  return Number(localStorage.getItem(`titan-bright-${id}`)) || 100;
}

function renderDevices(devices) {
  deviceGrid.replaceChildren();
  for (const d of devices) {
    const card = document.createElement("div");
    card.className = `device ${d.on ? "on" : ""} ${d.online ? "" : "offline"}`;
    const name = document.createElement("span");
    name.className = "d-name";
    name.textContent = d.label;
    const state = document.createElement("span");
    state.className = "d-state";
    state.textContent = !d.online ? "offline" : `${d.on ? "pornit" : "oprit"}${d.on && d.watts != null ? " · " + fmtWatts(d.watts) : ""}`;
    card.append(name, state);
    if (d.online) {
      card.style.cursor = "pointer";
      card.addEventListener("click", async (event) => {
        if (event.target.tagName === "INPUT") return;
        card.style.opacity = ".6";
        try {
          await homeFetch(`/api/home/devices/${encodeURIComponent(d.id)}/power`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ on: !d.on }),
          });
        } catch (error) {
          if (error.message !== "auth") homeNote.textContent = error.message;
        }
        loadHome();
      });
      if (d.kind === "light" && d.on) {
        const slider = document.createElement("input");
        slider.type = "range";
        slider.min = 1;
        slider.max = 100;
        slider.value = brightnessFor(d.id);
        slider.setAttribute("aria-label", `Luminozitate ${d.label}`);
        slider.addEventListener("change", async () => {
          localStorage.setItem(`titan-bright-${d.id}`, slider.value);
          try {
            await homeFetch(`/api/home/devices/${encodeURIComponent(d.id)}/brightness`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ percent: Number(slider.value) }),
            });
          } catch (error) {
            if (error.message !== "auth") homeNote.textContent = error.message;
          }
        });
        card.append(slider);
      }
    }
    deviceGrid.append(card);
  }
}

function drawChart(series) {
  const canvas = document.querySelector("#energy-chart");
  const ratio = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * ratio;
  canvas.height = h * ratio;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const max = Math.max(0.001, ...series.map((p) => p.kwh));
  const gap = 3, bw = Math.max(2, (w - gap * (series.length - 1)) / series.length);
  ctx.fillStyle = "rgba(77,229,255,.85)";
  series.forEach((p, i) => {
    const bh = Math.max(p.kwh > 0 ? 2 : 0, (p.kwh / max) * (h - 6));
    ctx.beginPath();
    ctx.roundRect(i * (bw + gap), h - bh, bw, bh, 2);
    ctx.fill();
  });
}

function renderEnergy(data) {
  energyCard.hidden = data.metered_devices === 0;
  if (data.metered_devices === 0) return;
  document.querySelector("#energy-now").textContent = fmtWatts(data.watts_now);
  document.querySelector("#energy-total-label").textContent = rangeLabels[data.range];
  document.querySelector("#energy-total").textContent = fmtKwh(data.total_kwh);
  document.querySelector("#energy-cost").textContent =
    data.price_per_kwh ? `≈ ${(data.total_kwh * data.price_per_kwh).toFixed(2)} ${data.currency}` : "";
  const list = document.querySelector("#energy-list");
  list.replaceChildren();
  for (const item of data.per_device) {
    const li = document.createElement("li");
    const left = document.createElement("span");
    left.textContent = item.label;
    const right = document.createElement("b");
    right.textContent = `${fmtKwh(item.kwh)}${item.watts != null ? " · " + fmtWatts(item.watts) : ""}`;
    li.append(left, right);
    list.append(li);
  }
  drawChart(data.series);
}

async function loadHome() {
  try {
    const devices = await homeFetch("/api/home/devices");
    homeSection.hidden = !devices.configured;
    if (!devices.configured) return;
    homeNote.textContent = "actualizat acum";
    renderDevices(devices.devices);
    renderEnergy(await homeFetch(`/api/home/energy?range=${energyRange}`));
  } catch (error) {
    if (error.message !== "auth") homeNote.textContent = "indisponibil";
  }
}

document.querySelectorAll(".range-tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    energyRange = button.dataset.range;
    document.querySelectorAll(".range-tabs button").forEach((b) => b.classList.toggle("active", b === button));
    loadHome();
  });
});

function startHomePolling() {
  clearInterval(homeTimer);
  loadHome();
  homeTimer = setInterval(() => { if (!document.hidden) loadHome(); }, 10000);
}
document.addEventListener("visibilitychange", () => { if (!document.hidden) loadHome(); });

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/static/service-worker.js");
checkHub().then(startHomePolling);
