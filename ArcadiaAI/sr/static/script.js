/**
 * ArcadiaAI - Gestione Chat
 * Script principale per l'interfaccia chat
 */

// Stato applicazione// Stato applicazione
const state = {
  conversations: JSON.parse(localStorage.getItem("arcadia_chats")) || [],
  activeConversationIndex: null,
  isWaitingForResponse: false
};

// Elementi DOM
const DOM = {
  newChatBtn: document.getElementById("new-chat-btn"),
  clearChatsBtn: document.getElementById("clear-chats-btn"),
  sendBtn: document.getElementById("send-btn"),
  input: document.getElementById("input"),
  chatbox: document.getElementById("chatbox"),
  chatList: document.getElementById("chat-list"),
  apiProvider: document.getElementById("api-provider")
};

// Inizializzazione
function init() {
  // Verifica che tutti gli elementi esistano
  if (!DOM.newChatBtn || !DOM.clearChatsBtn || !DOM.sendBtn || !DOM.input || !DOM.chatbox || !DOM.chatList) {
    console.error("Errore: Elementi DOM mancanti!");
    return;
  }

  loadConversations();
  setupEventListeners();
  renderUI();
}

// Carica le conversazioni dal localStorage
function loadConversations() {
  try {
    const saved = localStorage.getItem("arcadia_chats");
    if (saved) {
      state.conversations = JSON.parse(saved);
      if (state.conversations.length > 0) {
        // Imposta l'ultima conversazione come attiva
        state.activeConversationIndex = state.conversations.length - 1;
      }
    }
  } catch (e) {
    console.error("Errore caricamento chat:", e);
    state.conversations = [];
  }
}

// Setup event listeners
function setupEventListeners() {
  // Invio messaggio
  DOM.sendBtn.addEventListener("click", sendMessage);
  DOM.input.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !state.isWaitingForResponse) {
      sendMessage();
    }
  });

  // Nuova chat
  DOM.newChatBtn.addEventListener("click", newConversation);

  // Elimina tutto
  DOM.clearChatsBtn.addEventListener("click", clearAllConversations);
}

// Render dell'interfaccia
function renderUI() {
  renderSidebar();
  renderMessages();
  renderInputState();
}

// Render della sidebar con la lista delle chat
function renderSidebar() {
  DOM.chatList.innerHTML = "";

  state.conversations.forEach((conversation, index) => {
    const li = document.createElement("li");
    if (index === state.activeConversationIndex) {
      li.classList.add("active");
    }

    li.innerHTML = `
      <span class="chat-title">${conversation.title}</span>
      <span class="chat-date">${formatDate(conversation.updatedAt)}</span>
    `;

    // Aggiungi evento click per aprire la conversazione
    li.addEventListener("click", () => {
      state.activeConversationIndex = index;
      renderUI();
      DOM.input.focus();
    });

    DOM.chatList.appendChild(li);
  });

  // Se non ci sono conversazioni, mostra un messaggio
  if (state.conversations.length === 0) {
    DOM.chatList.innerHTML = '<li class="empty">Nessuna conversazione</li>';
  }
}

// Render dei messaggi nella chat attiva
function renderMessages() {
  DOM.chatbox.innerHTML = "";

  if (state.activeConversationIndex === null || state.conversations.length === 0) {
    DOM.chatbox.innerHTML = '<div class="welcome-message">Crea una nuova chat per iniziare</div>';
    return;
  }

  const conversation = state.conversations[state.activeConversationIndex];
  
  conversation.messages.forEach(msg => {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${msg.sender}-message`;
    messageDiv.textContent = msg.text;
    DOM.chatbox.appendChild(messageDiv);
  });

  // Scroll automatico
  DOM.chatbox.scrollTop = DOM.chatbox.scrollHeight;
}

// Formatta la data per la visualizzazione
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  });
}

// Crea una nuova conversazione
function newConversation() {
  const newChat = {
    id: Date.now().toString(),
    title: `Chat ${state.conversations.length + 1}`,
    messages: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };

  state.conversations.push(newChat);
  state.activeConversationIndex = state.conversations.length - 1;

  saveToLocalStorage();
  renderUI();
  DOM.input.focus();
}

// Elimina tutte le conversazioni
function clearAllConversations() {
  if (state.conversations.length === 0) return;

  if (confirm("Sei sicuro di voler eliminare TUTTE le conversazioni?")) {
    fetch("/clear_chats", {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        state.conversations = [];
        state.activeConversationIndex = null;
        localStorage.removeItem("arcadia_chats");
        renderUI();
      } else {
        alert("Errore durante l'eliminazione: " + data.error);
      }
    })
    .catch(error => {
      console.error("Errore:", error);
      alert("Errore di connessione durante l'eliminazione");
    });
  }
}

// Invia un messaggio
async function sendMessage() {
  const message = DOM.input.value.trim();
  if (!message || state.isWaitingForResponse) return;

  // Crea nuova conversazione se non esiste
  if (state.activeConversationIndex === null) {
    newConversation();
  }

  const conversation = state.conversations[state.activeConversationIndex];
  const selectedApi = DOM.apiProvider.value;

  // Aggiungi messaggio utente
  addMessageToConversation("user", message);
  DOM.input.value = "";
  renderMessages();

  // Mostra loader
  state.isWaitingForResponse = true;
  renderInputState();

try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        conversation_history: conversation.messages.map(m => ({
          role: m.sender === 'user' ? 'user' : 'model',
          message: m.text
        })),
        api_provider: selectedApi,
        experimental_mode: document.getElementById("experimental-mode-toggle")?.checked || false // <--- AGGIUNTO QUI
      })
    });

    if (!response.ok) {
      throw new Error(`Errore HTTP ${response.status}`);
    }

    const data = await response.json();
    addMessageToConversation("ai", data.reply);
    
    // Aggiorna titolo se è il primo messaggio
    if (conversation.messages.length === 2) {
      updateConversationTitle(conversation, message);
    }

  } catch (error) {
    console.error("Errore invio messaggio:", error);
    addMessageToConversation("ai", "❌ Errore durante l'invio. Riprova.");
  } finally {
    state.isWaitingForResponse = false;
    renderInputState();
    renderMessages();
  }
}

// Aggiungi un messaggio alla conversazione
function addMessageToConversation(sender, text) {
  if (state.activeConversationIndex === null) return;

  const message = {
    sender,
    text,
    timestamp: new Date().toISOString()
  };

  const conversation = state.conversations[state.activeConversationIndex];
  conversation.messages.push(message);
  conversation.updatedAt = new Date().toISOString();
  
  saveToLocalStorage();
}

// Aggiorna il titolo della conversazione
function updateConversationTitle(conversation, firstMessage) {
  const newTitle = firstMessage.length > 20 
    ? firstMessage.substring(0, 20) + "..." 
    : firstMessage;
  
  conversation.title = newTitle;
  saveToLocalStorage();
  renderSidebar();
}

// Salva nello storage locale
function saveToLocalStorage() {
  localStorage.setItem("arcadia_chats", JSON.stringify(state.conversations));
}

// Render dello stato dell'input
function renderInputState() {
  DOM.input.disabled = state.isWaitingForResponse;
  DOM.input.placeholder = state.isWaitingForResponse 
    ? "In attesa di risposta..." 
    : "Scrivi un messaggio...";
  DOM.sendBtn.disabled = state.isWaitingForResponse;
}

// Avvia l'applicazione
document.addEventListener("DOMContentLoaded", init);
