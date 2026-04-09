const API_BASE = "";

const welcome = document.getElementById("welcome");
const messages = document.getElementById("messages");
const typing = document.getElementById("typing");
const messageInput = document.getElementById("messageInput");

const imageBtn = document.getElementById("imageBtn");
const imageInput = document.getElementById("imageInput");
const previewBox = document.getElementById("previewBox");
const previewImage = document.getElementById("previewImage");
const removeImageBtn = document.getElementById("removeImageBtn");
const sendBtn = document.getElementById("sendBtn");
const chatArea = document.getElementById("chatArea");
const composerWrap = document.getElementById("composerWrap");

let selectedImageFile = null;
let isSending = false;

function hideWelcome() {
  if (welcome) welcome.classList.add("hidden");
}

function showTyping(show) {
  if (typing) typing.classList.toggle("hidden", !show);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function scrollChatBottom() {
  requestAnimationFrame(() => {
    if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
  });
}

function addMessage(role, text, imageUrl = null) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (text && text.trim() !== "") {
    const textBlock = document.createElement("div");
    textBlock.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
    bubble.appendChild(textBlock);
  }

  if (imageUrl) {
    const img = document.createElement("img");
    img.src = imageUrl;
    img.className = "msg-image";
    bubble.appendChild(img);
  }

  row.appendChild(bubble);
  messages.appendChild(row);

  scrollChatBottom();
}

function addError(text) {
  addMessage("ai", `Erreur : ${text}`);
}

function clearSelectedImage() {
  selectedImageFile = null;
  imageInput.value = "";
  previewImage.src = "";
  previewBox.classList.add("hidden");
}

imageBtn.addEventListener("click", () => {
  imageInput.click();
});

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (!file) return;

  selectedImageFile = file;
  previewImage.src = URL.createObjectURL(file);
  previewBox.classList.remove("hidden");
});

removeImageBtn.addEventListener("click", () => {
  clearSelectedImage();
});

async function sendMessage() {
  if (isSending) return;

  const text = messageInput.value.trim();

  if (!text && !selectedImageFile) return;

  isSending = true;
  sendBtn.disabled = true;
  sendBtn.textContent = "Envoi...";
  hideWelcome();

  const localImageUrl = selectedImageFile
    ? URL.createObjectURL(selectedImageFile)
    : null;

  addMessage("user", text || "", localImageUrl);
  showTyping(true);

  const formData = new FormData();
  formData.append("message", text || "");

  if (selectedImageFile) {
    formData.append("image", selectedImageFile);
  }

  messageInput.value = "";

  try {
    const endpoint = `${API_BASE}/chat` || "/chat";

    const res = await fetch(endpoint, {
      method: "POST",
      body: formData
    });

    const contentType = res.headers.get("content-type") || "";
    let data;

    if (contentType.includes("application/json")) {
      data = await res.json();
    } else {
      const rawText = await res.text();
      throw new Error(rawText || "Réponse invalide du serveur");
    }

    showTyping(false);

    if (!res.ok) {
      throw new Error(data.details || data.error || "Erreur inconnue");
    }

    addMessage("ai", data.reply || "Pas de réponse.");
    clearSelectedImage();
  } catch (err) {
    showTyping(false);
    addError(err.message || "Erreur réseau");
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    sendBtn.textContent = "Envoyer";
    scrollChatBottom();
  }
}

sendBtn.addEventListener("click", sendMessage);

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});

/* stabilisation mobile iPhone */
function updateViewportHeight() {
  const vh = window.visualViewport
    ? window.visualViewport.height
    : window.innerHeight;
  document.documentElement.style.setProperty("--vvh", `${vh}px`);
}

if (window.visualViewport) {
  const syncComposer = () => {
    const viewport = window.visualViewport;
    const keyboardOffset =
      window.innerHeight - viewport.height - viewport.offsetTop;
    composerWrap.style.transform = `translateY(-${Math.max(0, keyboardOffset)}px)`;
  };

  window.visualViewport.addEventListener("resize", () => {
    updateViewportHeight();
    syncComposer();
  });

  window.visualViewport.addEventListener("scroll", syncComposer);
}

messageInput.addEventListener("focus", () => {
  setTimeout(scrollChatBottom, 150);
});

updateViewportHeight();
