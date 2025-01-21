// Attendre que le DOM soit chargé
document.addEventListener('DOMContentLoaded', function() {
    // Récupérer les éléments du DOM
    const chatForm = document.getElementById('chat-form');
    const promptInput = document.getElementById('prompt');
    const chatMessages = document.getElementById('chat-messages');
    const messagesWrapper = document.querySelector('.messages-wrapper');
    const newChatBtn = document.getElementById('new-chat');
    const historyList = document.querySelector('.history-list');
    
    let currentChatId = null;

    function scrollToBottom() {
        messagesWrapper.scrollTop = messagesWrapper.scrollHeight;
    }

    function appendMessage(sender, message, isError = false) {
        if (!message) {
            console.error('Message vide reçu');
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender === 'user' ? 'user-message' : 'alya-message'} animate__animated animate__fadeIn`;
        if (isError) messageDiv.className += ' error-message';
        
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    // Fonction pour récupérer le cookie CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Fonction pour charger une conversation spécifique
    async function loadConversation(chatId) {
        try {
            const response = await fetch(`/get-conversation/${chatId}/`);
            if (!response.ok) throw new Error('Erreur lors du chargement de la conversation');
            
            const data = await response.json();
            if (data.status === 'success') {
                chatMessages.innerHTML = '';
                data.messages.forEach(msg => {
                    appendMessage(msg.is_user ? 'user' : 'alya', msg.content);
                });
                currentChatId = chatId;
            }
        } catch (error) {
            console.error('Erreur:', error);
            appendMessage('alya', 'Erreur lors du chargement de la conversation', true);
        }
    }

    // Fonction pour charger l'historique des chats
    async function loadChatHistory() {
        try {
            const response = await fetch('/chat-history/');
            if (!response.ok) throw new Error('Erreur lors du chargement de l\'historique');
            
            const data = await response.json();
            if (data.status === 'success' && historyList) {
                historyList.innerHTML = '';
                
                if (data.chats.length === 0) {
                    historyList.innerHTML = `
                        <div class="text-muted small text-center py-3">
                            <i class="fa-solid fa-message"></i>
                            Aucune conversation
                        </div>
                    `;
                    return;
                }

                data.chats.forEach(chat => {
                    const date = new Date(chat.created_at);
                    const formattedDate = date.toLocaleDateString();
                    const formattedTime = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    
                    const chatElement = document.createElement('div');
                    chatElement.className = 'chat-history-item p-3 border-bottom';
                    chatElement.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="chat-preview">
                                <div class="chat-date small text-muted">
                                    ${formattedDate} à ${formattedTime}
                                </div>
                                <div class="chat-text">
                                    ${chat.preview}
                                </div>
                            </div>
                            <button class="btn btn-link text-dark p-0 load-chat" data-chat-id="${chat.id}">
                                <i class="fa-solid fa-arrow-right"></i>
                            </button>
                        </div>
                    `;
                    
                    chatElement.querySelector('.load-chat').addEventListener('click', () => {
                        loadConversation(chat.id);
                    });
                    
                    historyList.appendChild(chatElement);
                });
            }
        } catch (error) {
            console.error('Erreur:', error);
        }
    }

    // Fonction pour envoyer un message
    async function handleSubmit(e) {
        e.preventDefault();
        const message = promptInput.value.trim();
        
        if (!message) return;
        
        try {
            // Afficher le message utilisateur
            appendMessage('user', message);
            promptInput.value = '';
            
            // Afficher l'indicateur de chargement
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message alya-message loading';
            loadingDiv.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
            chatMessages.appendChild(loadingDiv);
            scrollToBottom();

            const response = await fetch('/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ 
                    prompt: message,
                    chat_id: currentChatId
                })
            });

            // Supprimer l'indicateur de chargement
            loadingDiv.remove();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Réponse reçue:', data);

            if (data.status === 'success' && data.message) {
                appendMessage('alya', data.message);
                currentChatId = data.chat_id;
                // Recharger l'historique pour afficher la nouvelle conversation
                loadChatHistory();
            } else {
                throw new Error(data.message || 'Une erreur est survenue');
            }

        } catch (error) {
            console.error('Erreur:', error);
            appendMessage('alya', 'Désolé, une erreur est survenue lors du traitement de votre demande.', true);
        }
    }

    // Fonction pour gérer un nouveau chat
    function handleNewChat() {
        chatMessages.innerHTML = '';
        currentChatId = null;
        appendMessage('alya', 'Bonjour! Je suis ALYA, votre assistant personnel. Comment puis-je vous aider aujourd\'hui?');
    }

    // Event listeners
    chatForm.addEventListener('submit', handleSubmit);
    if (newChatBtn) {
        newChatBtn.addEventListener('click', handleNewChat);
    }

    promptInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Message initial et chargement de l'historique
    if (chatMessages.children.length === 0) {
        appendMessage('alya', 'Bonjour! Je suis ALYA, votre assistant personnel. Comment puis-je vous aider aujourd\'hui?');
    }
    loadChatHistory();
}); 