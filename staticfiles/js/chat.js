// Attendre que le DOM soit chargé
document.addEventListener('DOMContentLoaded', function() {
    // Récupérer les éléments du DOM
    const chatForm = document.getElementById('chat-form');
    const promptInput = document.getElementById('prompt');
    const chatMessages = document.getElementById('chat-messages');
    const messagesWrapper = document.querySelector('.messages-wrapper');
    const newChatBtn = document.getElementById('new-chat');

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
                body: JSON.stringify({ prompt: message })
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

    // Message initial
    if (chatMessages.children.length === 0) {
        appendMessage('alya', 'Bonjour! Je suis ALYA, votre assistant personnel. Comment puis-je vous aider aujourd\'hui?');
    }
}); 