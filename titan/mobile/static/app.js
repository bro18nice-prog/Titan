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

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/static/service-worker.js");
checkHub();
