document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('chat-input');
    const chatButton = document.getElementById('chat-button');
    const chatMessages = document.getElementById('chat-messages');

    if (!chatInput || !chatButton || !chatMessages) {
        console.error('Éléments du chat non trouvés');
        return;
    }

    chatButton.addEventListener('click', function() {
        const message = chatInput.value.trim();
        if (message) {
            sendMessage(message);
            chatInput.value = '';
        }
    });

    function sendMessage(message) {
        fetch('/chat/message/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayMessage(data.message);
            } else {
                console.error('Erreur lors de l\'envoi du message:', data.message);
            }
        })
        .catch(error => {
            console.error('Erreur réseau:', error);
        });
    }

    function displayMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
    }

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
}); 